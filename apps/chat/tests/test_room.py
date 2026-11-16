import io
import os

from django.conf import settings
from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse
from PIL import Image

from apps.chat.models import Message
from apps.chat.views import MESSAGES_SHOWN
from apps.hubs.models import Hub, HubMembership

from .base import ChatTestCase, picture


class AccessTests(ChatTestCase):
    def test_anonymous_visitors_are_sent_to_login(self):
        self.client.logout()
        self.assertRedirects(self.client.get(self.room_url), f"{reverse('login:login')}?next={self.room_url}")
        self.assertEqual(self.client.post(self.room_url, {"content": "x"}).status_code, 302)
        self.assertFalse(Message.objects.exists())

    def test_outsiders_are_sent_to_the_hub_page_and_see_no_messages(self):
        self.say(self.friend, "secret plans")
        self.client.force_login(self.outsider)
        response = self.client.get(self.room_url)
        self.assertRedirects(response, reverse("hubs:detail", args=[self.hub.id]), fetch_redirect_response=False)
        self.assertNotContains(self.client.get(self.room_url, follow=True), "secret plans")

    def test_outsiders_cannot_post(self):
        self.client.force_login(self.outsider)
        self.send("let me in")
        self.assertFalse(Message.objects.exists())

    def test_leaving_the_hub_closes_the_chat(self):
        HubMembership.objects.filter(user=self.member, hub=self.hub).delete()
        self.assertEqual(self.client.get(self.room_url).status_code, 302)

    def test_hubs_that_are_not_approved_have_no_chat(self):
        for status in (Hub.Status.PENDING, Hub.Status.REJECTED):
            hub = Hub.objects.create(name=f"Hub {status}", requested_by=self.friend, status=status)
            HubMembership.objects.create(user=self.member, hub=hub)
            with self.subTest(status=status):
                self.assertEqual(self.client.get(reverse("chat:room", args=[hub.id])).status_code, 404)
        self.assertEqual(self.client.get(reverse("chat:room", args=[999999])).status_code, 404)


class ReadingTests(ChatTestCase):
    def shown(self):
        return [m.content for m in self.client.get(self.room_url).context["chat_messages"]]

    def test_only_the_last_24_hours_are_shown_oldest_first(self):
        self.say(self.friend, "yesterday", hours_ago=25)
        self.say(self.friend, "morning", hours_ago=5)
        self.say(self.member, "just now")
        self.assertEqual(self.shown(), ["morning", "just now"])

    def test_other_hubs_messages_never_appear(self):
        other = Hub.objects.create(name="Pokemon Go", requested_by=self.friend, status=Hub.Status.APPROVED)
        HubMembership.objects.create(user=self.friend, hub=other)
        self.say(self.friend, "elsewhere", hub=other)
        self.assertEqual(self.shown(), [])

    def test_the_page_shows_who_said_what(self):
        self.say(self.friend, "see you at the library")
        page = self.client.get(self.room_url)
        self.assertContains(page, "Fred")
        self.assertContains(page, "see you at the library")

    def test_a_busy_hub_shows_only_the_newest_messages(self):
        Message.objects.bulk_create(
            [Message(hub=self.hub, sender=self.friend, content=f"m{n}") for n in range(MESSAGES_SHOWN + 5)]
        )
        shown = self.shown()
        self.assertEqual(len(shown), MESSAGES_SHOWN)
        self.assertEqual(shown[0], "m5")
        self.assertEqual(shown[-1], f"m{MESSAGES_SHOWN + 4}")

    def test_query_count_does_not_grow_with_the_number_of_messages(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.client.get(self.room_url)
            return len(captured)

        self.say(self.friend, "one")
        baseline = queries()
        for n in range(10):
            self.say(User.objects.create_user(f"chatter{n}"), f"message {n}")
        self.assertEqual(queries(), baseline)


class SendingTests(ChatTestCase):
    def test_a_message_is_saved_for_the_hub_and_the_logged_in_sender(self):
        response = self.send("  hello everyone  ")
        self.assertRedirects(response, self.room_url + "#latest", fetch_redirect_response=False)
        message = Message.objects.get()
        self.assertEqual((message.content, message.hub, message.sender), ("hello everyone", self.hub, self.member))

    def test_sender_hub_and_time_cannot_be_forged(self):
        other = Hub.objects.create(name="Pokemon Go", requested_by=self.friend, status=Hub.Status.APPROVED)
        self.client.post(self.room_url, {"content": "hi", "sender": self.friend.pk, "hub": other.pk,
                                         "created_at": "2000-01-01 00:00:00"})
        message = Message.objects.get()
        self.assertEqual((message.sender, message.hub), (self.member, self.hub))
        self.assertEqual(Message.objects.recent().count(), 1)

    def test_an_empty_message_is_refused(self):
        for text in ("", "   ", "\n\n"):
            with self.subTest(text=text):
                response = self.send(text)
                self.assertEqual(response.status_code, 200)
                self.assertTrue(response.context["form"].errors)
        self.assertFalse(Message.objects.exists())

    def test_500_characters_is_the_limit(self):
        self.assertEqual(self.send("x" * 501).status_code, 200)
        self.assertFalse(Message.objects.exists())
        self.assertEqual(self.send("x" * 500).status_code, 302)
        self.assertEqual(Message.objects.count(), 1)

    def test_markup_in_a_message_is_shown_as_text(self):
        self.send("<script>alert(1)</script> <b>bold</b>")
        page = self.client.get(self.room_url)
        self.assertNotContains(page, "<script>alert(1)</script>")
        self.assertNotContains(page, "<b>bold</b>")
        self.assertContains(page, "&lt;script&gt;alert(1)&lt;/script&gt;")

    def test_line_breaks_are_kept(self):
        self.send("line one\nline two")
        self.assertContains(self.client.get(self.room_url), "line one<br>line two")


class PictureTests(ChatTestCase):
    def test_a_picture_alone_is_a_valid_message(self):
        self.assertEqual(self.send("", image=picture()).status_code, 302)
        message = Message.objects.get()
        self.assertTrue(message.image)
        self.assertTrue(os.path.exists(message.image.path))
        self.assertContains(self.client.get(self.room_url), message.image.url)

    def test_text_and_picture_together(self):
        self.send("look!", image=picture())
        message = Message.objects.get()
        self.assertEqual(message.content, "look!")
        self.assertTrue(message.image)

    def test_every_allowed_format_works(self):
        for fmt in ("JPEG", "PNG", "GIF", "WEBP"):
            with self.subTest(fmt=fmt):
                self.assertEqual(self.send("", image=picture(f"p.{fmt.lower()}", fmt)).status_code, 302)

    def test_things_that_are_not_pictures_are_refused(self):
        fake = SimpleUploadedFile("evil.png", b"<script>alert(1)</script>", content_type="image/png")
        for file in (fake, picture("p.bmp", "BMP")):
            with self.subTest(file=file.name):
                response = self.send("hi", image=file)
                self.assertIn("image", response.context["form"].errors)
        self.assertFalse(Message.objects.exists())

    def test_pictures_over_2_mb_are_refused(self):
        buffer = io.BytesIO()
        Image.frombytes("RGB", (1200, 1200), os.urandom(1200 * 1200 * 3)).save(buffer, "PNG")
        big = SimpleUploadedFile("big.png", buffer.getvalue(), content_type="image/png")
        self.assertIn("image", self.send("", image=big).context["form"].errors)
        self.assertFalse(Message.objects.exists())

    def test_a_refused_picture_leaves_no_file_behind(self):
        chat_dir = os.path.join(settings.MEDIA_ROOT, "chat")
        files_before = set(os.listdir(chat_dir)) if os.path.isdir(chat_dir) else set()
        self.send("hi", image=picture("p.bmp", "BMP"))
        files_after = set(os.listdir(chat_dir)) if os.path.isdir(chat_dir) else set()
        self.assertEqual(files_after, files_before)


class DeletingTests(ChatTestCase):
    def delete_url(self, message, hub=None):
        return reverse("chat:delete", args=[(hub or self.hub).id, message.id])

    def test_you_can_delete_your_own_message_and_its_picture_file(self):
        self.send("oops", image=picture())
        message = Message.objects.get()
        path = message.image.path
        self.assertTrue(os.path.exists(path))
        response = self.client.post(self.delete_url(message))
        self.assertRedirects(response, self.room_url, fetch_redirect_response=False)
        self.assertFalse(Message.objects.exists())
        self.assertFalse(os.path.exists(path))

    def test_you_cannot_delete_someone_elses_message(self):
        message = self.say(self.friend, "mine, not yours")
        self.assertEqual(self.client.post(self.delete_url(message)).status_code, 404)
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())

    def test_outsiders_and_anonymous_visitors_cannot_delete(self):
        message = self.say(self.member, "hello")
        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(self.delete_url(message)).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post(self.delete_url(message)).status_code, 302)
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())

    def test_deleting_needs_a_post(self):
        message = self.say(self.member, "hello")
        self.assertEqual(self.client.get(self.delete_url(message)).status_code, 405)
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())

    def test_a_message_cannot_be_deleted_through_a_different_hub(self):
        other = Hub.objects.create(name="Pokemon Go", requested_by=self.member, status=Hub.Status.APPROVED)
        HubMembership.objects.create(user=self.member, hub=other)
        message = self.say(self.member, "hello")
        self.assertEqual(self.client.post(self.delete_url(message, hub=other)).status_code, 404)
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())

    def test_only_your_own_messages_offer_a_delete_button(self):
        mine, theirs = self.say(self.member, "mine"), self.say(self.friend, "theirs")
        page = self.client.get(self.room_url).content.decode()
        self.assertIn(self.delete_url(mine), page)
        self.assertNotIn(self.delete_url(theirs), page)

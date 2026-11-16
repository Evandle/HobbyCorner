from django.contrib.auth.models import User
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from apps.chat.models import Message
from apps.chat.views import MESSAGES_SHOWN
from apps.hubs.models import Hub, HubMembership

from .base import ChatTestCase


class PollTestCase(ChatTestCase):
    def setUp(self):
        super().setUp()
        self.poll_url = reverse("chat:poll", args=[self.hub.id])

    def poll(self, after=None, **extra):
        params = {} if after is None else {"after": after}
        return self.client.get(self.poll_url, params, **extra)


class PollAccessTests(PollTestCase):
    def test_anonymous_visitors_are_sent_to_login(self):
        self.client.logout()
        self.assertEqual(self.poll(0).status_code, 302)

    def test_outsiders_get_403_and_learn_nothing(self):
        self.say(self.friend, "secret plans")
        self.client.force_login(self.outsider)
        response = self.poll(0)
        self.assertEqual(response.status_code, 403)
        self.assertNotIn(b"secret plans", response.content)

    def test_hubs_that_are_not_approved_have_no_poll(self):
        pending = Hub.objects.create(name="Waiting", requested_by=self.friend, status=Hub.Status.PENDING)
        HubMembership.objects.create(user=self.member, hub=pending)
        self.assertEqual(self.client.get(reverse("chat:poll", args=[pending.id]), {"after": 0}).status_code, 404)

    def test_polling_is_get_only_and_never_cached(self):
        self.assertEqual(self.client.post(self.poll_url, {"after": 0}).status_code, 405)
        self.assertIn("no-store", self.poll(0)["Cache-Control"])


class PollContentTests(PollTestCase):
    def test_only_messages_after_the_given_id_come_back(self):
        old = self.say(self.friend, "already on screen")
        new_one = self.say(self.friend, "brand new")
        data = self.poll(old.id).json()
        self.assertEqual((data["count"], data["last_id"]), (1, new_one.id))
        self.assertIn("brand new", data["html"])
        self.assertNotIn("already on screen", data["html"])

    def test_nothing_new_returns_an_empty_answer_and_the_same_id(self):
        last = self.say(self.friend, "hello")
        data = self.poll(last.id).json()
        self.assertEqual((data["count"], data["html"], data["last_id"]), (0, "", last.id))

    def test_leaving_out_after_means_everything_in_the_window(self):
        self.say(self.friend, "stale", hours_ago=30)
        self.say(self.friend, "fresh")
        data = self.poll().json()
        self.assertEqual(data["count"], 1)
        self.assertIn("fresh", data["html"])

    def test_expired_messages_are_never_sent(self):
        self.say(self.friend, "stale", hours_ago=30)
        self.assertEqual(self.poll(0).json()["count"], 0)

    def test_other_hubs_messages_are_never_sent(self):
        other = Hub.objects.create(name="Pokemon Go", requested_by=self.friend, status=Hub.Status.APPROVED)
        HubMembership.objects.create(user=self.friend, hub=other)
        self.say(self.friend, "elsewhere", hub=other)
        self.assertEqual(self.poll(0).json()["count"], 0)

    def test_only_your_own_messages_carry_a_delete_form(self):
        mine, theirs = self.say(self.member, "mine"), self.say(self.friend, "theirs")
        html = self.poll(0).json()["html"]
        self.assertIn(reverse("chat:delete", args=[self.hub.id, mine.id]), html)
        self.assertNotIn(reverse("chat:delete", args=[self.hub.id, theirs.id]), html)
        self.assertIn("csrfmiddlewaretoken", html)

    def test_message_text_arrives_escaped(self):
        self.say(self.friend, "<img src=x onerror=alert(1)>")
        data = self.poll(0).json()
        self.assertNotIn("<img src=x", data["html"])
        self.assertIn("&lt;img src=x onerror=alert(1)&gt;", data["html"])

    def test_a_flood_is_handed_over_in_batches_without_losing_any(self):
        Message.objects.bulk_create(
            [Message(hub=self.hub, sender=self.friend, content=f"m{n}") for n in range(MESSAGES_SHOWN + 5)]
        )
        first = self.poll(0).json()
        self.assertEqual(first["count"], MESSAGES_SHOWN)
        second = self.poll(first["last_id"]).json()
        self.assertEqual(second["count"], 5)
        self.assertIn(f"m{MESSAGES_SHOWN + 4}", second["html"])

    def test_query_count_does_not_grow_with_the_number_of_new_messages(self):
        def queries():
            with CaptureQueriesContext(connection) as captured:
                self.poll(0)
            return len(captured)

        self.say(self.friend, "one")
        baseline = queries()
        for n in range(10):
            self.say(User.objects.create_user(f"chatter{n}"), f"message {n}")
        self.assertEqual(queries(), baseline)


class PollInputTests(PollTestCase):
    def test_bad_after_values_are_refused_politely(self):
        for bad in ("abc", "-1", "1.5", "", "99999999999999999999", "1; DROP TABLE messages"):
            with self.subTest(after=bad):
                response = self.poll(bad)
                self.assertEqual(response.status_code, 400)
                self.assertIn("error", response.json())


class LiveRegionTests(ChatTestCase):
    def test_the_message_list_is_a_polite_keyboard_reachable_live_region(self):
        page = self.client.get(self.room_url).content.decode()
        for fragment in ('role="log"', 'aria-live="polite"', 'tabindex="0"',
                         f'data-poll-url="{reverse("chat:poll", args=[self.hub.id])}"'):
            with self.subTest(fragment=fragment):
                self.assertIn(fragment, page)

    def test_the_page_tells_the_script_where_it_is_up_to(self):
        last = self.say(self.friend, "hello")
        self.assertIn(f'data-last-id="{last.id}"', self.client.get(self.room_url).content.decode())

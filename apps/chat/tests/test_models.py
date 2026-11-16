from datetime import timedelta

from django.core.exceptions import ValidationError

from apps.chat.models import FRESH_START_WINDOW, Message

from .base import ChatTestCase


class FreshStartWindowTests(ChatTestCase):
    def test_the_window_is_24_hours(self):
        self.assertEqual(FRESH_START_WINDOW, timedelta(hours=24))

    def test_recent_and_expired_split_messages_at_24_hours(self):
        fresh = self.say(self.member, "fresh", hours_ago=23)
        stale = self.say(self.member, "stale", hours_ago=25)
        self.assertEqual(list(Message.objects.recent()), [fresh])
        self.assertEqual(list(Message.objects.expired()), [stale])

    def test_every_message_is_either_recent_or_expired(self):
        for hours in (0, 12, 23, 25, 48):
            self.say(self.member, f"{hours}h", hours_ago=hours)
        self.assertEqual(Message.objects.recent().count() + Message.objects.expired().count(), 5)


class MessageContentTests(ChatTestCase):
    def test_a_message_needs_text_or_a_picture(self):
        with self.assertRaises(ValidationError):
            Message(hub=self.hub, sender=self.member, content="   ").full_clean()
        Message(hub=self.hub, sender=self.member, content="hi").full_clean()

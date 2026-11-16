import os
from datetime import timedelta
from io import StringIO

from django.core.management import call_command

from apps.chat.models import Message
from apps.hubs.models import Hub, HubMembership

from .base import ChatTestCase, picture


class PurgeCommandTests(ChatTestCase):
    def run_purge(self, *args):
        out = StringIO()
        call_command("purge_expired_messages", *args, stdout=out)
        return out.getvalue()

    def say_with_picture(self, hours_ago):
        self.send("", image=picture())
        message = Message.objects.latest("id")
        Message.objects.filter(pk=message.pk).update(
            created_at=message.created_at - timedelta(hours=hours_ago)
        )
        message.refresh_from_db()
        return message

    def test_only_expired_messages_are_deleted(self):
        keep = self.say(self.member, "fresh", hours_ago=23)
        self.say(self.member, "stale", hours_ago=25)
        self.say(self.friend, "ancient", hours_ago=500)
        output = self.run_purge()
        self.assertEqual(list(Message.objects.all()), [keep])
        self.assertIn("Deleted 2", output)

    def test_it_cleans_every_hub(self):
        other = Hub.objects.create(name="Pokemon Go", requested_by=self.friend, status=Hub.Status.APPROVED)
        HubMembership.objects.create(user=self.friend, hub=other)
        self.say(self.friend, "stale here", hours_ago=30)
        self.say(self.friend, "stale there", hours_ago=30, hub=other)
        self.run_purge()
        self.assertFalse(Message.objects.exists())

    def test_picture_files_of_expired_messages_are_removed_and_fresh_ones_kept(self):
        old = self.say_with_picture(hours_ago=26)
        new = self.say_with_picture(hours_ago=1)
        old_path, new_path = old.image.path, new.image.path
        self.assertTrue(os.path.exists(old_path) and os.path.exists(new_path))
        self.run_purge()
        self.assertFalse(os.path.exists(old_path))
        self.assertTrue(os.path.exists(new_path))
        self.assertEqual(list(Message.objects.all()), [new])

    def test_a_dry_run_changes_nothing(self):
        old = self.say_with_picture(hours_ago=26)
        path = old.image.path
        output = self.run_purge("--dry-run")
        self.assertIn("Would delete 1", output)
        self.assertTrue(Message.objects.filter(pk=old.pk).exists())
        self.assertTrue(os.path.exists(path))

    def test_running_it_twice_is_harmless(self):
        self.say(self.member, "stale", hours_ago=30)
        self.run_purge()
        self.assertIn("Deleted 0", self.run_purge())

    def test_a_picture_file_that_is_already_gone_does_not_stop_the_cleanup(self):
        old = self.say_with_picture(hours_ago=26)
        os.remove(old.image.path)
        self.run_purge()
        self.assertFalse(Message.objects.exists())

    def test_with_nothing_to_do_it_says_so_and_keeps_everything(self):
        self.say(self.member, "fresh")
        self.assertIn("Deleted 0", self.run_purge())
        self.assertEqual(Message.objects.count(), 1)

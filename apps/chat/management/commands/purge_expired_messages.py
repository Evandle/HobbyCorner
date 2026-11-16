from django.core.management.base import BaseCommand

from apps.chat.models import Message


class Command(BaseCommand):
    help = "Delete chat messages older than 24 hours, together with their picture files."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show how many messages would be deleted, without deleting anything.",
        )

    def handle(self, *args, **options):
        # Take one snapshot, so the picture files and the rows are always the
        # same set (a message can't expire halfway through the cleanup).
        expired = list(Message.objects.expired().values_list("pk", "image"))

        if options["dry_run"]:
            self.stdout.write(f"Would delete {len(expired)} expired message(s).")
            return

        storage = Message._meta.get_field("image").storage
        for _, picture_name in expired:
            if picture_name:
                storage.delete(picture_name)  # quietly fine if the file is already gone
        Message.objects.filter(pk__in=[pk for pk, _ in expired]).delete()
        self.stdout.write(f"Deleted {len(expired)} expired message(s).")

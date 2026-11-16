from datetime import timedelta

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


FRESH_START_WINDOW = timedelta(hours=24)


class MessageQuerySet(models.QuerySet):
    def recent(self):
        """Fresh Start window: only messages from the last 24 hours."""
        return self.filter(created_at__gte=timezone.now() - FRESH_START_WINDOW)

    def expired(self):
        """Messages the scheduled cleanup job should delete."""
        return self.filter(created_at__lt=timezone.now() - FRESH_START_WINDOW)


class Message(models.Model):
    hub = models.ForeignKey(
        "hubs.Hub", on_delete=models.CASCADE, related_name="messages"
    )
    sender = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sent_messages",
    )
    content = models.TextField(blank=True)
    image = models.ImageField(upload_to="chat/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = MessageQuerySet.as_manager()

    class Meta:
        db_table = "messages"
        ordering = ["created_at"]
        indexes = [models.Index(fields=["hub", "created_at"], name="msg_hub_created_idx")]

    def clean(self):
        if not self.content.strip() and not self.image:
            raise ValidationError("A message needs text, an image, or both.")

    def __str__(self):
        return f"{self.sender} in {self.hub}: {self.content[:30]}"

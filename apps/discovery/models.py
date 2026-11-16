from django.conf import settings
from django.db import models


class Meetup(models.Model):
    hub = models.ForeignKey(
        "hubs.Hub", on_delete=models.CASCADE, related_name="meetups"
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_meetups",
    )
    location = models.ForeignKey(
        "locations.Location", on_delete=models.PROTECT, related_name="meetups"
    )
    scheduled_time = models.DateTimeField()
    attendees = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="MeetupRSVP",
        related_name="rsvped_meetups",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "meetups"
        ordering = ["scheduled_time"]

    def __str__(self):
        return f"{self.hub} @ {self.location} ({self.scheduled_time:%Y-%m-%d %H:%M})"


class MeetupRSVP(models.Model):
    class Status(models.TextChoices):
        INTERESTED = "interested", "Interested"
        GOING = "going", "Going"

    meetup = models.ForeignKey(
        Meetup, on_delete=models.CASCADE, related_name="rsvps"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="meetup_rsvps",
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.INTERESTED
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "meetup_rsvps"
        constraints = [
            models.UniqueConstraint(
                fields=["meetup", "user"], name="unique_meetup_rsvp"
            )
        ]

    def __str__(self):
        return f"{self.user} -> {self.meetup} ({self.status})"

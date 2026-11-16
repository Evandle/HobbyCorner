from django.conf import settings
from django.db import models


class Hub(models.Model):
    """A niche-interest community (e.g. "Uma Musume"). Anyone can request one;
    a moderator (is_staff) approves or rejects it."""

    class Status(models.TextChoices):
        PENDING = "pending", "Pending review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"

    name = models.CharField(max_length=100, unique=True)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.PENDING
    )
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="requested_hubs",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        through="HubMembership",
        related_name="joined_hubs",
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hubs"
        ordering = ["name"]

    def __str__(self):
        return self.name


class HubMembership(models.Model):
    hub = models.ForeignKey(
        Hub, on_delete=models.CASCADE, related_name="memberships"
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="hub_memberships",
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "hub_memberships"
        constraints = [
            models.UniqueConstraint(
                fields=["hub", "user"], name="unique_hub_membership"
            )
        ]

    def __str__(self):
        return f"{self.user} in {self.hub}"

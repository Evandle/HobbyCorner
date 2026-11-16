from django.contrib.auth.models import User
from django.test import TestCase

from apps.hubs.models import Hub


class HubTestCase(TestCase):
    """Three people and one approved Hub, shared by every Hubs test."""

    def setUp(self):
        self.member = User.objects.create_user("member")
        self.stranger = User.objects.create_user("stranger")
        self.moderator = User.objects.create_user("moderator", is_staff=True)
        self.hub = self.make_hub("Uma Musume", category="Games")

    def make_hub(self, name, status=Hub.Status.APPROVED, requested_by=None, **extra):
        return Hub.objects.create(
            name=name,
            status=status,
            requested_by=requested_by or self.stranger,
            **extra,
        )

    def login(self, user):
        self.client.force_login(user)

import io
import shutil
import tempfile
from datetime import timedelta

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from apps.chat.models import Message
from apps.hubs.models import Hub, HubMembership

TEMP_MEDIA = tempfile.mkdtemp()


def picture(name="pic.png", fmt="PNG", size=(10, 10)):
    buffer = io.BytesIO()
    Image.new("RGB", size, "blue").save(buffer, fmt)
    return SimpleUploadedFile(name, buffer.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=TEMP_MEDIA)
class ChatTestCase(TestCase):
    """A Hub with two members ("member", "friend") and one outsider."""

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA, ignore_errors=True)

    def setUp(self):
        self.member = User.objects.create_user("member", first_name="Mia")
        self.friend = User.objects.create_user("friend", first_name="Fred")
        self.outsider = User.objects.create_user("outsider")
        self.hub = Hub.objects.create(name="Uma Musume", requested_by=self.friend, status=Hub.Status.APPROVED)
        for user in (self.member, self.friend):
            HubMembership.objects.create(user=user, hub=self.hub)
        self.room_url = reverse("chat:room", args=[self.hub.id])
        self.client.force_login(self.member)

    def say(self, sender, text="hello", hours_ago=0, hub=None, **extra):
        message = Message.objects.create(hub=hub or self.hub, sender=sender, content=text, **extra)
        if hours_ago:
            Message.objects.filter(pk=message.pk).update(created_at=timezone.now() - timedelta(hours=hours_ago))
        message.refresh_from_db()
        return message

    def send(self, text="hi there", **files):
        return self.client.post(self.room_url, {"content": text, **files})

from django.contrib.auth.models import User
from django.db import models


class UserSettings(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="settings"
    )
    dark_mode = models.BooleanField(default=False)
    email_notifications = models.BooleanField(default=True)

    def __str__(self):
        return f"Settings for {self.user.username}"

    @staticmethod
    def get_or_create_for(user):
        settings_obj, _ = UserSettings.objects.get_or_create(user=user)
        return settings_obj

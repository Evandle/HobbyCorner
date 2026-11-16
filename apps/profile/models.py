from django.contrib.auth.models import User
from django.db import models


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    university_email = models.EmailField(
        unique=True,
        help_text="Official university email, used to confirm student status."
    )
    full_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(
        upload_to="profile/",
        blank=True,
        null=True,
    )
    interests = models.CharField(
        max_length=255,
        blank=True,
        help_text="Comma-separated niche interests, e.g. 'Pokemon Go, Uma Musume'."
    )
    trust_rating = models.PositiveIntegerField(
        default=100,
        help_text="Community trust score out of 100, updated by the rating system."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def interest_list(self):
        # Return the comma-separated interests as a clean list.
        return [i.strip() for i in self.interests.split(",") if i.strip()]

    @staticmethod
    def get_or_create_for(user):
        """
        Every feature that needs a Profile (home, profile screen) calls this
        instead of duplicating get_or_create logic, so the default-value
        rules live in one place (the profile feature that owns them).
        """
        profile, _ = Profile.objects.get_or_create(
            user=user,
            defaults={"university_email": user.email or f"{user.username}@cit.edu"},
        )
        return profile

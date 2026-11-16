from django.contrib.auth.models import User
from django.db import models
from django.db.models import Avg

from .validators import validate_university_email


class Interest(models.Model):
    name = models.CharField(max_length=100, unique=True)

    class Meta:
        db_table = "interests"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Profile(models.Model):
    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="profile"
    )
    university_email = models.EmailField(
        unique=True,
        validators=[validate_university_email],
        help_text="Your university email, used to confirm student status.",
    )
    bio = models.TextField(blank=True)
    profile_image = models.ImageField(upload_to="profile/", blank=True, null=True)
    location = models.ForeignKey(
        "locations.Location",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="profiles",
        help_text="Where you usually are on campus (used to suggest nearby meetups).",
    )
    interests = models.ManyToManyField(
        Interest, through="ProfileInterest", related_name="profiles", blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "profiles"

    def __str__(self):
        return f"{self.user.username}'s Profile"

    def save(self, *args, **kwargs):
        # One spelling per email, so BEN@x.com and ben@x.com can't both sign up.
        self.university_email = (self.university_email or "").strip().lower()
        super().save(*args, **kwargs)

    @property
    def trust_rating(self):
        """Derived, never stored (see the ERD): the average rating received
        (1 to 5) as a percentage. 100 until somebody has rated you."""
        average = self.user.ratings_received.aggregate(avg=Avg("score"))["avg"]
        return 100 if average is None else round(average / 5 * 100)

    def interest_list(self):
        return [interest.name for interest in self.interests.all()]

    @staticmethod
    def get_or_create_for(user):
        """For accounts made outside Register (e.g. createsuperuser). The
        placeholder email ends in .invalid, which can never be a real address."""
        email = user.email or f"user{user.pk}@no-email.invalid"
        profile, _ = Profile.objects.get_or_create(
            user=user, defaults={"university_email": email}
        )
        return profile


class ProfileInterest(models.Model):
    profile = models.ForeignKey(
        Profile, on_delete=models.CASCADE, related_name="profile_interests"
    )
    interest = models.ForeignKey(
        Interest, on_delete=models.CASCADE, related_name="profile_interests"
    )

    class Meta:
        db_table = "profile_interests"
        constraints = [
            models.UniqueConstraint(
                fields=["profile", "interest"], name="unique_profile_interest"
            )
        ]

    def __str__(self):
        return f"{self.profile} likes {self.interest}"

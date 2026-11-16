from django.conf import settings
from django.db import models


class Rating(models.Model):
    """One person's 1-5 rating of another. Profile.trust_rating is derived
    from the ratings a user has received; nothing here is stored on Profile."""

    rater = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings_given",
    )
    rated_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="ratings_received",
    )
    score = models.PositiveSmallIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "ratings"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(score__gte=1, score__lte=5),
                name="rating_score_1_to_5",
            )
        ]

    def __str__(self):
        return f"{self.rater} rated {self.rated_user}: {self.score}"

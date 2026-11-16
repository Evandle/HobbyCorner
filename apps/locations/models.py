from django.db import models


class Location(models.Model):
    """A campus building or area. A shared lookup table: Profile (where you
    usually are) and Discovery (where a meetup happens) both point at it."""

    name = models.CharField(
        max_length=150,
        unique=True,
        help_text="Self-reported campus building/area, not live GPS.",
    )

    class Meta:
        db_table = "locations"
        ordering = ["name"]

    def __str__(self):
        return self.name

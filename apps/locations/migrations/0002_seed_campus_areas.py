from django.db import migrations

# Generic starter areas. Rename or add your real campus spots in the Django admin.
AREAS = [
    "Library", "Canteen", "Gymnasium", "Main Gate",
    "Student Center", "Engineering Building", "Computer Laboratory", "Quadrangle",
]


def seed(apps, schema_editor):
    Location = apps.get_model("locations", "Location")
    for name in AREAS:
        Location.objects.get_or_create(name=name)


def unseed(apps, schema_editor):
    apps.get_model("locations", "Location").objects.filter(name__in=AREAS).delete()


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]

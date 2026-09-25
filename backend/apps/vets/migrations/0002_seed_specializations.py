"""Standart mutaxassisliklar / hayvon turlari (ARCHITECTURE.md 3-bo'lim)."""
from django.db import migrations

SPECIALIZATIONS = [
    ("It", "it", "🐕"),
    ("Mushuk", "mushuk", "🐈"),
    ("Qush", "qush", "🦜"),
    ("Qoramol", "qoramol", "🐄"),
    ("Qo'y / Echki", "qoy-echki", "🐑"),
    ("Ot", "ot", "🐎"),
    ("Ekzotik hayvonlar", "ekzotik", "🦎"),
    ("Kemiruvchilar", "kemiruvchilar", "🐹"),
]


def seed(apps, schema_editor):
    Specialization = apps.get_model("vets", "Specialization")
    for name, slug, icon in SPECIALIZATIONS:
        Specialization.objects.get_or_create(
            slug=slug, defaults={"name": name, "icon": icon}
        )


def unseed(apps, schema_editor):
    Specialization = apps.get_model("vets", "Specialization")
    Specialization.objects.filter(
        slug__in=[s[1] for s in SPECIALIZATIONS]
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("vets", "0001_initial")]
    operations = [migrations.RunPython(seed, unseed)]

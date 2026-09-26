from django.db import migrations


CATEGORIES = [
    ("Retiya & Charkha", "retiya-charkha"),
    ("Clothing", "clothing"),
    ("Books", "books"),
    ("Electronics", "electronics"),
    ("Furniture", "furniture"),
    ("Bags", "bags"),
    ("Hostel Essentials", "hostel-essentials"),
    ("Tools", "tools"),
    ("Art & Craft", "art-craft"),
    ("Sports & Fitness", "sports-fitness"),
]


def seed_categories(apps, schema_editor):
    Category = apps.get_model("categories", "Category")
    for name, slug in CATEGORIES:
        Category.objects.get_or_create(slug=slug, defaults={"name": name, "is_active": True})


class Migration(migrations.Migration):
    dependencies = [("categories", "0001_initial")]
    operations = [migrations.RunPython(seed_categories, migrations.RunPython.noop)]

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_profile_whatsapp_opt_in")]
    operations = [
        migrations.AddField(
            model_name="profile",
            name="preferred_language",
            field=models.CharField(
                choices=[("en", "English"), ("gu", "Gujarati"), ("hi", "Hindi")],
                default="en",
                max_length=2,
            ),
        ),
    ]

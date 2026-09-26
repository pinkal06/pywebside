from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("chat", "0003_messagereport")]

    operations = [
        migrations.AddField(
            model_name="conversation",
            name="status",
            field=models.CharField(
                choices=[("ACTIVE", "Active"), ("CLOSED", "Closed"), ("BLOCKED", "Blocked")],
                default="ACTIVE",
                max_length=10,
            ),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["conversation", "created_at"], name="chat_msg_conv_created_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["sender", "created_at"], name="chat_msg_sender_created_idx"),
        ),
        migrations.AddIndex(
            model_name="message",
            index=models.Index(fields=["is_read"], name="chat_msg_is_read_idx"),
        ),
    ]

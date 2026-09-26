from django.db import migrations, models
import django.db.models.deletion
from django.conf import settings
from django.db.models import Q


class Migration(migrations.Migration):
    dependencies = [
        ("chat", "0005_rename_chat_msg_conv_created_idx_chat_messag_convers_3154fc_idx_and_more"),
        ("orders", "0003_alter_order_status_and_more"),
        ("products", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="SellerAvailability",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("weekday", models.PositiveSmallIntegerField(choices=[(0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"), (4, "Friday"), (5, "Saturday"), (6, "Sunday")])),
                ("start_time", models.TimeField()),
                ("end_time", models.TimeField()),
                ("pickup_location", models.CharField(max_length=255)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("seller", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pickup_availability", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("weekday", "start_time")},
        ),
        migrations.CreateModel(
            name="PickupSchedule",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("pickup_location", models.CharField(max_length=255)),
                ("pickup_date", models.DateField()),
                ("pickup_time", models.TimeField()),
                ("buyer_message", models.TextField(blank=True, max_length=1000)),
                ("seller_message", models.TextField(blank=True, max_length=1000)),
                ("status", models.CharField(choices=[("PENDING", "Pending seller confirmation"), ("CONFIRMED", "Confirmed"), ("TIME_CHANGE_REQUESTED", "Time change requested"), ("REJECTED", "Rejected"), ("CANCELLED", "Cancelled"), ("COMPLETED", "Completed"), ("EXPIRED", "Expired")], default="PENDING", max_length=30)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("confirmed_at", models.DateTimeField(blank=True, null=True)),
                ("cancelled_at", models.DateTimeField(blank=True, null=True)),
                ("buyer", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pickup_schedules", to=settings.AUTH_USER_MODEL)),
                ("conversation", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pickup_schedules", to="chat.conversation")),
                ("order", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="pickup_schedules", to="orders.order")),
                ("product", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="pickup_schedules", to="products.product")),
                ("seller", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="seller_pickup_schedules", to=settings.AUTH_USER_MODEL)),
            ],
            options={"ordering": ("-pickup_date", "-pickup_time", "-created_at")},
        ),
        migrations.AddConstraint(
            model_name="selleravailability",
            constraint=models.CheckConstraint(condition=Q(("end_time__gt", models.F("start_time"))), name="availability_end_after_start"),
        ),
        migrations.AddConstraint(
            model_name="pickupschedule",
            constraint=models.UniqueConstraint(condition=~Q(("status__in", ["REJECTED", "CANCELLED", "COMPLETED", "EXPIRED"])), fields=("buyer", "seller", "product"), name="unique_active_pickup_per_product"),
        ),
        migrations.AddIndex(model_name="selleravailability", index=models.Index(fields=["seller", "weekday", "is_active"], name="orders_selle_seller__5b97c1_idx")),
        migrations.AddIndex(model_name="pickupschedule", index=models.Index(fields=["buyer", "pickup_date", "status"], name="orders_picku_buyer_i_40bc3b_idx")),
        migrations.AddIndex(model_name="pickupschedule", index=models.Index(fields=["seller", "pickup_date", "status"], name="orders_picku_seller__a4b22e_idx")),
        migrations.AddIndex(model_name="pickupschedule", index=models.Index(fields=["pickup_date", "status"], name="orders_picku_pickup_d_98f5ca_idx")),
    ]

from django.conf import settings
from django.db import models


class Notification(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    message = models.CharField(max_length=255)
    url = models.URLField(blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("-created_at",)

    def __str__(self):
        return f"{self.user}: {self.message}"

    def mark_read(self):
        if not self.is_read:
            from django.utils import timezone
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=("is_read", "read_at"))


class WhatsAppNotification(models.Model):
    PENDING = "PENDING"
    SENT = "SENT"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    STATUS_CHOICES = [(value, value.title()) for value in (PENDING, SENT, FAILED, SKIPPED)]

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="whatsapp_notifications")
    phone_number = models.CharField(max_length=32, blank=True)
    notification_type = models.CharField(max_length=80)
    template_name = models.CharField(max_length=120)
    reference_type = models.CharField(max_length=80, blank=True)
    reference_id = models.CharField(max_length=80, blank=True)
    idempotency_key = models.CharField(max_length=255, unique=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=PENDING)
    provider_message_id = models.CharField(max_length=120, blank=True)
    error_message = models.CharField(max_length=255, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=("status",)),
            models.Index(fields=("notification_type",)),
            models.Index(fields=("reference_type", "reference_id")),
        ]

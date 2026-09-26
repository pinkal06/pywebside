from django.conf import settings
from django.db import models


class AuditLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="audit_logs",
    )
    action = models.CharField(max_length=100)
    object_type = models.CharField(max_length=50)
    object_id = models.CharField(max_length=50, blank=True)
    description = models.TextField()
    ip_address = models.CharField(max_length=45, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["action"]),
            models.Index(fields=["object_type"]),
        ]

    def __str__(self):
        actor = self.user.username if self.user else "System"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {actor} - {self.action} on {self.object_type} #{self.object_id}"


class SecurityLog(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="security_logs",
    )
    event_type = models.CharField(max_length=50)
    description = models.TextField()
    ip_address = models.CharField(max_length=45, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["event_type"]),
        ]

    def __str__(self):
        actor = self.user.username if self.user else "Anonymous"
        return f"[{self.created_at:%Y-%m-%d %H:%M}] {self.event_type} - {actor} ({self.ip_address})"

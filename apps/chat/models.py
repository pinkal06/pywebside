from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone


class Conversation(models.Model):
    STATUS_ACTIVE = "ACTIVE"
    STATUS_CLOSED = "CLOSED"
    STATUS_BLOCKED = "BLOCKED"
    STATUS_CHOICES = [
        (STATUS_ACTIVE, "Active"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_BLOCKED, "Blocked"),
    ]
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="buyer_conversations")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_conversations")
    product = models.ForeignKey(
        "products.Product", on_delete=models.SET_NULL, related_name="conversations",
        blank=True, null=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        ordering = ("-updated_at",)
        constraints = [
            models.UniqueConstraint(fields=("buyer", "seller", "product"), name="unique_product_conversation"),
        ]

    def clean(self):
        if self.buyer_id and self.buyer_id == self.seller_id:
            raise ValidationError("A seller cannot start a conversation with themselves.")
        if self.product_id and self.seller_id != self.product.owner_id:
            raise ValidationError("The seller must own the linked product.")

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        subject = self.product.title if self.product_id else "General conversation"
        return f"{subject} ({self.buyer} and {self.seller})"

    def has_participant(self, user):
        return user.is_authenticated and user.pk in (self.buyer_id, self.seller_id)


class Message(models.Model):
    TYPE_TEXT = "text"
    TYPE_VOICE = "voice"
    MESSAGE_TYPE_CHOICES = [(TYPE_TEXT, "Text"), (TYPE_VOICE, "Voice")]
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="chat_messages")
    body = models.TextField(max_length=2000)
    message_type = models.CharField(max_length=10, choices=MESSAGE_TYPE_CHOICES, default=TYPE_TEXT)
    audio_file = models.FileField(upload_to="chat/voice/%Y/%m/", blank=True, null=True)
    audio_duration = models.PositiveIntegerField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)
    read_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        ordering = ("created_at",)
        indexes = [
            models.Index(fields=("conversation", "created_at")),
            models.Index(fields=("sender", "created_at")),
            models.Index(fields=("is_read",)),
        ]

    def clean(self):
        if self.conversation_id and self.sender_id and not self.conversation.has_participant(self.sender):
            raise ValidationError("Only conversation participants can send messages.")
        if self.message_type == self.TYPE_TEXT and (not self.body or not self.body.strip()):
            raise ValidationError("Message cannot be empty.")
        if self.message_type == self.TYPE_VOICE and not self.audio_file:
            raise ValidationError("Voice message file is required.")

    def mark_read(self):
        if not self.is_read:
            self.is_read = True
            self.read_at = timezone.now()
            self.save(update_fields=("is_read", "read_at"))

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

    def __str__(self):
        return f"Message from {self.sender} in conversation {self.conversation_id}"


class MessageReport(models.Model):
    STATUS_OPEN = "open"
    STATUS_REVIEWING = "reviewing"
    STATUS_RESOLVED = "resolved"
    STATUS_DISMISSED = "dismissed"
    REPORT_STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_REVIEWING, "Reviewing"),
        (STATUS_RESOLVED, "Resolved"),
        (STATUS_DISMISSED, "Dismissed"),
    ]

    REASON_CHOICES = [
        ("spam", "Spam"),
        ("harassment", "Harassment"),
        ("fraud", "Fraud"),
        ("scam", "Scam"),
        ("inappropriate", "Inappropriate content"),
        ("other", "Other"),
    ]

    message = models.ForeignKey(Message, on_delete=models.CASCADE, related_name="reports")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="reported_messages")
    reason = models.CharField(max_length=30, choices=REASON_CHOICES)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=REPORT_STATUS_CHOICES, default=STATUS_OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Report on Message #{self.message_id} by {self.reported_by} ({self.status})"

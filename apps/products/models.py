from urllib.parse import quote_plus

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse

from apps.categories.models import Category


class Product(models.Model):
    FULFILLMENT_DELIVERY = "delivery"
    FULFILLMENT_PICKUP = "pickup"
    FULFILLMENT_BOTH = "both"
    FULFILLMENT_CHOICES = [
        (FULFILLMENT_DELIVERY, "Delivery"),
        (FULFILLMENT_PICKUP, "Pickup"),
        (FULFILLMENT_BOTH, "Delivery and pickup"),
    ]
    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_REJECTED = "rejected"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_ACTIVE, "Active"),
        (STATUS_REJECTED, "Rejected"),
    ]

    CONDITION_CHOICES = [("new", "New"), ("like_new", "Like new"), ("good", "Good"), ("fair", "Fair")]
    owner = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="products")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products")
    title = models.CharField(max_length=160)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    discount_percent = models.DecimalField(max_digits=5, decimal_places=2, default=0, validators=[MinValueValidator(0)])
    stock_quantity = models.PositiveIntegerField(default=1)
    condition = models.CharField(max_length=20, choices=CONDITION_CHOICES, default="good")
    location = models.CharField(max_length=120, blank=True)
    fulfillment_method = models.CharField(max_length=20, choices=FULFILLMENT_CHOICES, default=FULFILLMENT_BOTH)
    specifications = models.JSONField(default=dict, blank=True)
    image = models.ImageField(upload_to="products/", blank=True, null=True)
    is_active = models.BooleanField(default=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    rejection_reason = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["is_active"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("product_detail", kwargs={"pk": self.pk})

    @property
    def maps_url(self):
        location = (self.location or "").strip()
        if not location:
            return ""
        if location.startswith(("http://", "https://")):
            return location
        return f"https://www.google.com/maps/search/?api=1&query={quote_plus(location)}"


class ProductReport(models.Model):
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
        ("prohibited", "Prohibited item"),
        ("inappropriate", "Inappropriate content"),
        ("fake", "Fake or counterfeit item"),
        ("copyright", "Copyright violation"),
        ("fraud", "Fraud or scam"),
        ("other", "Other"),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reports")
    reported_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="product_reports")
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
        return f"Report on {self.product.title} by {self.reported_by} ({self.status})"


class Wishlist(models.Model):
    """A product saved by a verified, active user."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="wishlist_items")
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="wishlist_items")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("-created_at",)
        constraints = [
            models.UniqueConstraint(fields=("user", "product"), name="unique_wishlist_user_product"),
        ]

    def __str__(self):
        return f"{self.user} - {self.product}"

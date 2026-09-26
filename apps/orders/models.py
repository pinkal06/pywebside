from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.utils import timezone


class Order(models.Model):
    PENDING = "pending"
    CONFIRMED = "confirmed"
    PROCESSING = "processing"
    SHIPPED = "shipped"
    DELIVERED = "delivered"
    CANCELLED = "cancelled"
    # Backwards-compatible choices
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    COMPLETED = "completed"

    STATUS_CHOICES = [
        (PENDING, "Pending"),
        (CONFIRMED, "Confirmed"),
        (PROCESSING, "Processing"),
        (SHIPPED, "Shipped"),
        (DELIVERED, "Delivered"),
        (CANCELLED, "Cancelled"),
        (ACCEPTED, "Accepted"),
        (REJECTED, "Rejected"),
        (COMPLETED, "Completed"),
    ]

    ALLOWED_TRANSITIONS = {
        PENDING: [CONFIRMED, ACCEPTED, CANCELLED, REJECTED],
        CONFIRMED: [PROCESSING, CANCELLED],
        ACCEPTED: [PROCESSING, CANCELLED],
        PROCESSING: [SHIPPED, CANCELLED],
        SHIPPED: [DELIVERED],
        DELIVERED: [],
        COMPLETED: [],
        CANCELLED: [],
        REJECTED: [],
    }

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="orders")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="received_orders")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    shipping_address = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ("-created_at",)
        indexes = [
            models.Index(fields=["status"]),
            models.Index(fields=["-created_at"]),
        ]

    def __str__(self):
        return f"Order #{self.pk} - {self.product.title}"

    @property
    def order_number(self):
        date_str = self.created_at.strftime("%Y%m%d") if self.created_at else "00000000"
        return f"RB-{date_str}-{self.pk:06d}"

    def can_transition_to(self, new_status):
        return new_status in self.ALLOWED_TRANSITIONS.get(self.status, [])



class Cart(models.Model):
    """The authenticated user's persistent shopping cart."""

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="cart")
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Cart for {self.user}"

    @property
    def total(self):
        return sum(item.line_total for item in self.items.select_related("product").all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="cart_items")
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=("cart", "product"), name="unique_cart_product"),
        ]

    @property
    def line_total(self):
        return self.product.price * self.quantity


class SellerAvailability(models.Model):
    WEEKDAY_CHOICES = [
        (0, "Monday"), (1, "Tuesday"), (2, "Wednesday"), (3, "Thursday"),
        (4, "Friday"), (5, "Saturday"), (6, "Sunday"),
    ]
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pickup_availability")
    weekday = models.PositiveSmallIntegerField(choices=WEEKDAY_CHOICES)
    start_time = models.TimeField()
    end_time = models.TimeField()
    pickup_location = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ("weekday", "start_time")
        constraints = [
            models.CheckConstraint(condition=Q(end_time__gt=models.F("start_time")), name="availability_end_after_start"),
        ]
        indexes = [models.Index(fields=("seller", "weekday", "is_active"))]

    def __str__(self):
        return f"{self.seller} - {self.get_weekday_display()}"


class PickupSchedule(models.Model):
    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    TIME_CHANGE_REQUESTED = "TIME_CHANGE_REQUESTED"
    REJECTED = "REJECTED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    EXPIRED = "EXPIRED"
    STATUS_CHOICES = [
        (PENDING, "Pending seller confirmation"),
        (CONFIRMED, "Confirmed"),
        (TIME_CHANGE_REQUESTED, "Time change requested"),
        (REJECTED, "Rejected"),
        (CANCELLED, "Cancelled"),
        (COMPLETED, "Completed"),
        (EXPIRED, "Expired"),
    ]
    INACTIVE_STATUSES = [REJECTED, CANCELLED, COMPLETED, EXPIRED]

    product = models.ForeignKey("products.Product", on_delete=models.CASCADE, related_name="pickup_schedules")
    buyer = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pickup_schedules")
    seller = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="seller_pickup_schedules")
    conversation = models.ForeignKey("chat.Conversation", on_delete=models.CASCADE, related_name="pickup_schedules")
    order = models.ForeignKey("orders.Order", on_delete=models.SET_NULL, null=True, blank=True, related_name="pickup_schedules")
    pickup_location = models.CharField(max_length=255)
    pickup_date = models.DateField()
    pickup_time = models.TimeField()
    buyer_message = models.TextField(blank=True, max_length=1000)
    seller_message = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default=PENDING)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    reminder_sent_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ("-pickup_date", "-pickup_time", "-created_at")
        indexes = [
            models.Index(fields=("buyer", "pickup_date", "status")),
            models.Index(fields=("seller", "pickup_date", "status")),
            models.Index(fields=("pickup_date", "status")),
        ]

    def __str__(self):
        return f"Pickup for {self.product} on {self.pickup_date}"

    @property
    def is_active(self):
        return self.status not in self.INACTIVE_STATUSES

    def mark_confirmed(self):
        self.status = self.CONFIRMED
        self.confirmed_at = timezone.now()

    def mark_completed(self):
        self.status = self.COMPLETED
        self.completed_at = timezone.now()

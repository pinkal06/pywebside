from django.contrib import admin

from .models import Cart, CartItem, Order, PickupSchedule, SellerAvailability


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "buyer", "seller", "quantity", "total_price", "status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("product__title", "buyer__email", "seller__email")


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("user", "updated_at")
    search_fields = ("user__email",)


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ("cart", "product", "quantity")


@admin.register(SellerAvailability)
class SellerAvailabilityAdmin(admin.ModelAdmin):
    list_display = ("seller", "weekday", "start_time", "end_time", "pickup_location", "is_active")
    list_filter = ("weekday", "is_active")
    search_fields = ("seller__email", "pickup_location")


@admin.register(PickupSchedule)
class PickupScheduleAdmin(admin.ModelAdmin):
    list_display = ("id", "product", "buyer", "seller", "pickup_date", "pickup_time", "status")
    list_filter = ("status", "pickup_date")
    search_fields = ("product__title", "buyer__email", "seller__email", "pickup_location")

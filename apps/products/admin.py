from django.contrib import admin
from .models import Product, ProductReport, Wishlist


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("title", "owner", "category", "price", "stock_quantity", "status", "is_active", "created_at")
    list_filter = ("status", "is_active", "condition", "category", "created_at")
    search_fields = ("title", "description", "owner__username", "owner__email")


@admin.register(ProductReport)
class ProductReportAdmin(admin.ModelAdmin):
    list_display = ("product", "reported_by", "reason", "status", "created_at")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("product__title", "reported_by__username", "description")


admin.site.register(Wishlist)

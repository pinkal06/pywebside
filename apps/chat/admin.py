from django.contrib import admin
from .models import Conversation, Message, MessageReport


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("product", "buyer", "seller", "updated_at")
    list_filter = ("created_at",)
    search_fields = ("product__title", "buyer__email", "seller__email")


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ("conversation", "sender", "is_read", "created_at")
    list_filter = ("is_read", "created_at")
    search_fields = ("body", "sender__email")


@admin.register(MessageReport)
class MessageReportAdmin(admin.ModelAdmin):
    list_display = ("message", "reported_by", "reason", "status", "created_at")
    list_filter = ("status", "reason", "created_at")
    search_fields = ("message__body", "reported_by__username", "description")

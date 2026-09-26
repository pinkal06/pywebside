from django.contrib import admin
from .models import AuditLog, SecurityLog


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "action", "object_type", "object_id", "ip_address")
    list_filter = ("action", "object_type", "created_at")
    search_fields = ("description", "object_id", "user__username", "ip_address")
    readonly_fields = ("user", "action", "object_type", "object_id", "description", "ip_address", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(SecurityLog)
class SecurityLogAdmin(admin.ModelAdmin):
    list_display = ("created_at", "user", "event_type", "ip_address", "user_agent")
    list_filter = ("event_type", "created_at")
    search_fields = ("description", "user__username", "ip_address")
    readonly_fields = ("user", "event_type", "description", "ip_address", "user_agent", "created_at")

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

from django.contrib import admin

from .models import Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'role', 'is_email_verified', 'is_active', 'created_at')
    list_filter = ('role', 'is_email_verified', 'is_active')
    search_fields = ('full_name', 'user__email', 'student_id', 'college', 'city')
    fieldsets = (
        ('Account', {'fields': ('user', 'role', 'is_email_verified', 'is_active')}),
        ('Profile Details', {'fields': ('full_name', 'profile_photo', 'mobile_number', 'college', 'department', 'semester', 'student_id', 'city', 'state')}),
    )

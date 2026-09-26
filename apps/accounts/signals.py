from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Profile


@receiver(post_save, sender=get_user_model())
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        profile, _ = Profile.objects.get_or_create(user=instance)
        if instance.is_superuser or instance.is_staff:
            profile.role = Profile.ROLE_ADMIN
        elif profile.role in ("", None):
            profile.role = Profile.ROLE_BUYER
        if not profile.full_name:
            profile.full_name = instance.get_full_name() or instance.email or instance.username
        if not profile.is_email_verified and getattr(instance, "email", ""):
            profile.is_email_verified = getattr(instance, "is_active", True)
        if not profile.is_active:
            profile.is_active = instance.is_active
        profile.save(update_fields=["role", "full_name", "is_email_verified", "is_active", "updated_at"])

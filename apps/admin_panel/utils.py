from functools import wraps
from django.conf import settings
from django.core.exceptions import PermissionDenied
from django.shortcuts import redirect

from apps.accounts.models import Profile
from .models import AuditLog, SecurityLog


def get_client_ip(request):
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR", "")
    return ip or "127.0.0.1"


def log_audit(request, action, object_type, object_id="", description=""):
    user = request.user if getattr(request, "user", None) and request.user.is_authenticated else None
    ip = get_client_ip(request)
    return AuditLog.objects.create(
        user=user,
        action=action,
        object_type=object_type,
        object_id=str(object_id),
        description=description,
        ip_address=ip,
    )


def log_security(request, event_type, description="", user=None):
    if user is None and getattr(request, "user", None) and request.user.is_authenticated:
        user = request.user
    ip = get_client_ip(request)
    user_agent = request.META.get("HTTP_USER_AGENT", "")[:255]
    return SecurityLog.objects.create(
        user=user,
        event_type=event_type,
        description=description,
        ip_address=ip,
        user_agent=user_agent,
    )


def is_admin_user(user):
    if not user or not user.is_authenticated:
        return False
    if not user.is_active:
        return False
    if user.is_superuser or user.is_staff:
        profile = getattr(user, "profile", None)
        return profile is None or profile.is_active
    profile = getattr(user, "profile", None)
    if profile and profile.is_active and profile.role == Profile.ROLE_ADMIN:
        return True
    return False


def admin_required(view_func):
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect(f"{settings.LOGIN_URL}?next={request.path}")
        if not is_admin_user(request.user):
            log_security(
                request,
                event_type="UNAUTHORIZED_ADMIN_ACCESS",
                description=f"Forbidden attempt to access admin view: {request.path}",
                user=request.user,
            )
            raise PermissionDenied("You do not have administrative privileges.")
        return view_func(request, *args, **kwargs)

    return _wrapped_view

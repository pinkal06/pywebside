from django.core.mail import send_mail
from django.urls import reverse

from .models import Notification


def notify(user, message, url_name=None, kwargs=None, email=True):
    """Create an in-app notification and, when configured, a concise email."""
    url = reverse(url_name, kwargs=kwargs or {}) if url_name else ""
    notification = Notification.objects.create(user=user, message=message, url=url)
    if email and user.email:
        send_mail(
            "RetiyaBazar notification",
            message,
            None,
            [user.email],
            fail_silently=True,
        )
    return notification

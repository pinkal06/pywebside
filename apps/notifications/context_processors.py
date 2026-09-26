from .models import Notification
from apps.chat.models import Message
from django.db.models import Q


def notification_summary(request):
    if not request.user.is_authenticated:
        return {"unread_notification_count": 0, "recent_notifications": [], "unread_message_count": 0}
    qs = Notification.objects.filter(user=request.user)
    unread_messages = Message.objects.filter(
        Q(conversation__buyer=request.user) | Q(conversation__seller=request.user),
        is_read=False,
    ).exclude(sender=request.user).count()
    return {
        "unread_notification_count": qs.filter(is_read=False).count(),
        "recent_notifications": qs[:5],
        "unread_message_count": unread_messages,
    }

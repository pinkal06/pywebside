from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import Notification


@login_required
def notification_list(request):
    notifications = Notification.objects.filter(user=request.user)[:100]
    return render(request, "notifications/notification_list.html", {
        "notifications": notifications, "page_title": "Notifications",
    })


@login_required
def notification_mark_read(request, pk):
    notification = get_object_or_404(Notification, pk=pk, user=request.user)
    if request.method == "POST":
        notification.mark_read()
    return redirect(request.POST.get("next") or "notification_list")


@login_required
def notification_mark_all_read(request):
    if request.method == "POST":
        Notification.objects.filter(user=request.user, is_read=False).update(
            is_read=True, read_at=timezone.now()
        )
    return redirect("notification_list")


@login_required
def notification_dropdown(request):
    """Small JSON payload used by the navbar and safe for polling/fallback UIs."""
    from django.http import JsonResponse
    notifications = Notification.objects.filter(user=request.user, is_read=False)[:10]
    return JsonResponse({
        "count": Notification.objects.filter(user=request.user, is_read=False).count(),
        "notifications": [
            {"message": n.message, "url": n.url, "created_at": n.created_at.isoformat()}
            for n in notifications
        ],
    })

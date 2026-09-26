from .models import Product, Wishlist
from apps.notifications.models import Notification
from apps.orders.models import Cart


def shopping_counts(request):
    wishlist_count = 0
    if request.user.is_authenticated:
        wishlist_count = Wishlist.objects.filter(user=request.user).count()
        unread_notification_count = Notification.objects.filter(
            user=request.user, is_read=False
        ).count()
    else:
        unread_notification_count = 0
    cart = request.session.get("cart", {})
    if request.user.is_authenticated:
        persistent, _ = Cart.objects.get_or_create(user=request.user)
        cart = {str(item.product_id): item.quantity for item in persistent.items.all()}
    active_ids = {str(pk) for pk in Product.objects.filter(
        is_active=True, pk__in=cart.keys()
    ).values_list("pk", flat=True)}
    cart_count = 0
    for product_id, value in cart.items():
        if str(product_id) not in active_ids:
            continue
        try:
            cart_count += max(0, int(value))
        except (TypeError, ValueError):
            continue
    return {
        "wishlist_count": wishlist_count,
        "cart_count": cart_count,
        "unread_notification_count": unread_notification_count,
    }

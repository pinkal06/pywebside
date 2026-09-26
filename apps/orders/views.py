from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Q
from django import forms
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from apps.products.models import Product
from apps.notifications.utils import notify
from apps.notifications.whatsapp_service import send_whatsapp_message

from .forms import CheckoutForm, OrderForm, PickupScheduleForm, SellerAvailabilityForm
from .models import Cart, Order, PickupSchedule, SellerAvailability
from apps.chat.models import Conversation


def _verified_active(request):
    profile = getattr(request.user, "profile", None)
    return bool(
        request.user.is_authenticated
        and request.user.is_active
        and profile
        and profile.is_active
        and profile.is_email_verified
    )


@login_required
def place_order(request, product_pk):
    product = get_object_or_404(Product.objects.select_related("owner"), pk=product_pk, is_active=True)
    if not _verified_active(request):
        messages.error(request, "Please verify your email and keep your profile active to place an order.")
        return redirect("profile")
    if product.owner_id == request.user.id:
        messages.error(request, "You cannot place an order for your own product.")
        return redirect(product)
    if Order.objects.filter(
        product=product,
        buyer=request.user,
        status__in=[Order.PENDING, Order.ACCEPTED],
    ).exists():
        messages.info(request, "You already have an active order for this product.")
        return redirect("buyer_orders")

    form = OrderForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            product = Product.objects.select_for_update().get(pk=product.pk)
            if product.stock_quantity < form.cleaned_data["quantity"]:
                form.add_error("quantity", f"Only {product.stock_quantity} available.")
                return render(request, "orders/place_order.html", {
                    "form": form, "product": product, "page_title": "Place order",
                })
            order = form.save(commit=False)
            order.product = product
            order.buyer = request.user
            order.seller = product.owner
            order.total_price = product.price * order.quantity
            product.stock_quantity -= order.quantity
            product.save(update_fields=["stock_quantity", "updated_at"])
            order.save()
        notify(
            order.seller,
            f"New order #{order.pk} for {product.title}.",
            "order_detail",
            {"pk": order.pk},
        )
        send_whatsapp_message(request.user, "ORDER_CONFIRMED", reference=order)
        send_whatsapp_message(order.seller, "ORDER_CONFIRMED", reference=order)
        messages.success(request, "Order placed successfully.")
        return redirect("buyer_orders")
    return render(request, "orders/place_order.html", {
        "form": form, "product": product, "page_title": "Place order",
    })


@login_required
def buyer_orders(request):
    if not _verified_active(request):
        messages.error(request, "Please verify your email and keep your profile active to view orders.")
        return redirect("profile")
    orders = Order.objects.filter(buyer=request.user).select_related("product", "seller")
    return render(request, "orders/buyer_orders.html", {"orders": orders, "page_title": "My orders"})


@login_required
def checkout(request):
    if not _verified_active(request):
        messages.error(request, "Please verify your email and keep your profile active to checkout.")
        return redirect("profile")
    cart = Cart.objects.filter(user=request.user).prefetch_related("items__product").first()
    items = list(cart.items.select_related("product", "product__owner").all()) if cart else []
    if not items:
        messages.info(request, "Your cart is empty.")
        return redirect("cart")
    form = CheckoutForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            locked_cart = Cart.objects.select_for_update().get(user=request.user)
            locked_items = list(locked_cart.items.select_related("product").all())
            if not locked_items:
                return redirect("cart")
            products = {}
            for item in locked_items:
                product = Product.objects.select_for_update().get(pk=item.product_id)
                if not product.is_active or product.owner_id == request.user.id or product.stock_quantity < item.quantity:
                    messages.error(request, f"{product.title} no longer has enough stock.")
                    return redirect("cart")
                products[item.product_id] = product
            address = form.cleaned_data["shipping_address"]
            for item in locked_items:
                product = products[item.product_id]
                order = Order.objects.create(
                    product=product, buyer=request.user, seller=product.owner,
                    quantity=item.quantity, total_price=product.price * item.quantity,
                    shipping_address=address,
                )
                notify(
                    order.seller,
                    f"New order #{order.pk} for {product.title}.",
                    "order_detail",
                    {"pk": order.pk},
                )
                send_whatsapp_message(order.buyer, "ORDER_CONFIRMED", reference=order)
                send_whatsapp_message(order.seller, "ORDER_CONFIRMED", reference=order)
                product.stock_quantity -= item.quantity
                product.save(update_fields=["stock_quantity", "updated_at"])
            locked_cart.items.all().delete()
        return redirect("order_confirmation")
    total = sum(item.product.price * item.quantity for item in items)
    return render(request, "orders/checkout.html", {
        "form": form, "items": items, "cart_total": total, "page_title": "Checkout",
    })


@login_required
def order_confirmation(request):
    order = Order.objects.filter(buyer=request.user).select_related("product").first()
    return render(request, "orders/order_confirmation.html", {"order": order, "page_title": "Order confirmed"})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("product", "buyer", "seller"), pk=pk)
    if request.user.id not in (order.buyer_id, order.seller_id):
        raise PermissionDenied
    return render(request, "orders/order_detail.html", {"order": order, "page_title": f"Order #{order.pk}"})


@login_required
def seller_orders(request):
    if not _verified_active(request):
        messages.error(request, "Please verify your email and keep your profile active to view orders.")
        return redirect("profile")
    orders = Order.objects.filter(seller=request.user).select_related("product", "buyer")
    return render(request, "orders/seller_orders.html", {"orders": orders, "page_title": "Received orders"})


@login_required
def update_order_status(request, pk):
    order = get_object_or_404(Order.objects.select_related("product"), pk=pk)
    if order.seller_id != request.user.id:
        raise PermissionDenied
    if not _verified_active(request):
        messages.error(request, "Please verify your email and keep your profile active to manage orders.")
        return redirect("profile")
    if request.method != "POST":
        return redirect("seller_orders")
    status = request.POST.get("status")
    allowed = {Order.ACCEPTED, Order.REJECTED, Order.COMPLETED, Order.CANCELLED}
    if status not in allowed:
        messages.error(request, "That order status is not available.")
    else:
        order.status = status
        order.save(update_fields=["status", "updated_at"])
        notify(
            order.buyer,
            f"Order #{order.pk} is now {order.get_status_display().lower()}.",
            "order_detail",
            {"pk": order.pk},
        )
        messages.success(request, "Order status updated.")
    return redirect("seller_orders")


def _seller_required(request):
    profile = getattr(request.user, "profile", None)
    if not profile or profile.role != "SELLER" or not profile.is_active:
        raise PermissionDenied


def _pickup_allowed(seller, pickup_date, pickup_time):
    return SellerAvailability.objects.filter(
        seller=seller, weekday=pickup_date.weekday(), is_active=True,
        start_time__lte=pickup_time, end_time__gte=pickup_time,
    ).first()


@login_required
def pickup_list(request):
    schedules = PickupSchedule.objects.filter(
        Q(buyer=request.user) | Q(seller=request.user)
    ).select_related("product", "buyer", "seller", "conversation")
    return render(request, "orders/pickup_list.html", {
        "schedules": schedules, "page_title": "My pickups",
    })


@login_required
def availability_list(request):
    _seller_required(request)
    availability = SellerAvailability.objects.filter(seller=request.user)
    form = SellerAvailabilityForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        item = form.save(commit=False)
        item.seller = request.user
        item.save()
        messages.success(request, "Pickup availability added.")
        return redirect("availability_list")
    return render(request, "orders/availability_list.html", {
        "availability": availability, "form": form, "page_title": "Pickup availability",
    })


@login_required
def availability_delete(request, pk):
    _seller_required(request)
    item = get_object_or_404(SellerAvailability, pk=pk, seller=request.user)
    if request.method == "POST":
        item.delete()
        messages.success(request, "Pickup availability removed.")
    return redirect("availability_list")


@login_required
def pickup_request(request, conversation_pk):
    conversation = get_object_or_404(
        Conversation.objects.select_related("product", "buyer", "seller"),
        pk=conversation_pk,
    )
    if request.user.id != conversation.buyer_id:
        raise PermissionDenied
    if not conversation.product_id or not conversation.product.is_active or conversation.product.stock_quantity < 1:
        messages.error(request, "Pickup is unavailable because this product is no longer available.")
        return redirect("conversation_detail", pk=conversation.pk)
    form = PickupScheduleForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        pickup_date = form.cleaned_data["pickup_date"]
        pickup_time = form.cleaned_data["pickup_time"]
        if timezone.localdate() > pickup_date or (
            pickup_date == timezone.localdate() and pickup_time <= timezone.localtime().time()
        ):
            form.add_error(None, "Choose a future date and time.")
        else:
            availability = _pickup_allowed(conversation.seller, pickup_date, pickup_time)
            if not availability:
                form.add_error(None, "That time is outside the seller's available pickup hours.")
            elif PickupSchedule.objects.filter(
                buyer=request.user, seller=conversation.seller, product=conversation.product
            ).exclude(status__in=PickupSchedule.INACTIVE_STATUSES).exists():
                form.add_error(None, "You already have an active pickup request for this product.")
            else:
                schedule = form.save(commit=False)
                schedule.product = conversation.product
                schedule.buyer = request.user
                schedule.seller = conversation.seller
                schedule.conversation = conversation
                schedule.pickup_location = availability.pickup_location
                schedule.save()
                notify(conversation.seller, f"Buyer requested pickup for {conversation.product.title}.", "pickup_detail", {"pk": schedule.pk})
                notify(request.user, "Your pickup request was sent to the seller.", "pickup_detail", {"pk": schedule.pk})
                return redirect("pickup_detail", pk=schedule.pk)
    availability = SellerAvailability.objects.filter(seller=conversation.seller, is_active=True)
    return render(request, "orders/pickup_form.html", {
        "form": form, "conversation": conversation, "availability": availability,
        "page_title": "Schedule pickup",
    })


@login_required
def pickup_detail(request, pk):
    schedule = get_object_or_404(
        PickupSchedule.objects.select_related("product", "buyer", "seller", "conversation"), pk=pk
    )
    if request.user.id not in (schedule.buyer_id, schedule.seller_id):
        raise PermissionDenied
    if request.method == "POST":
        action = request.POST.get("action")
        seller_action = request.user.id == schedule.seller_id
        active_statuses = (PickupSchedule.PENDING, PickupSchedule.CONFIRMED, PickupSchedule.TIME_CHANGE_REQUESTED)
        if action == "confirm" and seller_action and schedule.status in (PickupSchedule.PENDING, PickupSchedule.TIME_CHANGE_REQUESTED):
            schedule.mark_confirmed()
            schedule.save(update_fields=("status", "confirmed_at", "updated_at"))
            notify(schedule.buyer, "Your pickup was confirmed.", "pickup_detail", {"pk": schedule.pk})
        elif action == "reject" and seller_action and schedule.status in (PickupSchedule.PENDING, PickupSchedule.TIME_CHANGE_REQUESTED):
            schedule.status = PickupSchedule.REJECTED
            schedule.seller_message = request.POST.get("message", "").strip()[:1000]
            schedule.save(update_fields=("status", "seller_message", "updated_at"))
            notify(schedule.buyer, "Your pickup request was rejected.", "pickup_detail", {"pk": schedule.pk})
        elif action == "cancel" and schedule.status in active_statuses:
            schedule.status = PickupSchedule.CANCELLED
            schedule.cancelled_at = timezone.now()
            schedule.save(update_fields=("status", "cancelled_at", "updated_at"))
            other = schedule.seller if request.user.id == schedule.buyer_id else schedule.buyer
            notify(other, "A pickup request was cancelled.", "pickup_detail", {"pk": schedule.pk})
        elif action == "reminder" and seller_action and schedule.status in (PickupSchedule.CONFIRMED, PickupSchedule.TIME_CHANGE_REQUESTED):
            schedule.reminder_sent_at = timezone.now()
            schedule.seller_message = request.POST.get("message", "").strip()[:1000] or "This is a reminder for the scheduled pickup."
            schedule.save(update_fields=("reminder_sent_at", "seller_message", "updated_at"))
            notify(schedule.buyer, "Seller sent a pickup reminder.", "pickup_detail", {"pk": schedule.pk})
        elif action == "complete" and schedule.status == PickupSchedule.CONFIRMED:
            schedule.mark_completed()
            schedule.save(update_fields=("status", "completed_at", "updated_at"))
            other = schedule.seller if request.user.id == schedule.buyer_id else schedule.buyer
            notify(other, "Pickup was marked completed.", "pickup_detail", {"pk": schedule.pk})
        elif action == "suggest" and seller_action and schedule.status in (PickupSchedule.PENDING, PickupSchedule.TIME_CHANGE_REQUESTED):
            try:
                new_date = forms.DateField().clean(request.POST.get("pickup_date"))
                new_time = forms.TimeField().clean(request.POST.get("pickup_time"))
            except forms.ValidationError:
                messages.error(request, "Enter a valid suggested date and time.")
            else:
                availability = _pickup_allowed(schedule.seller, new_date, new_time)
                if not availability:
                    messages.error(request, "Suggested time is outside your availability.")
                else:
                    schedule.pickup_date = new_date
                    schedule.pickup_time = new_time
                    schedule.pickup_location = availability.pickup_location
                    schedule.seller_message = request.POST.get("message", "").strip()[:1000]
                    schedule.status = PickupSchedule.TIME_CHANGE_REQUESTED
                    schedule.save()
                    notify(schedule.buyer, "The seller suggested another pickup time.", "pickup_detail", {"pk": schedule.pk})
        elif action == "accept_change" and request.user.id == schedule.buyer_id and schedule.status == PickupSchedule.TIME_CHANGE_REQUESTED:
            schedule.mark_confirmed()
            schedule.save(update_fields=("status", "confirmed_at", "updated_at"))
            notify(schedule.seller, "Buyer accepted the suggested pickup time.", "pickup_detail", {"pk": schedule.pk})
        return redirect("pickup_detail", pk=schedule.pk)
    return render(request, "orders/pickup_detail.html", {"schedule": schedule, "page_title": "Pickup details"})

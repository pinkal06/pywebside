import json

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from apps.categories.models import Category
from .forms import ProductForm
from .models import Product, Wishlist
from apps.orders.models import Cart, CartItem
from apps.notifications.utils import notify
from apps.notifications.whatsapp_service import send_whatsapp_message


def product_list(request):
    products = Product.objects.filter(is_active=True).select_related("category", "owner")
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    condition = request.GET.get("condition", "").strip()
    if query:
        products = products.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(category__name__icontains=query)
            | Q(owner__profile__full_name__icontains=query)
        )
    if category:
        products = products.filter(category__slug=category)
    if condition:
        products = products.filter(condition=condition)
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(Wishlist.objects.filter(user=request.user, product__in=products).values_list("product_id", flat=True))
    return render(request, "products/product_list.html", {
        "products": products, "wishlist_ids": wishlist_ids, "query": query, "selected_category": category,
        "selected_condition": condition, "product_conditions": Product.CONDITION_CHOICES,
        "categories": Category.objects.filter(is_active=True),
        "page_title": "Products",
    })


def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("category", "owner"), pk=pk, is_active=True)
    is_wishlisted = request.user.is_authenticated and Wishlist.objects.filter(
        user=request.user, product=product
    ).exists()
    return render(request, "products/product_detail.html", {
        "product": product,
        "is_wishlisted": is_wishlisted,
        "page_title": f"{product.title} | RetiyaBazar",
        "meta_description": product.description[:160],
        "product_schema": json.dumps({
            "@context": "https://schema.org",
            "@type": "Product",
            "name": product.title,
            "description": product.description,
            "category": product.category.name,
            "offers": {
                "@type": "Offer",
                "priceCurrency": "INR",
                "price": str(product.price),
                "availability": (
                    "https://schema.org/InStock"
                    if product.stock_quantity > 0
                    else "https://schema.org/OutOfStock"
                ),
                "url": request.build_absolute_uri(product.get_absolute_url()),
            },
        }),
    })


def _verified(request):
    profile = getattr(request.user, "profile", None)
    return (
        request.user.is_authenticated
        and request.user.is_active
        and profile
        and profile.is_active
        and profile.is_email_verified
    )


@login_required
def product_create(request):
    if not _verified(request):
        messages.error(request, "Please verify your email before listing a product.")
        return redirect("profile")
    selected_category = request.GET.get("category")
    initial = {"category": selected_category} if selected_category else {}
    form = ProductForm(request.POST or None, request.FILES or None, initial=initial)
    if form.is_valid():
        product = form.save(commit=False)
        product.owner = request.user
        product.save()
        send_whatsapp_message(product.owner, "PRODUCT_ADDED", reference=product)
        messages.success(request, "Product listed successfully.")
        return redirect(product)
    return render(request, "products/product_form.html", {"form": form, "page_title": "Sell a product"})


@login_required
def product_update(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.owner_id != request.user.id:
        raise PermissionDenied
    form = ProductForm(request.POST or None, request.FILES or None, instance=product)
    if form.is_valid():
        form.save()
        # Keep interested buyers informed without exposing product ownership.
        recipients = set(
            product.conversations.values_list("buyer_id", flat=True)
        ) | set(product.wishlist_items.values_list("user_id", flat=True))
        from django.contrib.auth import get_user_model
        for user in get_user_model().objects.filter(pk__in=recipients).exclude(pk=request.user.pk):
            notify(user, f"Product updated: {product.title}", "product_detail", {"pk": product.pk})
        messages.success(request, "Product updated.")
        return redirect(product)
    return render(request, "products/product_form.html", {"form": form, "product": product, "page_title": "Edit product"})


@login_required
def product_delete(request, pk):
    product = get_object_or_404(Product, pk=pk)
    if product.owner_id != request.user.id:
        raise PermissionDenied
    if request.method == "POST":
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect("product_list")
    return render(request, "products/product_confirm_delete.html", {"product": product, "page_title": "Delete product"})


def _verified_active(request):
    if not request.user.is_authenticated:
        return False
    profile = getattr(request.user, "profile", None)
    return bool(request.user.is_active and profile and profile.is_active and profile.is_email_verified)


def _require_verified(request):
    if not _verified_active(request):
        messages.error(request, "Please verify your active account before using your wishlist.")
        return redirect("login" if not request.user.is_authenticated else "profile")
    return None


@login_required
def wishlist_list(request):
    denied = _require_verified(request)
    if denied:
        return denied
    items = Wishlist.objects.filter(user=request.user).select_related(
        "product", "product__category", "product__owner"
    )
    query = request.GET.get("q", "").strip()
    category = request.GET.get("category", "").strip()
    availability = request.GET.get("availability", "").strip()
    sort = request.GET.get("sort", "recent").strip()
    if query:
        items = items.filter(Q(product__title__icontains=query) | Q(product__description__icontains=query))
    if category:
        items = items.filter(product__category__slug=category)
    if availability == "available":
        items = items.filter(product__is_active=True, product__stock_quantity__gt=0)
    elif availability == "sold_out":
        items = items.filter(product__stock_quantity=0)
    elif availability == "unavailable":
        items = items.filter(product__is_active=False)
    sort_fields = {
        "price_low": "product__price",
        "price_high": "-product__price",
        "name_az": "product__title",
        "name_za": "-product__title",
    }
    items = items.order_by(sort_fields.get(sort, "-created_at"))
    page_obj = Paginator(items, 20).get_page(request.GET.get("page"))
    wishlisted_ids = set(
        Wishlist.objects.filter(user=request.user).values_list("product_id", flat=True)
    )
    recommendations = Product.objects.filter(is_active=True, stock_quantity__gt=0).exclude(
        pk__in=wishlisted_ids
    ).select_related("category", "owner").order_by("-created_at")[:4]
    return render(request, "products/wishlist.html", {
        "page_obj": page_obj,
        "items": page_obj.object_list,
        "categories": Category.objects.filter(is_active=True),
        "recommendations": recommendations,
        "query": query,
        "category": category,
        "availability": availability,
        "sort": sort,
        "page_title": "My Wishlist",
    })


@login_required
def wishlist_add(request, pk):
    denied = _require_verified(request)
    if denied:
        return denied
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if product.owner_id == request.user.id:
        messages.error(request, "You cannot add your own product to your wishlist.")
    else:
        Wishlist.objects.get_or_create(user=request.user, product=product)
        messages.success(request, "Product added to your wishlist.")
    return redirect(request.POST.get("next") or product.get_absolute_url())


@login_required
def wishlist_remove(request, pk):
    denied = _require_verified(request)
    if denied:
        return denied
    Wishlist.objects.filter(user=request.user, product_id=pk).delete()
    messages.success(request, "Product removed from your wishlist.")
    return redirect(request.POST.get("next") or "wishlist")


@login_required
def wishlist_move_to_cart(request, pk):
    denied = _require_verified(request)
    if denied:
        return denied
    if request.method != "POST":
        return redirect("wishlist")
    with transaction.atomic():
        item = Wishlist.objects.select_related("product").filter(user=request.user, product_id=pk).first()
        if not item:
            messages.error(request, "This product is not in your wishlist.")
            return redirect("wishlist")
        product = item.product
        if not product.is_active or product.stock_quantity < 1 or not _can_shop(request, product):
            messages.error(request, "This product is currently unavailable.")
            return redirect("wishlist")
        cart = _cart(request)
        cart[str(product.pk)] = min(99, product.stock_quantity, int(cart.get(str(product.pk), 0)) + 1)
        _save_cart(request, cart)
        item.delete()
    messages.success(request, "Product moved to your cart.")
    return redirect("wishlist")


def _cart(request):
    if request.user.is_authenticated:
        cart, _ = Cart.objects.get_or_create(user=request.user)
        session_cart = request.session.get("cart", {})
        for product_id, quantity in session_cart.items():
            try:
                quantity = max(1, int(quantity))
            except (TypeError, ValueError):
                continue
            product = Product.objects.filter(pk=product_id, is_active=True).first()
            if product and product.owner_id != request.user.id and product.stock_quantity:
                item, _ = CartItem.objects.get_or_create(cart=cart, product=product)
                item.quantity = min(99, product.stock_quantity, item.quantity + quantity)
                item.save(update_fields=["quantity"])
        if session_cart:
            request.session.pop("cart", None)
        return {str(item.product_id): item.quantity for item in cart.items.all()}
    return request.session.get("cart", {})


def _save_cart(request, cart):
    if request.user.is_authenticated:
        persistent, _ = Cart.objects.get_or_create(user=request.user)
        persistent.items.exclude(product_id__in=cart.keys()).delete()
        for product_id, quantity in cart.items():
            CartItem.objects.update_or_create(
                cart=persistent, product_id=product_id,
                defaults={"quantity": quantity},
            )
        return
    request.session["cart"] = cart
    request.session.modified = True


def _can_shop(request, product):
    return product.owner_id != request.user.id if request.user.is_authenticated else True


def cart_summary(request):
    cart = _cart(request)
    products = Product.objects.filter(id__in=cart.keys(), is_active=True).select_related("category", "owner")
    items = []
    valid_ids = set()
    total = 0
    for product in products:
        if not _can_shop(request, product):
            continue
        try:
            quantity = max(1, min(int(cart.get(str(product.pk), 1)), product.stock_quantity, 99))
        except (TypeError, ValueError):
            quantity = 1
        valid_ids.add(str(product.pk))
        line_total = product.price * quantity
        total += line_total
        items.append({"product": product, "quantity": quantity, "line_total": line_total})
    if set(cart) != valid_ids:
        _save_cart(request, {key: cart[key] for key in valid_ids})
    return render(request, "products/cart.html", {
        "items": items, "cart_total": total, "page_title": "Cart",
    })


def cart_add(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    if not _can_shop(request, product):
        messages.error(request, "You cannot add your own product to your cart.")
        return redirect(request.POST.get("next") or product.get_absolute_url())
    try:
        quantity = max(1, min(int(request.POST.get("quantity", 1)), 99))
    except (TypeError, ValueError):
        quantity = 1
    cart = _cart(request)
    current = int(cart.get(str(product.pk), 0))
    if product.stock_quantity < 1:
        messages.error(request, "This product is out of stock.")
        return redirect(request.POST.get("next") or product.get_absolute_url())
    cart[str(product.pk)] = min(99, product.stock_quantity, current + quantity)
    _save_cart(request, cart)
    messages.success(request, "Product added to your cart.")
    return redirect(request.POST.get("next") or "cart")


def cart_remove(request, pk):
    cart = _cart(request)
    cart.pop(str(pk), None)
    _save_cart(request, cart)
    messages.success(request, "Product removed from your cart.")
    return redirect("cart")


def cart_update(request):
    cart = _cart(request)
    for key, value in request.POST.items():
        if not key.startswith("quantity_"):
            continue
        product_id = key.removeprefix("quantity_")
        if product_id not in cart:
            continue
        try:
            quantity = int(value)
        except (TypeError, ValueError):
            quantity = 1
        if quantity <= 0:
            cart.pop(product_id, None)
        else:
            stock = Product.objects.filter(pk=product_id, is_active=True).values_list("stock_quantity", flat=True).first()
            if stock is None or stock < 1:
                cart.pop(product_id, None)
            else:
                cart[product_id] = min(quantity, stock, 99)
    _save_cart(request, cart)
    messages.success(request, "Cart updated.")
    return redirect("cart")
    if request.method != "POST":
        return redirect("product_detail", pk=pk)
    if request.method != "POST":
        return redirect("wishlist")

import json
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.text import slugify

from apps.accounts.models import Profile
from apps.categories.models import Category
from apps.chat.models import MessageReport
from apps.notifications.models import Notification, WhatsAppNotification
from apps.notifications.whatsapp_service import send_whatsapp_message
from apps.notifications.utils import notify
from apps.orders.models import Order
from apps.products.models import Product, ProductReport
from .models import AuditLog, SecurityLog
from .utils import admin_required, log_audit

User = get_user_model()


def paginate_queryset(request, queryset, per_page=20):
    paginator = Paginator(queryset, per_page)
    page_number = request.GET.get("page")
    return paginator.get_page(page_number)


# ==============================================================================
# 1. DASHBOARD & CHARTS
# ==============================================================================
@admin_required
def dashboard(request):
    total_users = User.objects.count()
    total_buyers = Profile.objects.filter(role=Profile.ROLE_BUYER).count()
    total_sellers = Profile.objects.filter(role=Profile.ROLE_SELLER).count()

    total_products = Product.objects.count()
    active_products = Product.objects.filter(is_active=True, status=Product.STATUS_ACTIVE).count()
    pending_products = Product.objects.filter(status=Product.STATUS_PENDING).count()
    sold_out_products = Product.objects.filter(stock_quantity=0).count()

    total_orders = Order.objects.count()
    pending_orders = Order.objects.filter(status=Order.PENDING).count()
    completed_orders = Order.objects.filter(status__in=[Order.DELIVERED, Order.COMPLETED]).count()
    cancelled_orders = Order.objects.filter(status=Order.CANCELLED).count()
    total_revenue = float(Order.objects.exclude(status=Order.CANCELLED).aggregate(total=Sum("total_price"))["total"] or 0)
    avg_order_value = float(Order.objects.exclude(status=Order.CANCELLED).aggregate(total=Sum("total_price"))["total"] or 0) / total_orders if total_orders else 0
    total_categories = Category.objects.count()
    active_sellers = User.objects.filter(profile__role=Profile.ROLE_SELLER, is_active=True).count()
    low_stock_products = Product.objects.filter(is_active=True, stock_quantity__lt=3).count()
    open_product_reports = ProductReport.objects.filter(status="open").count()
    open_message_reports = MessageReport.objects.filter(status="open").count()
    total_unread_reports = open_product_reports + open_message_reports
    unread_notifications = Notification.objects.filter(is_read=False).count()

    # --- Live Chart Data (Last 7 Days) ---
    today = timezone.now().date()
    date_labels = [(today - timedelta(days=i)).strftime("%b %d") for i in reversed(range(7))]
    days_range = [(today - timedelta(days=i)) for i in reversed(range(7))]

    registrations_data = []
    products_added_data = []
    orders_data = []
    sales_data = []

    for d in days_range:
        reg_count = User.objects.filter(date_joined__date=d).count()
        registrations_data.append(reg_count)

        prod_count = Product.objects.filter(created_at__date=d).count()
        products_added_data.append(prod_count)

        day_orders = Order.objects.filter(created_at__date=d)
        orders_data.append(day_orders.count())

        day_sales = day_orders.exclude(status=Order.CANCELLED).aggregate(total=Sum("total_price"))["total"] or 0
        sales_data.append(float(day_sales))

    # Category Distribution
    category_counts = (
        Category.objects.annotate(product_count=Count("products"))
        .filter(product_count__gt=0)
        .order_by("-product_count")[:8]
    )
    category_labels = [c.name for c in category_counts]
    category_product_data = [c.product_count for c in category_counts]

    recent_pending_products = (
        Product.objects.filter(status=Product.STATUS_PENDING)
        .select_related("owner", "category")
        .order_by("-created_at")[:5]
    )

    recent_orders = (
        Order.objects.select_related("buyer", "seller", "product")
        .order_by("-created_at")[:5]
    )

    top_sellers = (
        User.objects.filter(profile__role=Profile.ROLE_SELLER, is_active=True)
        .annotate(sales=Sum("received_orders__total_price"))
        .order_by("-sales")[:5]
    )

    low_stock_items = (
        Product.objects.filter(is_active=True, stock_quantity__lt=3)
        .select_related("owner", "category")
        .order_by("stock_quantity", "-created_at")[:5]
    )

    recent_product_reports = (
        ProductReport.objects.filter(status="open")
        .select_related("product", "reported_by")
        .order_by("-created_at")[:5]
    )
    recent_message_reports = (
        MessageReport.objects.filter(status="open")
        .select_related("message", "reported_by")
        .order_by("-created_at")[:5]
    )

    recent_audits = AuditLog.objects.select_related("user").order_by("-created_at")[:5]

    context = {
        "page_title": "Admin Dashboard",
        "total_users": total_users,
        "total_buyers": total_buyers,
        "total_sellers": total_sellers,
        "total_products": total_products,
        "active_products": active_products,
        "pending_products": pending_products,
        "sold_out_products": sold_out_products,
        "total_orders": total_orders,
        "pending_orders": pending_orders,
        "completed_orders": completed_orders,
        "cancelled_orders": cancelled_orders,
        "total_categories": total_categories,
        "active_sellers": active_sellers,
        "low_stock_products": low_stock_products,
        "total_revenue": total_revenue,
        "avg_order_value": avg_order_value,
        "total_unread_reports": total_unread_reports,
        "open_product_reports": open_product_reports,
        "open_message_reports": open_message_reports,
        "unread_notifications": unread_notifications,
        "recent_pending_products": recent_pending_products,
        "recent_orders": recent_orders,
        "top_sellers": top_sellers,
        "low_stock_items": low_stock_items,
        "recent_product_reports": recent_product_reports,
        "recent_message_reports": recent_message_reports,
        "recent_audits": recent_audits,
        # JSON serialized chart payloads
        "chart_dates": json.dumps(date_labels),
        "chart_registrations": json.dumps(registrations_data),
        "chart_products": json.dumps(products_added_data),
        "chart_orders": json.dumps(orders_data),
        "chart_sales": json.dumps(sales_data),
        "chart_category_labels": json.dumps(category_labels),
        "chart_category_data": json.dumps(category_product_data),
    }
    return render(request, "admin_panel/dashboard.html", context)


# ==============================================================================
# 2. USER MANAGEMENT
# ==============================================================================
@admin_required
def user_list(request):
    users = (
        User.objects.select_related("profile")
        .annotate(
            product_count=Count("products", distinct=True),
            order_count=Count("orders", distinct=True),
        )
        .order_by("-date_joined")
    )

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    role_filter = request.GET.get("role", "").strip()

    if query:
        users = users.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__full_name__icontains=query)
            | Q(profile__mobile_number__icontains=query)
        )

    if status_filter == "active":
        users = users.filter(is_active=True)
    elif status_filter == "inactive":
        users = users.filter(is_active=False)

    if role_filter == "BUYER":
        users = users.filter(profile__role=Profile.ROLE_BUYER)
    elif role_filter == "SELLER":
        users = users.filter(profile__role=Profile.ROLE_SELLER)
    elif role_filter == "ADMIN":
        users = users.filter(Q(is_superuser=True) | Q(is_staff=True) | Q(profile__role=Profile.ROLE_ADMIN))

    page_obj = paginate_queryset(request, users, per_page=20)

    context = {
        "page_title": "User Management",
        "page_obj": page_obj,
        "query": query,
        "status_filter": status_filter,
        "role_filter": role_filter,
    }
    return render(request, "admin_panel/users/user_list.html", context)


@admin_required
def user_detail(request, pk):
    target_user = get_object_or_404(
        User.objects.select_related("profile").annotate(
            product_count=Count("products", distinct=True),
            order_count=Count("orders", distinct=True),
        ),
        pk=pk,
    )
    products = Product.objects.filter(owner=target_user).select_related("category")[:10]
    orders = Order.objects.filter(buyer=target_user).select_related("product")[:10]

    context = {
        "page_title": f"User: {target_user.username}",
        "target_user": target_user,
        "products": products,
        "orders": orders,
    }
    return render(request, "admin_panel/users/user_detail.html", context)


@admin_required
def user_toggle_status(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:user_list")

    target_user = get_object_or_404(User.objects.select_related("profile"), pk=pk)

    # Super Admin Protection
    if target_user.is_superuser and target_user.is_active:
        active_superusers = User.objects.filter(is_superuser=True, is_active=True).count()
        if active_superusers <= 1:
            messages.error(
                request,
                "Security Protection: Cannot deactivate the final active super administrator account.",
            )
            return redirect(request.POST.get("next") or "admin_panel:user_list")

    new_status = not target_user.is_active
    target_user.is_active = new_status
    target_user.save(update_fields=["is_active"])

    if hasattr(target_user, "profile"):
        target_user.profile.is_active = new_status
        target_user.profile.save(update_fields=["is_active"])

    action_label = "ACTIVATED" if new_status else "DEACTIVATED"
    log_audit(
        request,
        action=f"USER_{action_label}",
        object_type="User",
        object_id=target_user.pk,
        description=f"Admin {request.user.username} {action_label.lower()} user {target_user.username} (ID: {target_user.pk})",
    )

    messages.success(request, f"User {target_user.username} successfully {action_label.lower()}.")
    return redirect(request.POST.get("next") or "admin_panel:user_list")


# ==============================================================================
# 3. SELLER MANAGEMENT
# ==============================================================================
@admin_required
def seller_list(request):
    sellers = (
        User.objects.filter(Q(profile__role=Profile.ROLE_SELLER) | Q(products__isnull=False))
        .distinct()
        .select_related("profile")
        .annotate(
            total_products=Count("products", distinct=True),
            active_products=Count("products", filter=Q(products__is_active=True, products__status=Product.STATUS_ACTIVE), distinct=True),
            orders_received=Count("received_orders", distinct=True),
        )
        .order_by("-date_joined")
    )

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if query:
        sellers = sellers.filter(
            Q(username__icontains=query)
            | Q(email__icontains=query)
            | Q(profile__full_name__icontains=query)
            | Q(profile__mobile_number__icontains=query)
        )

    if status_filter == "active":
        sellers = sellers.filter(is_active=True)
    elif status_filter == "inactive":
        sellers = sellers.filter(is_active=False)

    page_obj = paginate_queryset(request, sellers, per_page=20)

    context = {
        "page_title": "Seller Management",
        "page_obj": page_obj,
        "query": query,
        "status_filter": status_filter,
    }
    return render(request, "admin_panel/sellers/seller_list.html", context)


# ==============================================================================
# 4. PRODUCT MANAGEMENT & APPROVALS
# ==============================================================================
@admin_required
def product_list(request):
    products = Product.objects.select_related("owner", "category").order_by("-created_at")

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()
    category_filter = request.GET.get("category", "").strip()

    if query:
        products = products.filter(
            Q(title__icontains=query)
            | Q(description__icontains=query)
            | Q(owner__username__icontains=query)
            | Q(owner__email__icontains=query)
        )

    if status_filter == "pending":
        products = products.filter(status=Product.STATUS_PENDING)
    elif status_filter == "active":
        products = products.filter(status=Product.STATUS_ACTIVE, is_active=True)
    elif status_filter == "rejected":
        products = products.filter(status=Product.STATUS_REJECTED)
    elif status_filter == "inactive":
        products = products.filter(is_active=False)

    if category_filter:
        products = products.filter(category__slug=category_filter)

    categories = Category.objects.filter(is_active=True)
    page_obj = paginate_queryset(request, products, per_page=20)

    context = {
        "page_title": "Product Management",
        "page_obj": page_obj,
        "categories": categories,
        "query": query,
        "status_filter": status_filter,
        "category_filter": category_filter,
    }
    return render(request, "admin_panel/products/product_list.html", context)


@admin_required
def product_detail(request, pk):
    product = get_object_or_404(Product.objects.select_related("owner", "category"), pk=pk)
    reports = product.reports.select_related("reported_by").order_by("-created_at")
    recent_orders = product.orders.select_related("buyer").order_by("-created_at")[:5]

    context = {
        "page_title": f"Product: {product.title}",
        "product": product,
        "reports": reports,
        "recent_orders": recent_orders,
    }
    return render(request, "admin_panel/products/product_detail.html", context)


@admin_required
def product_approve(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:product_list")

    product = get_object_or_404(Product.objects.select_related("owner"), pk=pk)
    if product.status != Product.STATUS_PENDING:
        messages.error(request, "Only pending products can be approved.")
        return redirect(request.POST.get("next") or "admin_panel:product_list")

    product.status = Product.STATUS_ACTIVE
    product.is_active = True
    product.rejection_reason = ""
    product.save(update_fields=["status", "is_active", "rejection_reason", "updated_at"])

    # Notify Seller
    notify(
        user=product.owner,
        message=f'Your product "{product.title}" has been approved and is now active.',
        url_name="product_detail",
        kwargs={"pk": product.pk},
    )
    send_whatsapp_message(product.owner, "PRODUCT_APPROVED", reference=product)

    log_audit(
        request,
        action="PRODUCT_APPROVED",
        object_type="Product",
        object_id=product.pk,
        description=f"Admin approved product '{product.title}' (ID: {product.pk}) belonging to {product.owner.username}",
    )

    messages.success(request, f'Product "{product.title}" approved successfully.')
    return redirect(request.POST.get("next") or "admin_panel:product_list")


@admin_required
def product_reject(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:product_list")

    product = get_object_or_404(Product.objects.select_related("owner"), pk=pk)
    if product.status != Product.STATUS_PENDING:
        messages.error(request, "Only pending products can be rejected.")
        return redirect(request.POST.get("next") or "admin_panel:product_list")

    reason = request.POST.get("reason", "").strip()

    if not reason:
        messages.error(request, "Rejection reason is required.")
        return redirect(request.POST.get("next") or "admin_panel:product_list")

    product.status = Product.STATUS_REJECTED
    product.is_active = False
    product.rejection_reason = reason
    product.save(update_fields=["status", "is_active", "rejection_reason", "updated_at"])

    # Notify Seller
    notify(
        user=product.owner,
        message=f'Your product "{product.title}" requires changes: {reason}',
        url_name="product_detail",
        kwargs={"pk": product.pk},
    )
    send_whatsapp_message(product.owner, "PRODUCT_REJECTED", reference=product)

    log_audit(
        request,
        action="PRODUCT_REJECTED",
        object_type="Product",
        object_id=product.pk,
        description=f"Admin rejected product '{product.title}' (ID: {product.pk}). Reason: {reason}",
    )

    messages.warning(request, f'Product "{product.title}" has been rejected.')
    return redirect(request.POST.get("next") or "admin_panel:product_list")


@admin_required
def product_toggle_status(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:product_list")

    product = get_object_or_404(Product, pk=pk)
    new_active = not product.is_active
    product.is_active = new_active
    if new_active and product.status == Product.STATUS_REJECTED:
        product.status = Product.STATUS_ACTIVE
    product.save(update_fields=["is_active", "status", "updated_at"])

    action_label = "ACTIVATED" if new_active else "DEACTIVATED"
    log_audit(
        request,
        action=f"PRODUCT_{action_label}",
        object_type="Product",
        object_id=product.pk,
        description=f"Admin {action_label.lower()} product '{product.title}' (ID: {product.pk})",
    )

    messages.success(request, f'Product "{product.title}" {action_label.lower()}.')
    return redirect(request.POST.get("next") or "admin_panel:product_list")


# ==============================================================================
# 5. CATEGORY MANAGEMENT
# ==============================================================================
@admin_required
def category_list(request):
    categories = Category.objects.annotate(product_count=Count("products")).order_by("name")
    page_obj = paginate_queryset(request, categories, per_page=20)
    return render(request, "admin_panel/categories/category_list.html", {
        "page_title": "Category Management",
        "page_obj": page_obj,
    })


@admin_required
def category_create(request):
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        slug = request.POST.get("slug", "").strip() or slugify(name)
        description = request.POST.get("description", "").strip()
        is_active = bool(request.POST.get("is_active"))

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin_panel/categories/category_form.html", {
                "name": name, "slug": slug, "description": description, "is_active": is_active,
                "page_title": "Add Category",
            })

        if Category.objects.filter(name__iexact=name).exists():
            messages.error(request, f"A category with name '{name}' already exists.")
            return render(request, "admin_panel/categories/category_form.html", {
                "name": name, "slug": slug, "description": description, "is_active": is_active,
                "page_title": "Add Category",
            })

        category = Category.objects.create(name=name, slug=slug, description=description, is_active=is_active)
        log_audit(request, "CATEGORY_CREATED", "Category", category.pk, f"Created category '{category.name}'")
        messages.success(request, f"Category '{category.name}' created.")
        return redirect("admin_panel:category_list")

    return render(request, "admin_panel/categories/category_form.html", {"page_title": "Add Category", "is_active": True})


@admin_required
def category_edit(request, slug):
    category = get_object_or_404(Category, slug=slug)
    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        new_slug = request.POST.get("slug", "").strip() or slugify(name)
        description = request.POST.get("description", "").strip()
        is_active = bool(request.POST.get("is_active"))

        if not name:
            messages.error(request, "Category name is required.")
            return render(request, "admin_panel/categories/category_form.html", {
                "category": category, "page_title": f"Edit Category: {category.name}",
            })

        if Category.objects.filter(name__iexact=name).exclude(pk=category.pk).exists():
            messages.error(request, f"Another category with name '{name}' already exists.")
            return render(request, "admin_panel/categories/category_form.html", {
                "category": category, "page_title": f"Edit Category: {category.name}",
            })

        category.name = name
        category.slug = new_slug
        category.description = description
        category.is_active = is_active
        category.save()

        log_audit(request, "CATEGORY_UPDATED", "Category", category.pk, f"Updated category '{category.name}'")
        messages.success(request, f"Category '{category.name}' updated.")
        return redirect("admin_panel:category_list")

    return render(request, "admin_panel/categories/category_form.html", {
        "category": category, "page_title": f"Edit Category: {category.name}",
        "name": category.name, "slug": category.slug, "description": category.description, "is_active": category.is_active,
    })


@admin_required
def category_toggle_status(request, slug):
    if request.method != "POST":
        return redirect("admin_panel:category_list")
    category = get_object_or_404(Category, slug=slug)
    category.is_active = not category.is_active
    category.save(update_fields=["is_active", "updated_at"])

    action = "ACTIVATED" if category.is_active else "DEACTIVATED"
    log_audit(request, f"CATEGORY_{action}", "Category", category.pk, f"Category '{category.name}' {action.lower()}")
    messages.success(request, f"Category '{category.name}' {action.lower()}.")
    return redirect("admin_panel:category_list")


@admin_required
def category_delete(request, slug):
    if request.method != "POST":
        return redirect("admin_panel:category_list")

    category = get_object_or_404(Category, slug=slug)
    product_count = category.products.count()

    # Category Delete Protection
    if product_count > 0:
        messages.error(
            request,
            f"Deletion Protected: Category '{category.name}' contains {product_count} products. Reassign or remove products before deleting this category.",
        )
        return redirect("admin_panel:category_list")

    name = category.name
    category.delete()
    log_audit(request, "CATEGORY_DELETED", "Category", "", f"Deleted category '{name}'")
    messages.success(request, f"Category '{name}' deleted successfully.")
    return redirect("admin_panel:category_list")


# ==============================================================================
# 6. ORDER MANAGEMENT
# ==============================================================================
@admin_required
def order_list(request):
    orders = Order.objects.select_related("buyer", "seller", "product").order_by("-created_at")

    query = request.GET.get("q", "").strip()
    status_filter = request.GET.get("status", "").strip()

    if query:
        orders = orders.filter(
            Q(pk__icontains=query.replace("RB-", "").lstrip("0"))
            | Q(buyer__username__icontains=query)
            | Q(buyer__email__icontains=query)
            | Q(product__title__icontains=query)
        )

    if status_filter:
        orders = orders.filter(status=status_filter)

    page_obj = paginate_queryset(request, orders, per_page=20)

    context = {
        "page_title": "Order Management",
        "page_obj": page_obj,
        "query": query,
        "status_filter": status_filter,
        "status_choices": Order.STATUS_CHOICES,
    }
    return render(request, "admin_panel/orders/order_list.html", context)


@admin_required
def order_detail(request, pk):
    order = get_object_or_404(Order.objects.select_related("buyer", "seller", "product"), pk=pk)
    allowed_transitions = order.ALLOWED_TRANSITIONS.get(order.status, [])

    context = {
        "page_title": f"Order #{order.order_number}",
        "order": order,
        "allowed_transitions": allowed_transitions,
    }
    return render(request, "admin_panel/orders/order_detail.html", context)


@admin_required
def order_status_update(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:order_list")

    order = get_object_or_404(Order.objects.select_related("buyer", "seller", "product"), pk=pk)
    new_status = request.POST.get("status", "").strip().lower()

    if not order.can_transition_to(new_status):
        messages.error(
            request,
            f"Invalid status transition from '{order.get_status_display()}' to '{new_status}'.",
        )
        return redirect("admin_panel:order_detail", pk=order.pk)

    old_status = order.status
    order.status = new_status
    order.save(update_fields=["status", "updated_at"])

    # Notify Buyer
    notify(
        user=order.buyer,
        message=f"Your order #{order.order_number} status is now {order.get_status_display()}.",
        url_name="order_detail",
        kwargs={"pk": order.pk},
    )

    log_audit(
        request,
        action="ORDER_STATUS_UPDATED",
        object_type="Order",
        object_id=order.pk,
        description=f"Admin changed order #{order.order_number} status from {old_status} to {new_status}",
    )

    messages.success(request, f"Order status updated to {order.get_status_display()}.")
    return redirect("admin_panel:order_detail", pk=order.pk)


# ==============================================================================
# 7. REPORT MANAGEMENT (MESSAGES & PRODUCTS)
# ==============================================================================
@admin_required
def message_report_list(request):
    reports = MessageReport.objects.select_related("message", "message__sender", "reported_by").order_by("-created_at")

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        reports = reports.filter(status=status_filter)

    page_obj = paginate_queryset(request, reports, per_page=20)

    context = {
        "page_title": "Chat Message Reports",
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": MessageReport.REPORT_STATUS_CHOICES,
    }
    return render(request, "admin_panel/reports/message_reports.html", context)


@admin_required
def message_report_update_status(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:message_report_list")

    report = get_object_or_404(MessageReport, pk=pk)
    new_status = request.POST.get("status", "").strip()
    valid_statuses = dict(MessageReport.REPORT_STATUS_CHOICES).keys()

    if new_status in valid_statuses:
        report.status = new_status
        report.save(update_fields=["status", "updated_at"])
        log_audit(request, "MESSAGE_REPORT_STATUS_CHANGED", "MessageReport", report.pk, f"Status changed to {new_status}")
        messages.success(request, f"Report status updated to {report.get_status_display()}.")
    else:
        messages.error(request, "Invalid report status.")

    return redirect(request.POST.get("next") or "admin_panel:message_report_list")


@admin_required
def product_report_list(request):
    reports = ProductReport.objects.select_related("product", "product__owner", "reported_by").order_by("-created_at")

    status_filter = request.GET.get("status", "").strip()
    if status_filter:
        reports = reports.filter(status=status_filter)

    page_obj = paginate_queryset(request, reports, per_page=20)

    context = {
        "page_title": "Product Reports",
        "page_obj": page_obj,
        "status_filter": status_filter,
        "status_choices": ProductReport.REPORT_STATUS_CHOICES,
    }
    return render(request, "admin_panel/reports/product_reports.html", context)


@admin_required
def product_report_update_status(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:product_report_list")

    report = get_object_or_404(ProductReport, pk=pk)
    new_status = request.POST.get("status", "").strip()
    valid_statuses = dict(ProductReport.REPORT_STATUS_CHOICES).keys()

    if new_status in valid_statuses:
        report.status = new_status
        report.save(update_fields=["status", "updated_at"])
        log_audit(request, "PRODUCT_REPORT_STATUS_CHANGED", "ProductReport", report.pk, f"Status changed to {new_status}")
        messages.success(request, f"Report status updated to {report.get_status_display()}.")
    else:
        messages.error(request, "Invalid report status.")

    return redirect(request.POST.get("next") or "admin_panel:product_report_list")


# ==============================================================================
# 8. AUDIT & SECURITY LOGS
# ==============================================================================
@admin_required
def audit_log_list(request):
    logs = AuditLog.objects.select_related("user").order_by("-created_at")

    query = request.GET.get("q", "").strip()
    action_filter = request.GET.get("action", "").strip()

    if query:
        logs = logs.filter(
            Q(description__icontains=query)
            | Q(object_id__icontains=query)
            | Q(user__username__icontains=query)
            | Q(ip_address__icontains=query)
        )

    if action_filter:
        logs = logs.filter(action=action_filter)

    distinct_actions = AuditLog.objects.values_list("action", flat=True).distinct()
    page_obj = paginate_queryset(request, logs, per_page=20)

    context = {
        "page_title": "Admin Audit Logs",
        "page_obj": page_obj,
        "query": query,
        "action_filter": action_filter,
        "distinct_actions": distinct_actions,
    }
    return render(request, "admin_panel/audit_logs.html", context)


@admin_required
def security_log_list(request):
    logs = SecurityLog.objects.select_related("user").order_by("-created_at")

    query = request.GET.get("q", "").strip()
    event_filter = request.GET.get("event", "").strip()

    if query:
        logs = logs.filter(
            Q(description__icontains=query)
            | Q(ip_address__icontains=query)
            | Q(user__username__icontains=query)
        )

    if event_filter:
        logs = logs.filter(event_type=event_filter)

    distinct_events = SecurityLog.objects.values_list("event_type", flat=True).distinct()
    page_obj = paginate_queryset(request, logs, per_page=20)

    context = {
        "page_title": "Security Logs",
        "page_obj": page_obj,
        "query": query,
        "event_filter": event_filter,
        "distinct_events": distinct_events,
    }
    return render(request, "admin_panel/security_logs.html", context)


# ==============================================================================
# 9. NOTIFICATION OVERVIEW
# ==============================================================================
@admin_required
def notification_overview(request):
    notifications = Notification.objects.select_related("user").order_by("-created_at")
    page_obj = paginate_queryset(request, notifications, per_page=25)
    return render(request, "admin_panel/notifications.html", {
        "page_title": "System Notifications Overview",
        "page_obj": page_obj,
    })


@admin_required
def whatsapp_notification_list(request):
    notifications = WhatsAppNotification.objects.select_related("user").order_by("-created_at")
    status_filter = request.GET.get("status", "").strip()
    if status_filter in dict(WhatsAppNotification.STATUS_CHOICES):
        notifications = notifications.filter(status=status_filter)
    return render(request, "admin_panel/whatsapp.html", {
        "page_title": "WhatsApp Notifications",
        "page_obj": paginate_queryset(request, notifications),
        "status_filter": status_filter,
        "status_choices": WhatsAppNotification.STATUS_CHOICES,
    })


@admin_required
def whatsapp_notification_retry(request, pk):
    if request.method != "POST":
        return redirect("admin_panel:whatsapp_notification_list")
    notification = get_object_or_404(WhatsAppNotification.objects.select_related("user"), pk=pk)
    if notification.status != WhatsAppNotification.FAILED:
        messages.error(request, "Only failed WhatsApp notifications can be retried.")
        return redirect("admin_panel:whatsapp_notification_list")
    send_whatsapp_message(
        notification.user,
        notification.notification_type,
        reference=None,
        idempotency_suffix=f"retry:{notification.pk}:{timezone.now().timestamp()}",
    )
    messages.success(request, "WhatsApp notification retry queued in development mode.")
    return redirect("admin_panel:whatsapp_notification_list")

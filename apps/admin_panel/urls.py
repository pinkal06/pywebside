from django.urls import path
from . import views

app_name = "admin_panel"

urlpatterns = [
    # Dashboard
    path("", views.dashboard, name="dashboard"),

    # User Management
    path("users/", views.user_list, name="user_list"),
    path("users/<int:pk>/", views.user_detail, name="user_detail"),
    path("users/<int:pk>/toggle-status/", views.user_toggle_status, name="user_toggle_status"),

    # Seller Management
    path("sellers/", views.seller_list, name="seller_list"),

    # Product Management
    path("products/", views.product_list, name="product_list"),
    path("products/<int:pk>/", views.product_detail, name="product_detail"),
    path("products/<int:pk>/approve/", views.product_approve, name="product_approve"),
    path("products/<int:pk>/reject/", views.product_reject, name="product_reject"),
    path("products/<int:pk>/toggle-status/", views.product_toggle_status, name="product_toggle_status"),

    # Category Management
    path("categories/", views.category_list, name="category_list"),
    path("categories/create/", views.category_create, name="category_create"),
    path("categories/<slug:slug>/edit/", views.category_edit, name="category_edit"),
    path("categories/<slug:slug>/toggle-status/", views.category_toggle_status, name="category_toggle_status"),
    path("categories/<slug:slug>/delete/", views.category_delete, name="category_delete"),

    # Order Management
    path("orders/", views.order_list, name="order_list"),
    path("orders/<int:pk>/", views.order_detail, name="order_detail"),
    path("orders/<int:pk>/status/", views.order_status_update, name="order_status_update"),

    # Reports
    path("reports/messages/", views.message_report_list, name="message_report_list"),
    path("reports/messages/<int:pk>/status/", views.message_report_update_status, name="message_report_update_status"),
    path("reports/products/", views.product_report_list, name="product_report_list"),
    path("reports/products/<int:pk>/status/", views.product_report_update_status, name="product_report_update_status"),

    # Logs
    path("audit-logs/", views.audit_log_list, name="audit_log_list"),
    path("security-logs/", views.security_log_list, name="security_log_list"),

    # Notifications
    path("notifications/", views.notification_overview, name="notification_overview"),
    path("whatsapp/", views.whatsapp_notification_list, name="whatsapp_notification_list"),
    path("whatsapp/<int:pk>/retry/", views.whatsapp_notification_retry, name="whatsapp_notification_retry"),
]

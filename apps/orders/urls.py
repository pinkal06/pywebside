from django.urls import path

from . import views

urlpatterns = [
    path("place/<int:product_pk>/", views.place_order, name="place_order"),
    path("checkout/", views.checkout, name="checkout"),
    path("confirmation/", views.order_confirmation, name="order_confirmation"),
    path("mine/", views.buyer_orders, name="buyer_orders"),
    path("received/", views.seller_orders, name="seller_orders"),
    path("pickups/", views.pickup_list, name="pickup_list"),
    path("pickups/request/<int:conversation_pk>/", views.pickup_request, name="pickup_request"),
    path("pickups/<int:pk>/", views.pickup_detail, name="pickup_detail"),
    path("seller/availability/", views.availability_list, name="availability_list"),
    path("seller/availability/<int:pk>/delete/", views.availability_delete, name="availability_delete"),
    path("<int:pk>/", views.order_detail, name="order_detail"),
    path("<int:pk>/status/", views.update_order_status, name="update_order_status"),
]

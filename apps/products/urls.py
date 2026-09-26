from django.urls import path
from . import views

urlpatterns = [
    path("", views.product_list, name="product_list"),
    path("add/", views.product_create, name="product_create"),
    path("<int:pk>/", views.product_detail, name="product_detail"),
    path("<int:pk>/edit/", views.product_update, name="product_update"),
    path("<int:pk>/delete/", views.product_delete, name="product_delete"),
    path("wishlist/", views.wishlist_list, name="wishlist"),
    path("<int:pk>/wishlist/add/", views.wishlist_add, name="wishlist_add"),
    path("<int:pk>/wishlist/remove/", views.wishlist_remove, name="wishlist_remove"),
    path("<int:pk>/wishlist/move-to-cart/", views.wishlist_move_to_cart, name="wishlist_move_to_cart"),
    path("cart/", views.cart_summary, name="cart"),
    path("<int:pk>/cart/add/", views.cart_add, name="cart_add"),
    path("<int:pk>/cart/remove/", views.cart_remove, name="cart_remove"),
    path("cart/update/", views.cart_update, name="cart_update"),
]

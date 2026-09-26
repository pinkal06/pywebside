from django.urls import path

from . import views

urlpatterns = [
    path("", views.conversation_list, name="conversation_list"),
    path("start/<int:product_id>/", views.conversation_start, name="conversation_start"),
    path("<int:pk>/", views.conversation_detail, name="conversation_detail"),
]

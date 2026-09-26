from django.urls import path

from . import views

urlpatterns = [
    path("token/", views.cometchat_token_view, name="cometchat_token"),
]

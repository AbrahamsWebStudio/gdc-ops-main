from django.urls import path

from .views import CustomLoginView, CustomLogoutView, landing

urlpatterns = [
    path("", landing, name="landing"),
    path("login/", CustomLoginView.as_view(), name="login"),
    path("logout/", CustomLogoutView.as_view(), name="logout"),
]

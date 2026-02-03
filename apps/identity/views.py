from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import render
from django.urls import reverse_lazy


def landing(request):
    return render(request, "public/landing.html")


class CustomLoginView(LoginView):
    template_name = "identity/login.html"


class CustomLogoutView(LogoutView):
    next_page = reverse_lazy("landing")

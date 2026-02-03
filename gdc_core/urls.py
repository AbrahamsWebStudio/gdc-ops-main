"""gdc_core URL Configuration."""
from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", include("apps.identity.urls")),
    path("dashboard/", include("apps.dashboard.urls")),
    path("crm/", include("apps.crm.urls")),
]

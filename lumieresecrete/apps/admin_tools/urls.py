from django.urls import path

from .views import maintenance_view

app_name = "admin_tools"

urlpatterns = [
    path("maintenance/", maintenance_view, name="maintenance"),
]

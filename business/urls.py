from django.urls import path

from . import views

app_name = "business"

urlpatterns = [
    path("settings/", views.settings_view, name="settings"),
]
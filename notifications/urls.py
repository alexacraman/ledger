from django.urls import path
from . import views, api

app_name = "notifications"

urlpatterns = [
    path("send/", views.send_notification_view, name="send"),
    path("settings/", views.notification_settings_view, name="notification_settings_view"),
    path("api/subscribe/", api.subscribe, name="api_subscribe"),
    path("api/unsubscribe/", api.unsubscribe, name="api_unsubscribe"),

    path('notificationss-list/', views.list_notifications, name="list-notification"),
    path('delete/', views.delete_notification, name="delete-notification")
]

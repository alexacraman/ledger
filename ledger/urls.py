from django.contrib import admin
from django.urls import path, include

from . import views
urlpatterns = [
    path("", views.home_page, name="home_page"),
    path('profile/', views.profile_view, name="profile_view"),
    path("accounts/logout/", views.logout_view, name="logout_view"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("cash-book/accounts/", include("accounts.urls", namespace="accounts")),
    path("contacts/", include("contacts.urls", namespace="contacts")),
    path("business/", include("business.urls", namespace="business")),
    path("banking/", include("banking.urls", namespace="banking")),
    path('control/', admin.site.urls),
]

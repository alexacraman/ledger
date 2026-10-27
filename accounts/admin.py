from .models import Account
from django.contrib import admin

@admin.register(Account)
class AccountAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "type",
        "is_active",
    )

    list_filter = (
        "type",
        "is_active",
    )

    search_fields = (
        "code",
        "name",
    )

    ordering = (
        "code",
    )

    list_editable = (
        "is_active",
    )
from django.contrib import admin

from .models import BankAccount, BankTransaction


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "account",
        "is_active",
    )

    list_filter = (
        "is_active",
    )

    search_fields = (
        "name",
        "account__code",
        "account__name",
    )


@admin.register(BankTransaction)
class BankTransactionAdmin(admin.ModelAdmin):
    list_display = (
        "transaction_date",
        "bank_account",
        "description",
        "amount",
        "reconciled",
        "journal_entry",
    )

    list_filter = (
        "bank_account",
        "reconciled",
        "transaction_date",
    )

    search_fields = (
        "description",
        "reference",
    )

    date_hierarchy = "transaction_date"

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Expense, Invoice, JournalEntry, Purchase
from business.models import BusinessSettings


def get_business_settings():
    return BusinessSettings.objects.get(pk=1)


def financial_activity_exists():
    """
    Return True once the bookkeeping system contains financial activity.

    Draft documents are ignored because they have not yet become
    accounting transactions.
    """

    if JournalEntry.objects.exists():
        return True

    if Invoice.objects.exclude(status="DRAFT").exists():
        return True

    if Purchase.objects.exclude(status="DRAFT").exists():
        return True

    if Expense.objects.exclude(status="DRAFT").exists():
        return True

    return False


def update_business_settings(
    *,
    business_name,
    accounting_basis,
    vat_registered,
    vat_scheme,
):
    """
    Update business settings while protecting accounting configuration.

    Accounting basis and VAT registration become locked once financial
    activity exists.
    """

    valid_basis = {"CASH", "ACCRUAL"}
    valid_vat_schemes = {"STANDARD", "CASH", "FLAT_RATE"}

    if accounting_basis not in valid_basis:
        raise ValidationError(
            "Invalid accounting basis."
        )

    if vat_registered and vat_scheme not in valid_vat_schemes:
        raise ValidationError(
            "A valid VAT scheme is required when the business is VAT registered."
        )

    if not vat_registered:
        vat_scheme = ""

    with transaction.atomic():

        settings = (
            BusinessSettings.objects
            .select_for_update()
            .get(pk=1)
        )

        activity_exists = financial_activity_exists()

        if activity_exists:

            if accounting_basis != settings.accounting_basis:
                raise ValidationError(
                    "Accounting basis cannot be changed after financial activity has been recorded."
                )

            if vat_registered != settings.vat_registered:
                raise ValidationError(
                    "VAT registration status cannot be changed after financial activity has been recorded."
                )

        settings.business_name = business_name
        settings.accounting_basis = accounting_basis
        settings.vat_registered = vat_registered
        settings.vat_scheme = vat_scheme

        settings.full_clean()
        settings.save()

    return settings
from datetime import date

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Q

from accounts.models import Expense, Invoice, JournalEntry, Purchase
from business.models import AccountingBasisPeriod, BusinessSettings, VATRegistrationPeriod


def get_business_settings():
    settings = BusinessSettings.objects.order_by("pk").first()

    if settings is None:
        settings = BusinessSettings.objects.create(
            business_name="",
            accounting_basis="CASH",
            vat_registered=False,
            vat_scheme="",
        )

    return settings


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


def get_accounting_basis_for_date(target_date):
    """Return the effective accounting basis for a specific date."""
    row = (
        AccountingBasisPeriod.objects
        .filter(effective_from__lte=target_date)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=target_date))
        .order_by('-effective_from')
        .first()
    )

    if row is not None:
        return row.accounting_basis

    settings = get_business_settings()
    return settings.accounting_basis


def create_accounting_basis_period(*, effective_from, effective_to=None, accounting_basis):
    """Create an effective-dated accounting-basis period."""
    valid_basis = {'CASH', 'ACCRUAL'}
    if accounting_basis not in valid_basis:
        raise ValidationError('Invalid accounting basis.')

    if effective_to and effective_to < effective_from:
        raise ValidationError('The end date cannot be before the start date.')

    period = AccountingBasisPeriod(
        effective_from=effective_from,
        effective_to=effective_to,
        accounting_basis=accounting_basis,
    )
    period.full_clean()
    period.save()
    return period


def get_vat_registration_for_date(target_date):
    """Return the effective VAT status for a specific date."""
    row = (
        VATRegistrationPeriod.objects
        .filter(effective_from__lte=target_date)
        .filter(Q(effective_to__isnull=True) | Q(effective_to__gte=target_date))
        .order_by('-effective_from')
        .first()
    )

    if row is not None:
        return {
            'vat_registered': row.vat_registered,
            'vat_scheme': row.vat_scheme,
        }

    settings = get_business_settings()
    return {
        'vat_registered': settings.vat_registered,
        'vat_scheme': settings.vat_scheme,
    }


def create_vat_registration_period(*, effective_from, effective_to=None, vat_registered=False, vat_scheme=''):
    """Create an effective-dated VAT registration period."""
    if vat_registered and not vat_scheme:
        raise ValidationError('A valid VAT scheme is required when VAT is registered.')

    if effective_to and effective_to < effective_from:
        raise ValidationError('The end date cannot be before the start date.')

    period = VATRegistrationPeriod(
        effective_from=effective_from,
        effective_to=effective_to,
        vat_registered=vat_registered,
        vat_scheme=vat_scheme if vat_registered else '',
    )
    period.full_clean()
    period.save()
    return period


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
            .order_by("pk")
            .first()
        )

        if settings is None:
            settings = BusinessSettings.objects.create(
                business_name="",
                accounting_basis="CASH",
                vat_registered=False,
                vat_scheme="",
            )

        activity_exists = financial_activity_exists()

        if activity_exists and accounting_basis != settings.accounting_basis:
            create_accounting_basis_period(
                effective_from=date.today(),
                accounting_basis=accounting_basis,
            )

        if activity_exists and (vat_registered != settings.vat_registered or vat_scheme != settings.vat_scheme):
            create_vat_registration_period(
                effective_from=date.today(),
                vat_registered=vat_registered,
                vat_scheme=vat_scheme,
            )

        settings.business_name = business_name
        settings.accounting_basis = accounting_basis
        settings.vat_registered = vat_registered
        settings.vat_scheme = vat_scheme

        settings.full_clean()
        settings.save()

    return settings
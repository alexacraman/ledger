from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account, Purchase, PurchasePayment
from business.services.settings import get_business_settings

from .journal import create_journal_entry


def post_purchase( purchase, purchases_acc=None, vat_reclaimable_acc=None, accounts_payable_acc=None):
    """
    Finalise a purchase according to the business accounting basis.

    CASH:
        The purchase is finalised but creates no ledger entry.
        The eventual payment creates the expense.

    ACCRUAL:
        Creates the normal Dr Purchases (+ VAT), Cr A/P entry.
    """

    settings = get_business_settings()

    if settings.accounting_basis == "CASH":
        return finalise_cash_purchase(purchase)

    return post_purchase_to_ledger(purchase, purchases_acc, vat_reclaimable_acc, accounts_payable_acc)


def finalise_cash_purchase(purchase):
    """
    Finalise a purchase under cash basis without creating a journal entry.
    """

    settings = get_business_settings()

    if settings.accounting_basis != "CASH":
        raise ValidationError( "This function can only be used for cash-basis accounting." )

    if settings.vat_registered:
        raise NotImplementedError( "Cash-basis VAT accounting has not yet been implemented." )

    if purchase.status != "DRAFT":
        raise ValidationError( "Only draft purchases can be finalised." )

    if purchase.journal_entry_id:
        raise ValidationError( "A cash-basis purchase cannot already have a journal entry." )

    if not purchase.lines.exists():
        raise ValidationError( "Purchase must contain at least one line." )

    if purchase.total_gross <= 0:
        raise ValidationError( "Purchase total must be greater than zero." )

    if purchase.total_vat != 0:
        raise ValidationError( "VAT has been entered on a purchase for a non-VAT-registered business." )

    purchase.status = "POSTED"
    purchase.save()

    return purchase


def post_purchase_to_ledger( purchase, purchases_acc, vat_reclaimable_acc, accounts_payable_acc, ):
    """
    Accrual-basis purchase posting.

    Dr Purchases
    Dr VAT Reclaimable (when applicable)
        Cr Accounts Payable

    This function deliberately does not support cash basis.
    """

    settings = get_business_settings()

    if settings.accounting_basis != "ACCRUAL":
        raise ValidationError( "post_purchase_to_ledger() is only available under accrual accounting." )

    if purchase.status != "DRAFT":
        raise ValidationError( "Only draft purchases can be posted." )

    if purchase.journal_entry_id:
        raise ValidationError( "Purchase has already been posted to the ledger." )

    if not purchase.lines.exists():
        raise ValidationError( "Purchase must contain at least one line." )

    if purchase.total_gross <= 0:
        raise ValidationError( "Purchase total must be greater than zero." )

    with transaction.atomic():
        items = [
            {
                "account": purchases_acc,
                "debit": purchase.total_net,
            },
            {
                "account": accounts_payable_acc,
                "credit": purchase.total_gross,
            },
        ]

        if settings.vat_registered and purchase.total_vat > 0:
            items.insert(
                1,
                {
                    "account": vat_reclaimable_acc,
                    "debit": purchase.total_vat,
                },
            )

        journal_entry = create_journal_entry(
            transaction_date=purchase.purchase_date,
            description=f"Purchase {purchase.reference or purchase.pk}",
            reference=purchase.reference or "",
            items=items,
        )

        purchase.journal_entry = journal_entry
        purchase.status = "POSTED"
        purchase.save()

    return purchase


def record_purchase_payment( purchase, amount, bank_account, accounts_payable_acc, purchases_acc, payment_date, reference="", ):
    """
    Record a payment against a purchase.

    CASH:
        Dr Purchases
            Cr Bank

    ACCRUAL:
        Dr Accounts Payable
            Cr Bank
    """

    amount = Decimal(amount)

    if amount <= 0:
        raise ValidationError( "Payment amount must be greater than zero." )

    settings = get_business_settings()

    if settings.vat_registered and settings.accounting_basis == "CASH":
        raise NotImplementedError( "Cash-basis VAT accounting has not yet been implemented." )

    with transaction.atomic():
        purchase = Purchase.objects .select_for_update() .get(pk=purchase.pk)
        
        if purchase.status not in ("POSTED", "PARTIAL"):
            raise ValidationError( "Purchase is not available for payment." )

        outstanding = purchase.total_gross - purchase.total_paid

        if amount > outstanding:
            raise ValidationError( f"Payment exceeds the outstanding amount of £{outstanding}." )

        if settings.accounting_basis == "CASH":

            if purchase.journal_entry_id:
                raise ValidationError( "A cash-basis purchase cannot already have an accrual journal entry." )

            if purchase.total_vat != 0:
                raise ValidationError( "VAT has been entered on a non-VAT-registered purchase." )

            items = [
                {
                    "account": purchases_acc,
                    "debit": amount,
                },
                {
                    "account": bank_account,
                    "credit": amount,
                },
            ]

        else:

            if not purchase.journal_entry_id:
                raise ValidationError( "An accrual-basis purchase must have a journal entry before payment." )

            items = [
                {
                    "account": accounts_payable_acc,
                    "debit": amount,
                },
                {
                    "account": bank_account,
                    "credit": amount,
                },
            ]

        journal_entry = create_journal_entry(
            transaction_date=payment_date,
            description=f"Payment for purchase {purchase.reference or purchase.purchase_number}",
            reference=reference or purchase.reference or "",
            items=items,
        )

        PurchasePayment.objects.create( purchase=purchase, payment_date=payment_date, amount=amount, journal_entry=journal_entry, reference=reference, )

        if amount == outstanding:
            purchase.status = "PAID"
        else:
            purchase.status = "PARTIAL"

        purchase.save()

    return journal_entry

def void_purchase(*, purchase):
    """
    Void an unpaid cash-basis purchase.

    Cash-basis purchases do not create a journal entry when posted,
    so an unpaid purchase can be voided without requiring a ledger
    reversal.

    Once any payment has been recorded, the purchase must not be
    voided directly because the payment has already affected the
    ledger.
    """
    settings = get_business_settings()

    if settings.accounting_basis != "CASH":
        raise NotImplementedError( "Purchase voiding for accrual-basis purchases has not yet been implemented." )

    if settings.vat_registered:
        raise NotImplementedError( "VAT-registered purchase voiding has not yet been implemented." )

    with transaction.atomic():
        purchase = Purchase.objects .select_for_update() .get(pk=purchase.pk)
    
        if purchase.status != "POSTED":
            raise ValidationError( "Only posted purchases can be voided." )

        if purchase.journal_entry_id:
            raise ValidationError( "This purchase has a journal entry and cannot be voided directly." )

        if purchase.payments.exists():
            raise ValidationError( "A purchase with payments cannot be voided directly." )

        purchase.status = "VOID"
        purchase.save(update_fields=["status"])

    return purchase
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account, Invoice, Payment
from business.services.settings import get_business_settings

from .journal import create_journal_entry


def post_invoice(
    invoice,
    accounts_receivable_acc=None,
    sales_revenue_acc=None,
    vat_liability_acc=None,
):
    """
    Finalise an invoice according to the business accounting basis.

    CASH:
        The invoice is finalised but creates no ledger entry.
        The eventual payment creates the income entry.

    ACCRUAL:
        Creates the normal Dr A/R, Cr Sales (+ VAT) entry.
    """

    settings = get_business_settings()

    if settings.accounting_basis == "CASH":
        return finalise_cash_invoice(invoice)

    return post_invoice_to_ledger(
        invoice,
        accounts_receivable_acc,
        sales_revenue_acc,
        vat_liability_acc,
    )


def finalise_cash_invoice(invoice):
    """
    Finalise an invoice under cash basis without creating a journal entry.
    """

    settings = get_business_settings()

    if settings.accounting_basis != "CASH":
        raise ValidationError(
            "This function can only be used for cash-basis accounting."
        )

    if settings.vat_registered:
        raise NotImplementedError(
            "Cash-basis VAT accounting has not yet been implemented."
        )

    if invoice.status != "DRAFT":
        raise ValidationError(
            "Only draft invoices can be finalised."
        )

    if invoice.journal_entry_id:
        raise ValidationError(
            "A cash-basis invoice cannot already have a journal entry."
        )

    if not invoice.lines.exists():
        raise ValidationError(
            "Invoice must contain at least one line."
        )

    if invoice.total_gross <= 0:
        raise ValidationError(
            "Invoice total must be greater than zero."
        )

    if invoice.total_vat != 0:
        raise ValidationError(
            "VAT has been entered on an invoice for a non-VAT-registered business."
        )

    invoice.status = "POSTED"
    invoice.save()

    return invoice


def post_invoice_to_ledger(
    invoice,
    accounts_receivable_acc,
    sales_revenue_acc,
    vat_liability_acc,
):
    """
    Accrual-basis invoice posting.

    Dr Accounts Receivable
        Cr Sales Revenue
        Cr VAT Liability (when applicable)

    This function deliberately does not support cash basis.
    """

    settings = get_business_settings()

    if settings.accounting_basis != "ACCRUAL":
        raise ValidationError(
            "post_invoice_to_ledger() is only available under accrual accounting."
        )

    if invoice.status != "DRAFT":
        raise ValidationError(
            "Only draft invoices can be posted."
        )

    if invoice.journal_entry_id:
        raise ValidationError(
            "Invoice has already been posted to the ledger."
        )

    if not invoice.lines.exists():
        raise ValidationError(
            "Invoice must contain at least one line."
        )

    if invoice.total_gross <= 0:
        raise ValidationError(
            "Invoice total must be greater than zero."
        )

    with transaction.atomic():

        items = [
            {
                "account": accounts_receivable_acc,
                "debit": invoice.total_gross,
            },
            {
                "account": sales_revenue_acc,
                "credit": invoice.total_net,
            },
        ]

        if settings.vat_registered and invoice.total_vat > 0:
            items.append(
                {
                    "account": vat_liability_acc,
                    "credit": invoice.total_vat,
                }
            )

        journal_entry = create_journal_entry(
            transaction_date=invoice.issue_date,
            description=f"Invoice {invoice.invoice_number}",
            reference=invoice.invoice_number,
            items=items,
        )

        invoice.journal_entry = journal_entry
        invoice.status = "POSTED"
        invoice.save()

    return invoice


def record_invoice_payment(
    invoice,
    amount,
    bank_account,
    accounts_receivable_acc,
    sales_revenue_acc,
    payment_date,
    reference="",
):
    """
    Record a payment against an invoice.

    CASH:
        Dr Bank
            Cr Sales Revenue

    ACCRUAL:
        Dr Bank
            Cr Accounts Receivable
    """

    amount = Decimal(amount)

    if amount <= 0:
        raise ValidationError(
            "Payment amount must be greater than zero."
        )

    settings = get_business_settings()

    if settings.vat_registered and settings.accounting_basis == "CASH":
        raise NotImplementedError(
            "Cash-basis VAT accounting has not yet been implemented."
        )

    with transaction.atomic():

        invoice = (
            Invoice.objects
            .select_for_update()
            .get(pk=invoice.pk)
        )

        if invoice.status not in ("POSTED", "SENT", "PARTIAL"):
            raise ValidationError(
                "Invoice is not available for payment."
            )

        outstanding = invoice.amount_outstanding

        if amount > outstanding:
            raise ValidationError(
                f"Payment exceeds the outstanding amount of £{outstanding}."
            )

        if settings.accounting_basis == "CASH":

            if invoice.journal_entry_id:
                raise ValidationError(
                    "A cash-basis invoice cannot already have an accrual journal entry."
                )

            if invoice.total_vat != 0:
                raise ValidationError(
                    "VAT has been entered on a non-VAT-registered invoice."
                )

            items = [
                {
                    "account": bank_account,
                    "debit": amount,
                },
                {
                    "account": sales_revenue_acc,
                    "credit": amount,
                },
            ]

        else:

            if not invoice.journal_entry_id:
                raise ValidationError(
                    "An accrual-basis invoice must have a journal entry before payment."
                )

            items = [
                {
                    "account": bank_account,
                    "debit": amount,
                },
                {
                    "account": accounts_receivable_acc,
                    "credit": amount,
                },
            ]

        journal_entry = create_journal_entry(
            transaction_date=payment_date,
            description=f"Payment for invoice {invoice.invoice_number}",
            reference=reference or invoice.invoice_number,
            items=items,
        )

        Payment.objects.create(
            invoice=invoice,
            payment_date=payment_date,
            amount=amount,
            journal_entry=journal_entry,
            reference=reference,
        )

        if amount == outstanding:
            invoice.status = "PAID"
        else:
            invoice.status = "PARTIAL"

        invoice.save()

    return journal_entry


def mark_invoice_sent(invoice):
    """
    Mark a posted invoice as sent.
    """

    if invoice.status != "POSTED":
        raise ValidationError(
            "Only posted invoices can be marked as sent."
        )

    invoice.status = "SENT"
    invoice.save()

    return invoice

def void_invoice(*, invoice):
    """
    Void an unpaid cash-basis invoice.

    Cash-basis invoices do not create a journal entry when posted,
    so an unpaid invoice can be voided without requiring a ledger
    reversal.

    Once any payment has been recorded, the invoice must not be
    voided directly because the payment has already affected the
    ledger.
    """
    settings = get_business_settings()

    if settings.accounting_basis != "CASH":
        raise NotImplementedError(
            "Invoice voiding for accrual-basis invoices has not yet been implemented."
        )

    if settings.vat_registered:
        raise NotImplementedError(
            "VAT-registered invoice voiding has not yet been implemented."
        )

    with transaction.atomic():
        invoice = (
            Invoice.objects
            .select_for_update()
            .get(pk=invoice.pk)
        )

        if invoice.status not in {"POSTED", "SENT"}:
            raise ValidationError(
                "Only posted or sent invoices can be voided."
            )

        if invoice.journal_entry_id:
            raise ValidationError(
                "This invoice has a journal entry and cannot be voided directly."
            )

        if invoice.payments.exists():
            raise ValidationError(
                "An invoice with payments cannot be voided directly."
            )

        invoice.status = "VOID"
        invoice.save(update_fields=["status"])

    return invoice
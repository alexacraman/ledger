from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from business.services.settings import get_accounting_basis_for_date, get_business_settings, get_vat_registration_for_date
from accounts.models import Account
from .journal import create_journal_entry
from .validation import validate_account_type, validate_payment_account

def void_expense(*, expense):
    """
    Void a posted cash-basis expense by creating a reversing journal entry.

    The original journal entry is never modified or deleted.

    Original:
        Dr Expense account
        Cr Payment account

    Reversal:
        Dr Payment account
        Cr Expense account
    """
    accounting_basis = get_accounting_basis_for_date(expense.expense_date)
    vat_status = get_vat_registration_for_date(expense.expense_date)

    if accounting_basis != "CASH":
        raise NotImplementedError(
            "Expense voiding for accrual-basis expenses has not yet been implemented."
        )

    if vat_status["vat_registered"]:
        raise NotImplementedError(
            "VAT-registered expense voiding has not yet been implemented."
        )

    with transaction.atomic():
        expense = (
            expense.__class__.objects
            .select_for_update()
            .get(pk=expense.pk)
        )

        if expense.status != "POSTED":
            raise ValidationError(
                "Only posted expenses can be voided."
            )

        if not expense.journal_entry_id:
            raise ValidationError(
                "Posted expense does not have a journal entry."
            )

        original_entry = expense.journal_entry

        if not original_entry.is_posted:
            raise ValidationError(
                "The expense journal entry has not been posted."
            )

        reversal_items = []

        for item in original_entry.items.all():
            reversal_items.append(
                {
                    "account": item.account,
                    "debit": item.credit,
                    "credit": item.debit,
                }
            )

        reversal_entry = create_journal_entry(
            transaction_date=expense.expense_date,
            description=f"Reversal of expense: {expense.description}",
            reference=f"VOID-{expense.reference}" if expense.reference else "",
            items=reversal_items,
        )

        expense.status = "VOID"
        expense.save(update_fields=["status"])

    return expense, reversal_entry

def record_expense(*, expense, expense_account, payment_account, reference=""):
    """
    Record a paid business expense. Cash basis:
    Dr Expense
    Cr Bank/Cash
    """

    accounting_basis = get_accounting_basis_for_date(expense.expense_date)
    vat_status = get_vat_registration_for_date(expense.expense_date)

    if accounting_basis != "CASH":
        raise NotImplementedError( "Accrual-basis expenses have not yet been implemented." )

    if vat_status["vat_registered"]:
        raise NotImplementedError( "VAT-registered expenses have not yet been implemented." )

    if expense.status != "DRAFT":
        raise ValidationError( "Only draft expenses can be posted." )

    if expense.journal_entry_id:
        raise ValidationError( "Expense has already been posted to the ledger." )

    if not expense.lines.exists():
        raise ValidationError( "Expense must contain at least one line." )

    amount = expense.total_gross

    if amount <= 0:
        raise ValidationError( "Expense total must be greater than zero." )

    if expense.total_vat != 0:
        raise ValidationError( "VAT has been entered on an expense for a non-VAT-registered business." )

    validate_payment_account(payment_account)
    validate_account_type(expense_account, "EXPENSE", "Expense account")

    with transaction.atomic():
        journal_entry = create_journal_entry(
            transaction_date=expense.expense_date,
            description=expense.description,
            reference=reference,
            items=[
                {
                    "account": expense_account,
                    "debit": amount,
                },
                {
                    "account": payment_account,
                    "credit": amount,
                },
            ],
        )

        expense.journal_entry = journal_entry
        expense.status = "POSTED"
        expense.save()
    return expense
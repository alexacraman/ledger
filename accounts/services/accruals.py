from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account
from accounts.services.journal import create_journal_entry


def _validate_positive_amount(amount, field_name):
    value = Decimal(str(amount))
    if value <= 0:
        raise ValidationError(f"{field_name} must be greater than zero.")
    return value


def record_accrued_expense(*, transaction_date, amount, expense_account, accrued_expense_account, description, reference=""):
    """Post an accrued expense: Dr Expense, Cr Accrued Expense (liability)."""
    value = _validate_positive_amount(amount, "Accrued expense amount")

    if not isinstance(expense_account, Account):
        raise ValidationError("Expense account is required.")
    if not isinstance(accrued_expense_account, Account):
        raise ValidationError("Accrued expense account is required.")

    with transaction.atomic():
        entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {"account": expense_account, "debit": value},
                {"account": accrued_expense_account, "credit": value},
            ],
        )

    return entry


def record_accrued_income(*, transaction_date, amount, revenue_account, accrued_income_account, description, reference=""):
    """Post an accrued income: Dr Accrued Income (asset), Cr Revenue."""
    value = _validate_positive_amount(amount, "Accrued income amount")

    if not isinstance(revenue_account, Account):
        raise ValidationError("Revenue account is required.")
    if not isinstance(accrued_income_account, Account):
        raise ValidationError("Accrued income account is required.")

    with transaction.atomic():
        entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {"account": accrued_income_account, "debit": value},
                {"account": revenue_account, "credit": value},
            ],
        )

    return entry


def record_prepayment(*, transaction_date, amount, payment_account, prepayment_account, description, reference=""):
    """Post a prepayment: Dr Prepayment asset, Cr Bank/Cash."""
    value = _validate_positive_amount(amount, "Prepayment amount")

    if not isinstance(payment_account, Account):
        raise ValidationError("Payment account is required.")
    if not isinstance(prepayment_account, Account):
        raise ValidationError("Prepayment account is required.")

    with transaction.atomic():
        entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {"account": prepayment_account, "debit": value},
                {"account": payment_account, "credit": value},
            ],
        )

    return entry


def recognise_prepayment(*, transaction_date, amount, expense_account, prepayment_account, description, reference=""):
    """Recognise the consumed part of a prepayment: Dr Expense, Cr Prepayment asset."""
    value = _validate_positive_amount(amount, "Prepayment recognition amount")

    if not isinstance(expense_account, Account):
        raise ValidationError("Expense account is required.")
    if not isinstance(prepayment_account, Account):
        raise ValidationError("Prepayment account is required.")

    with transaction.atomic():
        entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {"account": expense_account, "debit": value},
                {"account": prepayment_account, "credit": value},
            ],
        )

    return entry


def record_bad_debt_write_off(*, transaction_date, amount, receivables_account, irrecoverable_debt_account, description, reference=""):
    """Write off a known irrecoverable balance: Dr Irrecoverable Debts, Cr Receivables."""
    value = _validate_positive_amount(amount, "Bad debt amount")

    if not isinstance(receivables_account, Account):
        raise ValidationError("Receivables account is required.")
    if not isinstance(irrecoverable_debt_account, Account):
        raise ValidationError("Irrecoverable debt account is required.")

    with transaction.atomic():
        entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {"account": irrecoverable_debt_account, "debit": value},
                {"account": receivables_account, "credit": value},
            ],
        )

    return entry


def record_doubtful_debt_allowance(*, transaction_date, amount, bad_debt_expense_account, allowance_account, description, reference=""):
    """Create a doubtful debt allowance: Dr Irrecoverable Debts / expense, Cr Allowance (contra asset)."""
    value = _validate_positive_amount(amount, "Doubtful debt allowance amount")

    if not isinstance(bad_debt_expense_account, Account):
        raise ValidationError("Bad debt expense account is required.")
    if not isinstance(allowance_account, Account):
        raise ValidationError("Allowance account is required.")

    with transaction.atomic():
        entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {"account": bad_debt_expense_account, "debit": value},
                {"account": allowance_account, "credit": value},
            ],
        )

    return entry


def create_year_end_adjustment(*, adjustment_type, transaction_date, amount, description, reference="", **kwargs):
    """Dispatch the correct year-end adjustment journal entry based on the adjustment type."""
    valid_types = {
        "accrued_expense": record_accrued_expense,
        "accrued_income": record_accrued_income,
        "prepayment": record_prepayment,
        "recognise_prepayment": recognise_prepayment,
        "bad_debt_write_off": record_bad_debt_write_off,
        "doubtful_debt_allowance": record_doubtful_debt_allowance,
    }

    if adjustment_type not in valid_types:
        raise ValidationError(f"Unsupported year-end adjustment type: {adjustment_type}.")

    value = _validate_positive_amount(amount, "Year-end adjustment amount")

    try:
        return valid_types[adjustment_type](
            transaction_date=transaction_date,
            amount=value,
            description=description,
            reference=reference,
            **kwargs,
        )
    except TypeError as exc:
        raise ValidationError("The supplied adjustment data is incomplete for this year-end adjustment type.") from exc

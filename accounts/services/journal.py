from datetime import date
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account, JournalEntry, JournalItem
from accounts.services.periods import get_or_create_period_for_date


def _coerce_decimal(value, field_name):
    if value is None or value == "":
        raise ValidationError(f"{field_name} is required.")

    try:
        amount = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError(f"{field_name} must be a valid decimal value.")

    if not amount.is_finite():
        raise ValidationError(f"{field_name} must be finite.")

    return amount


def create_journal_entry( *, transaction_date, description, items, reference=""):
    """
    Create and post a balanced journal entry.

    items should be a list of dictionaries containing:

        {
            "account": Account instance,
            "debit": Decimal(...),
        }

    or:

        {
            "account": Account instance,
            "credit": Decimal(...),
        }

    A journal entry must:
    - contain at least one line
    - contain only active accounts
    - have total debits equal total credits
    - belong to a valid accounting period
    - be posted successfully before being returned
    """

    if not isinstance(items, list) or not items:
        raise ValidationError( "A journal entry must contain at least one line." )

    if transaction_date is None or not isinstance(transaction_date, date):
        raise ValidationError( "A valid transaction date is required." )

    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")

    for index, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValidationError(f"Journal item at index {index} must be a dictionary.")

        account = item.get("account")

        if not isinstance(account, Account):
            raise ValidationError( "Each journal item must contain a valid Account." )

        if not account.is_active:
            raise ValidationError( f"Account {account.code} - {account.name} is inactive." )

        debit = _coerce_decimal(item.get("debit", Decimal("0.00")), f"Debit amount for account {account.code}")
        credit = _coerce_decimal(item.get("credit", Decimal("0.00")), f"Credit amount for account {account.code}")

        if debit < 0:
            raise ValidationError( f"Debit amount for account {account.code} cannot be negative." )

        if credit < 0:
            raise ValidationError( f"Credit amount for account {account.code} cannot be negative." )

        if debit and credit:
            raise ValidationError( f"Journal item for account {account.code} cannot contain both a debit and a credit." )

        if debit == 0 and credit == 0:
            raise ValidationError( f"Journal item for account {account.code} must contain a debit or credit." )

        total_debits += debit
        total_credits += credit

    if total_debits != total_credits:
        raise ValidationError( f"Journal entry is not balanced. Debits: {total_debits}, Credits: {total_credits}." )

    with transaction.atomic():
        period = get_or_create_period_for_date( transaction_date )
        entry  = JournalEntry.objects.create( transaction_date=transaction_date, description=description, reference=reference, period=period, )

        for item in items:
            debit = _coerce_decimal(item.get("debit", Decimal("0.00")), "Debit amount")
            credit = _coerce_decimal(item.get("credit", Decimal("0.00")), "Credit amount")

            JournalItem.objects.create( entry=entry, account=item["account"], debit=debit, credit=credit, )

        entry.post()

    return entry

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account, JournalEntry, JournalItem
from accounts.services.periods import get_or_create_period_for_date

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

    if not items:
        raise ValidationError( "A journal entry must contain at least one line." )

    total_debits = Decimal("0.00")
    total_credits = Decimal("0.00")

    for item in items:
        account = item.get("account")

        if not isinstance(account, Account):
            raise ValidationError( "Each journal item must contain a valid Account." )

        if not account.is_active:
            raise ValidationError( f"Account {account.code} - {account.name} is inactive." )

        debit  = Decimal(str(item.get("debit", "0")))
        credit = Decimal(str(item.get("credit", "0")))

        if debit < 0:
            raise ValidationError( f"Debit amount for account {account.code} " "cannot be negative." )

        if credit < 0:
            raise ValidationError( f"Credit amount for account {account.code} " "cannot be negative." )

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
            debit = Decimal(str(item.get("debit", "0")))
            credit = Decimal(str(item.get("credit", "0")))

            JournalItem.objects.create( entry=entry, account=item["account"], debit=debit, credit=credit, )

        entry.post()

    return entry

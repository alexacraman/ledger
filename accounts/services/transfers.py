from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from .journal import create_journal_entry
from .validation import validate_payment_account


def record_transfer(*, transaction_date, amount, from_account, to_account, description="Transfer", reference=""):
    """
    Transfer money between Bank and Cash.

    Example:
        Bank -> Cash

        Dr Cash
            Cr Bank
    """

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError(
            "Transfer amount must be greater than zero."
        )

    if from_account == to_account:
        raise ValidationError(
            "Source and destination accounts must be different."
        )

    validate_payment_account(from_account)
    validate_payment_account(to_account)

    with transaction.atomic():

        journal_entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {
                    "account": to_account,
                    "debit": amount,
                },
                {
                    "account": from_account,
                    "credit": amount,
                },
            ],
        )

    return journal_entry
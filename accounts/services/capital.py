from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account

from .journal import create_journal_entry
from .validation import validate_account_type, validate_payment_account


def record_capital( *, transaction_date, amount, capital_account, payment_account, description="Capital introduced", reference="", ):
    """
    Record capital introduced into the business.
    Dr Bank/Cash
    Cr Capital
    """

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError(
            "Capital amount must be greater than zero."
        )

    validate_payment_account(payment_account)
    validate_account_type( capital_account, "EQUITY", "Capital account")

    with transaction.atomic():
        journal_entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {
                    "account": payment_account,
                    "debit": amount,
                },
                {
                    "account": capital_account,
                    "credit": amount,
                },
            ],
        )

    return journal_entry


def record_drawing( *, transaction_date, amount, drawings_account, payment_account, description="Business drawing", reference="", ):
    """
    Record money withdrawn from the business by the owner.
    Dr Drawings
    Cr Bank/Cash
    """

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError( "Drawing amount must be greater than zero." )

    validate_payment_account(payment_account)
    validate_account_type(drawings_account, "EQUITY", "Drawings account")

    with transaction.atomic():
        journal_entry = create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            reference=reference,
            items=[
                {
                    "account": drawings_account,
                    "debit": amount,
                },
                {
                    "account": payment_account,
                    "credit": amount,
                },
            ],
        )

    return journal_entry
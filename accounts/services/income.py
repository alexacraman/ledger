from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import Account
from business.services.settings import get_business_settings

from .journal import create_journal_entry
from .validation import validate_account_type, validate_payment_account


def record_income( *, transaction_date, amount, income_account, payment_account, description, reference="", ):
    """
    Record income that has actually been received.Cash basis:
        Dr Bank/Cash
        Cr Income
    """

    settings = get_business_settings()

    if settings.accounting_basis != "CASH":
        raise NotImplementedError( "Accrual-basis income has not yet been implemented." )

    if settings.vat_registered:
        raise NotImplementedError( "VAT-registered income has not yet been implemented." )

    amount = Decimal(str(amount))

    if amount <= 0:
        raise ValidationError( "Income amount must be greater than zero." )

    validate_payment_account(payment_account)
    validate_account_type(income_account, "REVENUE", "Income account")

    if amount <= 0:
        raise ValidationError( "Income amount must be greater than zero." )

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
                    "account": income_account,
                    "credit": amount,
                },
            ],
        )

    return journal_entry
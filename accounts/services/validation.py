from django.core.exceptions import ValidationError

from accounts.models import Account


BANK_CASH_CODES = {"1000", "1100"}


def validate_payment_account(account):
    if account.code not in BANK_CASH_CODES:
        raise ValidationError(
            "Payment account must be Bank or Cash."
        )


def validate_account_type(account, expected_type, description):
    if account.type != expected_type:
        raise ValidationError(
            f"{description} has an invalid account type."
        )
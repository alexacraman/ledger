from django.core.exceptions import ValidationError
from django.db import transaction

from accounts.models import AccountingPeriod

def close_accounting_period(period):
    """
    Close an accounting period.
    A closed period cannot receive new posted journal entries.
    Closed periods cannot currently be reopened.
    """

    with transaction.atomic():
        period = AccountingPeriod.objects.select_for_update().get(pk=period.pk)

        if period.is_closed:
            raise ValidationError( f"Accounting period {period.name} is already closed." )

        period.is_closed = True
        period.save(update_fields=["is_closed"])

    return period
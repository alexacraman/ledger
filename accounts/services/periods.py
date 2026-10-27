from datetime import date

from django.core.exceptions import ValidationError

from ..models import AccountingPeriod


def get_or_create_period_for_date(transaction_date):
    """
    Return the accounting period containing transaction_date.
    For this system, accounting periods correspond to UK tax years,
    e.g. 2026/27 = 6 April 2026 to 5 April 2027.
    """

    period = AccountingPeriod.objects.filter( start_date__lte=transaction_date, end_date__gte=transaction_date, ).first()

    if period:
        return period

    # Determine the UK tax year containing the date.
    if transaction_date >= date(transaction_date.year, 4, 6):
        start_year = transaction_date.year
    else:
        start_year = transaction_date.year - 1

    start_date = date(start_year, 4, 6)
    end_date   = date(start_year + 1, 4, 5)

    name = f"{start_year}/{str(start_year + 1)[-2:]}"

    period = AccountingPeriod(name=name, start_date=start_date, end_date=end_date, is_closed=False)

    period.full_clean()
    period.save()

    return period
from datetime import date

from django.shortcuts import render

from accounts.services.reports import trial_balance, profit_and_loss, balance_sheet

from accounts.services.tax import (
    calculate_tax_position_for_tax_year,
    get_tax_year_label,
)

def tax_view(request):
    """
    Display the estimated Income Tax position for a UK tax year.

    The selected value represents the year in which the tax year starts.

    Example:

        2026
        ↓
        6 April 2026 → 5 April 2027
        ↓
        2026/27
    """

    today = date.today()

    # Determine the current UK tax year start.
    if (today.month, today.day) >= (4, 6):
        current_tax_year = today.year
    else:
        current_tax_year = today.year - 1

    selected_year = request.GET.get("tax_year")

    try:
        tax_year = int(selected_year)
    except (TypeError, ValueError):
        tax_year = current_tax_year

    # Basic sanity check. This prevents nonsensical values being passed
    # into the tax-year calculation.
    if tax_year < 2000 or tax_year > current_tax_year:
        tax_year = current_tax_year

    position = calculate_tax_position_for_tax_year(
        for_date=date(
            tax_year,
            4,
            6,
        ),
    )

    # Provide a useful range of tax years for the selector.
    tax_years = [
    {
        "value": year,
        "label": f"{year}/{str(year + 1)[-2:]}",
    }
    for year in range(
        current_tax_year,
        current_tax_year - 5,
        -1,
    )
]

    context = {
        "position": position,
        "tax_year": tax_year,
        "tax_years": tax_years,
        "tax_year_label": get_tax_year_label(
            position["period"],
        ),
    }

    return render(
        request,
        "accounts/tax.html",
        context,
    )


def trial_balance_view(request):
    """
    Display the Trial Balance as at a selected date.
    """

    as_at = request.GET.get('as_at')

    if as_at:
        try:
            as_at = date.fromisoformat(as_at)
        except ValueError:
            as_at = date.today()
    else:
        as_at = date.today()

    results = trial_balance(as_at=as_at)

    total_debit = sum(
        row['debit'] for row in results
    )

    total_credit = sum(
        row['credit'] for row in results
    )

    context = {
        'trial_balance': results,
        'as_at': as_at,
        'total_debit': total_debit,
        'total_credit': total_credit,
    }

    return render(
        request,
        'accounts/trial_balance.html',
        context
    )


def profit_and_loss_view(request):
    """
    Display the Profit & Loss for a selected date range.
    """

    today = date.today()

    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')

    try:
        date_from = date.fromisoformat(date_from) if date_from else date(
            today.year, 1, 1
        )
    except ValueError:
        date_from = date(today.year, 1, 1)

    try:
        date_to = date.fromisoformat(date_to) if date_to else today
    except ValueError:
        date_to = today

    results = profit_and_loss(
        date_from=date_from,
        date_to=date_to,
    )

    context = {
        'revenue': results['revenue'],
        'expenses': results['expenses'],
        'total_revenue': results['total_revenue'],
        'total_expenses': results['total_expenses'],
        'net_profit': results['net_profit'],
        'date_from': date_from,
        'date_to': date_to,
    }

    return render(
        request,
        'accounts/profit_and_loss.html',
        context
    )

def balance_sheet_view(request):
    """
    Display the Balance Sheet as at a selected date.
    """

    today = date.today()

    as_at = request.GET.get('as_at')

    try:
        as_at = date.fromisoformat(as_at) if as_at else today
    except ValueError:
        as_at = today

    results = balance_sheet(as_at=as_at)

    context = {
        'assets': results['assets'],
        'liabilities': results['liabilities'],
        'equity': results['equity'],

        'total_assets': results['total_assets'],
        'total_liabilities': results['total_liabilities'],
        'total_equity': results['total_equity'],

        'net_profit': results['net_profit'],

        'total_liabilities_and_equity':
            results['total_liabilities_and_equity'],

        'as_at': as_at,
    }

    return render(
        request,
        'accounts/balance_sheet.html',
        context
    )


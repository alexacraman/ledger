from datetime import date
from decimal import Decimal

from django.db.models import Sum

from ..models import Account


def trial_balance(as_at=None):
    """
    Return the trial balance as at a given date.

    Only posted journal entries dated on or before `as_at`
    are included.

    If `as_at` is None, the current trial balance is returned.
    """

    accounts = Account.objects.filter( is_active=True ).order_by('code')

    results = []

    for account in accounts:
        journal_items = account.journal_items.filter( entry__is_posted=True )

        if as_at is not None:
            journal_items = journal_items.filter( entry__transaction_date__lte=as_at )

        totals = journal_items.aggregate(
            debit=Sum('debit'),
            credit=Sum('credit'),
        )

        total_debit  = totals['debit'] or Decimal('0.00')
        total_credit = totals['credit'] or Decimal('0.00')

        balance = total_debit - total_credit

        if balance >= 0:
            debit = balance
            credit = Decimal('0.00')
        else:
            debit = Decimal('0.00')
            credit = abs(balance)

        results.append({
            'account': account,
            'debit': debit,
            'credit': credit,
        })

    return results


def profit_and_loss(date_from, date_to):
    """
    Return the Profit & Loss for a given date range.

    Only posted journal entries between date_from and date_to
    are included.

    Revenue accounts have a normal credit balance.
    Expense accounts have a normal debit balance.

    Returns:
        {
            'revenue': [...],
            'expenses': [...],
            'total_revenue': Decimal,
            'total_expenses': Decimal,
            'net_profit': Decimal,
        }
    """

    accounts = Account.objects.filter( is_active=True, type__in=['REVENUE', 'EXPENSE'], ).order_by('code')

    revenue  = []
    expenses = []

    total_revenue  = Decimal('0.00')
    total_expenses = Decimal('0.00')

    for account in accounts:

        journal_items = account.journal_items.filter(
            entry__is_posted=True,
            entry__transaction_date__gte=date_from,
            entry__transaction_date__lte=date_to,
        )

        totals = journal_items.aggregate(
            debit=Sum('debit'),
            credit=Sum('credit'),
        )

        total_debit  = totals['debit'] or Decimal('0.00')
        total_credit = totals['credit'] or Decimal('0.00')

        if account.type == 'REVENUE':
            balance = total_credit - total_debit

            if balance != 0:
                revenue.append({
                    'account': account,
                    'amount': balance,
                })
                total_revenue += balance

        elif account.type == 'EXPENSE':
            balance = total_debit - total_credit

            if balance != 0:
                expenses.append({
                    'account': account,
                    'amount': balance,
                })
                total_expenses += balance

    net_profit = total_revenue - total_expenses

    return {
        'revenue': revenue,
        'expenses': expenses,
        'total_revenue': total_revenue,
        'total_expenses': total_expenses,
        'net_profit': net_profit,
    }



def balance_sheet(as_at):
    """
    Return the Balance Sheet as at a given date.

    Only posted journal entries dated on or before `as_at`
    are included.

    Assets have a normal debit balance.
    Liabilities and Equity have a normal credit balance.

    Current profit is included in equity because we are not
    currently posting year-end closing entries.

    Returns:
        {
            'assets': [...],
            'liabilities': [...],
            'equity': [...],
            'total_assets': Decimal,
            'total_liabilities': Decimal,
            'total_equity': Decimal,
            'net_profit': Decimal,
            'total_liabilities_and_equity': Decimal,
        }
    """

    accounts = Account.objects.filter(is_active=True, type__in=['ASSET', 'LIABILITY', 'EQUITY'], ).order_by('code')

    assets = []
    liabilities = []
    equity = []

    total_assets = Decimal('0.00')
    total_liabilities = Decimal('0.00')
    total_equity = Decimal('0.00')

    for account in accounts:

        journal_items = account.journal_items.filter(
            entry__is_posted=True,
            entry__transaction_date__lte=as_at,
        )

        totals = journal_items.aggregate(
            debit=Sum('debit'),
            credit=Sum('credit'),
        )

        total_debit = totals['debit'] or Decimal('0.00')
        total_credit = totals['credit'] or Decimal('0.00')

        if account.type == 'ASSET':
            balance = total_debit - total_credit

            if balance != 0:
                assets.append({
                    'account': account,
                    'amount': balance,
                })
                total_assets += balance

        elif account.type == 'LIABILITY':
            balance = total_credit - total_debit

            if balance != 0:
                liabilities.append({
                    'account': account,
                    'amount': balance,
                })
                total_liabilities += balance

        elif account.type == 'EQUITY':
            balance = total_credit - total_debit

            if balance != 0:
                equity.append({
                    'account': account,
                    'amount': balance,
                })
                total_equity += balance

    # Current profit is part of equity until year-end
    # closing entries are introduced.
    pnl = profit_and_loss(date_from=date.min, date_to=as_at)

    net_profit = pnl['net_profit']

    total_equity += net_profit

    total_liabilities_and_equity = ( total_liabilities + total_equity )

    return {
        'assets': assets,
        'liabilities': liabilities,
        'equity': equity,
        'total_assets': total_assets,
        'total_liabilities': total_liabilities,
        'total_equity': total_equity,
        'net_profit': net_profit,
        'total_liabilities_and_equity':
            total_liabilities_and_equity,
    }




def bank_cash_balances(*, as_at=None):
    """
    Return Bank and Cash balances calculated from
    posted journal entries.
    """

    accounts = Account.objects.filter(code__in=["1000", "1100"], is_active=True)

    results = []
    total_balance = Decimal("0.00")

    for account in accounts:
        items = account.journal_items.filter(
            entry__is_posted=True,
        )

        if as_at is not None:
            items = items.filter(
                entry__transaction_date__lte=as_at,
            )

        totals = items.aggregate(
            total_debit=Sum("debit"),
            total_credit=Sum("credit"),
        )

        debit  = totals["total_debit"] or Decimal("0.00")
        credit = totals["total_credit"] or Decimal("0.00")

        balance = debit - credit

        total_balance += balance

        results.append({
            "account": account,
            "balance": balance,
        })

    return {
        "accounts": results,
        "total": total_balance,
    }
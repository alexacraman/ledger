from datetime import date

from django.shortcuts import render, redirect
from django.contrib.auth import logout
from django.contrib.auth.decorators import login_required

from business.models import BusinessSettings
from accounts.models import AccountingPeriod, JournalEntry

from accounts.services.dashboard import dashboard_document_data
from accounts.services.reports import balance_sheet, bank_cash_balances, profit_and_loss

def home_page(request):
    return render(request, 'registration/home_page.html', {})


def logout_view(request):
    logout(request)
    return redirect('home_page')

@login_required
def profile_view(request):
    
    today    = date.today()
    settings = BusinessSettings.objects.first()
    periods  = AccountingPeriod.objects.filter(start_date__lte=today).order_by("-start_date")
    
    current_period = AccountingPeriod.objects.filter(start_date__lte=today, end_date__gte=today).first()

    selected_period = current_period
    period_id = request.GET.get("period")

    if period_id:
        try:
            selected_period = periods.get(pk=int(period_id))
        except (TypeError, ValueError, AccountingPeriod.DoesNotExist):
            selected_period = current_period

    if selected_period:
        date_from = selected_period.start_date
        date_to = min(today, selected_period.end_date)
        as_at = date_to
    else:
        date_from = date(today.year, 1, 1)
        date_to = today
        as_at = today

    pnl = profit_and_loss(
        date_from=date_from,
        date_to=date_to,
    )

    bs = balance_sheet(
        as_at=as_at,
    )

    bank_cash = bank_cash_balances(
        as_at=as_at,
    )

    recent_transactions = JournalEntry.objects.filter(is_posted=True, transaction_date__gte=date_from, transaction_date__lte=as_at, ).select_related("period").order_by( "-transaction_date", "-id", )[:10]

    document_data = dashboard_document_data( as_at=today, )

    context = {
        "settings": settings,
        "periods": periods,
        "current_period": current_period,
        "selected_period": selected_period,

        "profit_loss": {
            "date_from": date_from,
            "date_to": date_to,
            "income": pnl["total_revenue"],
            "expenses": pnl["total_expenses"],
            "net_profit": pnl["net_profit"],
        },

        "financial_position": {
            "assets": bs["total_assets"],
            "liabilities": bs["total_liabilities"],
            "equity": bs["total_equity"],
        },

        "bank_cash": bank_cash,

        "recent_transactions": recent_transactions,

        "document_data": document_data,
    }

    return render(request, 'registration/profile.html', context)

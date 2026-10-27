from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .models import AccountingPeriod
from .services.period_management import close_accounting_period


@login_required
def period_list(request):
    periods = AccountingPeriod.objects.order_by("-start_date")
    return render( request, "accounts/periods/period_list.html", { "periods": periods, }, )


@login_required
def period_detail(request, pk):
    period  = get_object_or_404( AccountingPeriod, pk=pk, )
    entries = period.journal_entries .filter(is_posted=True) .order_by("-transaction_date", "-id")
    return render( request, "accounts/periods/period_detail.html", { "period": period, "entries": entries, }, )


@login_required
def period_close(request, pk):
    period = get_object_or_404( AccountingPeriod, pk=pk, )

    if request.method != "POST":
        return redirect( "accounts:period_detail", pk=period.pk, )
    try:
        close_accounting_period(period)

    except ValidationError as exc:
        messages.error( request, exc.message, )
        return redirect( "accounts:period_detail", pk=period.pk, )

    messages.success( request, f"Accounting period {period.name} has been closed.", )
    return redirect( "accounts:period_detail", pk=period.pk, )
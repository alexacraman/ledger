from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from accounts.models import Account

from .forms_accruals import YearEndAdjustmentForm
from .services.accruals import create_year_end_adjustment


@login_required
def year_end_adjustment_create(request):
    if request.method == "POST":
        form = YearEndAdjustmentForm(request.POST)

        if form.is_valid():
            cleaned = form.cleaned_data
            payload = {
                "transaction_date": cleaned["transaction_date"],
                "amount": cleaned["amount"],
                "description": cleaned["description"],
                "reference": cleaned.get("reference", ""),
            }

            for field_name in [
                "expense_account",
                "accrued_expense_account",
                "revenue_account",
                "accrued_income_account",
                "payment_account",
                "prepayment_account",
                "receivables_account",
                "irrecoverable_debt_account",
                "bad_debt_expense_account",
                "allowance_account",
            ]:
                if cleaned.get(field_name):
                    payload[field_name] = cleaned[field_name]

            entry = create_year_end_adjustment(
                adjustment_type=cleaned["adjustment_type"],
                **payload,
            )

            messages.success(
                request,
                f"Year-end adjustment posted: {entry.description} ({entry.transaction_date}).",
            )
            return redirect("accounts:year_end_adjustment_create")

    else:
        form = YearEndAdjustmentForm()

    accounts = Account.objects.filter(is_active=True).order_by("code")

    return render(
        request,
        "accounts/accruals/year_end_adjustment_form.html",
        {
            "form": form,
            "accounts": accounts,
            "title": "Year-end adjustment",
        },
    )

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .forms_expenses import (
    ExpenseForm,
    ExpenseLineItemForm,
)
from .models import Expense, ExpenseLineItem
from .services.expenses import record_expense


@login_required
def expense_list(request):
    expenses = (
        Expense.objects
        .select_related(
            "expense_account",
            "payment_account",
        )
        .order_by("-expense_date", "-id")
    )

    return render(
        request,
        "accounts/expenses/expense_list.html",
        {
            "expenses": expenses,
        },
    )


@login_required
def expense_create(request):

    if request.method == "POST":

        form = ExpenseForm(request.POST)

        if form.is_valid():

            expense = form.save(commit=False)
            expense.status = "DRAFT"
            expense.save()

            messages.success(
                request,
                "Expense draft created.",
            )

            return redirect(
                "accounts:expense_detail",
                pk=expense.pk,
            )

    else:

        form = ExpenseForm()

    return render(
        request,
        "accounts/expenses/expense_form.html",
        {
            "form": form,
            "title": "New Expense",
        },
    )


@login_required
def expense_detail(request, pk):

    expense = get_object_or_404(
        Expense.objects.select_related(
            "expense_account",
            "payment_account",
            "journal_entry",
        ),
        pk=pk,
    )

    return render(
        request,
        "accounts/expenses/expense_detail.html",
        {
            "expense": expense,
        },
    )


@login_required
def expense_line_create(request, pk):

    expense = get_object_or_404(
        Expense,
        pk=pk,
    )

    if expense.status != "DRAFT":
        messages.error(
            request,
            "Line items can only be added to draft expenses.",
        )

        return redirect(
            "accounts:expense_detail",
            pk=expense.pk,
        )

    if request.method == "POST":

        form = ExpenseLineItemForm(request.POST)

        if form.is_valid():

            line = form.save(commit=False)
            line.expense = expense

            # Currently not VAT registered.
            line.vat_rate = 0
            line.vat_amount = 0

            line.save()

            messages.success(
                request,
                "Expense line added.",
            )

            return redirect(
                "accounts:expense_detail",
                pk=expense.pk,
            )

    else:

        form = ExpenseLineItemForm()

    return render(
        request,
        "accounts/expenses/line_form.html",
        {
            "form": form,
            "expense": expense,
        },
    )


@login_required
def expense_line_update(request, expense_pk, line_pk):

    expense = get_object_or_404(
        Expense,
        pk=expense_pk,
    )

    line = get_object_or_404(
        ExpenseLineItem,
        pk=line_pk,
        expense=expense,
    )

    if expense.status != "DRAFT":
        messages.error(
            request,
            "Expense lines can only be changed on draft expenses.",
        )

        return redirect(
            "accounts:expense_detail",
            pk=expense.pk,
        )

    if request.method == "POST":

        form = ExpenseLineItemForm(
            request.POST,
            instance=line,
        )

        if form.is_valid():

            line = form.save(commit=False)

            line.vat_rate = 0
            line.vat_amount = 0

            line.save()

            messages.success(
                request,
                "Expense line updated.",
            )

            return redirect(
                "accounts:expense_detail",
                pk=expense.pk,
            )

    else:

        form = ExpenseLineItemForm(
            instance=line,
        )

    return render(
        request,
        "accounts/expenses/line_form.html",
        {
            "form": form,
            "expense": expense,
            "line": line,
        },
    )


@login_required
def expense_line_delete(request, expense_pk, line_pk):

    expense = get_object_or_404(
        Expense,
        pk=expense_pk,
    )

    line = get_object_or_404(
        ExpenseLineItem,
        pk=line_pk,
        expense=expense,
    )

    if expense.status != "DRAFT":
        messages.error(
            request,
            "Expense lines cannot be deleted from a posted expense.",
        )

        return redirect(
            "accounts:expense_detail",
            pk=expense.pk,
        )

    if request.method == "POST":

        line.delete()

        messages.success(
            request,
            "Expense line deleted.",
        )

        return redirect(
            "accounts:expense_detail",
            pk=expense.pk,
        )

    return render(
        request,
        "accounts/expenses/line_confirm_delete.html",
        {
            "expense": expense,
            "line": line,
        },
    )


@login_required
def expense_post(request, pk):

    if request.method != "POST":
        return redirect(
            "accounts:expense_detail",
            pk=pk,
        )

    expense = get_object_or_404(
        Expense.objects.select_related(
            "expense_account",
            "payment_account",
        ),
        pk=pk,
    )

    try:

        record_expense(
            expense=expense,
            expense_account=expense.expense_account,
            payment_account=expense.payment_account,
            reference=expense.reference,
        )

    except (
        ValidationError,
        NotImplementedError,
    ) as exc:

        messages.error(
            request,
            str(exc),
        )

    else:

        messages.success(
            request,
            "Expense posted successfully.",
        )

    return redirect(
        "accounts:expense_detail",
        pk=expense.pk,
    )
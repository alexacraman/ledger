
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render

from .models import BankAccount, BankTransaction
from .forms import (
    BankAccountForm,
    BankStatementImportForm,
    BankTransactionCreateForm,
)
from .services.imports import import_bank_statement
from .services.reconciliation import (
    reconcile_bank_transaction,
    get_reconciliation_candidates,
    create_transaction_from_bank_transaction,
    get_suggested_accounting_treatment,
    bulk_create_transactions_from_suggested_treatment,
)


@login_required
def bank_account_list(request):
    bank_accounts = BankAccount.objects.select_related("account").order_by("name")

    return render(
        request,
        "banking/bank_account_list.html",
        {
            "bank_accounts": bank_accounts,
        },
    )


@login_required
def bank_account_create(request):
    if request.method == "POST":
        form = BankAccountForm(request.POST)

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Bank account has been added.",
            )

            return redirect(
                "banking:bank_account_list",
            )

    else:
        form = BankAccountForm()

    return render(
        request,
        "banking/bank_account_form.html",
        {
            "form": form,
            "page_title": "Add bank account",
        },
    )


@login_required
def bank_account_detail(request, pk):
    bank_account = get_object_or_404(
        BankAccount.objects.select_related("account"),
        pk=pk,
    )

    show_reconciled = request.GET.get("show_reconciled", "1") not in {"0", "false", "False"}

    source_candidates = (
        bank_account.transactions
        .select_related("journal_entry")
        .filter(reconciled=True, journal_entry__isnull=False)
        .order_by("-transaction_date", "-id")
    )

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "bulk_reconcile":
            selected_ids = request.POST.getlist("selected_transactions")

            if not selected_ids:
                messages.error(
                    request,
                    "Please select at least one unreconciled transaction.",
                )
            else:
                source_transaction_id = request.POST.get("source_transaction")

                if source_transaction_id is None:
                    messages.error(
                        request,
                        "Please choose a reconciled source transaction before bulk reconciling.",
                    )
                else:
                    try:
                        source_transaction_id = int(source_transaction_id)
                    except (TypeError, ValueError):
                        messages.error(
                            request,
                            "The selected source transaction is invalid.",
                        )
                        source_transaction_id = None

                    if source_transaction_id is not None:
                        selected_ids = [
                            pk for pk in selected_ids
                            if pk not in (None, "") and int(pk) != source_transaction_id
                        ]

                        source_transaction = get_object_or_404(
                            BankTransaction.objects.select_related(
                                "bank_account__account",
                                "journal_entry",
                            ),
                            pk=source_transaction_id,
                            bank_account=bank_account,
                        )

                        selected_transactions = (
                            BankTransaction.objects
                            .select_related(
                                "bank_account__account",
                                "journal_entry",
                            )
                            .filter(
                                bank_account=bank_account,
                                pk__in=selected_ids,
                            )
                            .order_by("-transaction_date", "-id")
                        )

                        if not selected_transactions.exists():
                            messages.error(
                                request,
                                "Please select at least one unreconciled target transaction other than the source transaction.",
                            )
                        else:
                            try:
                                bulk_create_transactions_from_suggested_treatment(
                                    bank_transactions=selected_transactions,
                                    source_bank_transaction=source_transaction,
                                )
                            except ValidationError as exc:
                                messages.error(request, str(exc))
                            else:
                                messages.success(
                                    request,
                                    (
                                        f"{selected_transactions.count()} transaction"
                                        f"{'s' if selected_transactions.count() != 1 else ''} "
                                        "reconciled using the same treatment."
                                    ),
                                )
                                return redirect(
                                    "banking:bank_account_detail",
                                    pk=bank_account.pk,
                                )

    transactions = (
        bank_account.transactions
        .select_related("journal_entry")
        .order_by("-transaction_date", "-id")
    )

    if not show_reconciled:
        transactions = transactions.filter(reconciled=False)

    transaction_count = bank_account.transactions.count()
    reconciled_count = bank_account.transactions.filter(reconciled=True).count()
    unreconciled_count = transaction_count - reconciled_count
    filtered_transaction_count = transactions.count()

    # --------------------------------------------------------------
    # Historical accounting treatment suggestions
    # --------------------------------------------------------------

    for transaction in transactions:
        transaction.suggested_treatment = None

        if not transaction.reconciled:
            transaction.suggested_treatment = get_suggested_accounting_treatment(
                transaction,
            )

    return render(
        request,
        "banking/bank_account_detail.html",
        {
            "bank_account": bank_account,
            "transactions": transactions,
            "source_candidates": source_candidates,
            "transaction_count": transaction_count,
            "filtered_transaction_count": filtered_transaction_count,
            "reconciled_count": reconciled_count,
            "unreconciled_count": unreconciled_count,
            "show_reconciled": show_reconciled,
        },
    )


@login_required
def bank_account_update(request, pk):
    bank_account = get_object_or_404(
        BankAccount,
        pk=pk,
    )

    if request.method == "POST":
        form = BankAccountForm(
            request.POST,
            instance=bank_account,
        )

        if form.is_valid():
            form.save()

            messages.success(
                request,
                "Bank account has been updated.",
            )

            return redirect(
                "banking:bank_account_detail",
                pk=bank_account.pk,
            )

    else:
        form = BankAccountForm(
            instance=bank_account,
        )

    return render(
        request,
        "banking/bank_account_form.html",
        {
            "form": form,
            "bank_account": bank_account,
            "page_title": "Edit bank account",
        },
    )


@login_required
def bank_statement_import(request):
    if request.method == "POST":
        form = BankStatementImportForm(
            request.POST,
            request.FILES,
        )

        if form.is_valid():
            try:
                statement_import = import_bank_statement(
                    bank_account=form.cleaned_data["bank_account"],
                    uploaded_file=form.cleaned_data["file"],
                )

            except ValidationError as exc:
                form.add_error(
                    "file",
                    exc.message,
                )

            else:
                messages.success(
                    request,
                    (
                        f"{statement_import.rows_imported} "
                        "bank transaction"
                        f"{'s' if statement_import.rows_imported != 1 else ''} "
                        "imported successfully."
                    ),
                )

                if statement_import.rows_skipped:
                    messages.info(
                        request,
                        (
                            f"{statement_import.rows_skipped} "
                            "duplicate or repeated row"
                            f"{'s' if statement_import.rows_skipped != 1 else ''} "
                            "were skipped."
                        ),
                    )

                return redirect(
                    "banking:bank_account_detail",
                    pk=statement_import.bank_account.pk,
                )

    else:
        form = BankStatementImportForm()

    return render(
        request,
        "banking/bank_statement_import.html",
        {
            "form": form,
        },
    )


@login_required
def bank_transaction_reconcile(request, pk):
    """
    Review an unreconciled bank transaction and optionally reconcile
    it against an existing posted journal entry.

    A separate suggested accounting treatment is also supplied when
    previous reconciled transactions indicate a likely treatment.
    """

    transaction = get_object_or_404(
        BankTransaction.objects.select_related(
            "bank_account__account",
            "journal_entry",
        ),
        pk=pk,
    )

    if transaction.reconciled:
        messages.info(
            request,
            "This bank transaction has already been reconciled.",
        )

        return redirect(
            "banking:bank_transaction_detail",
            pk=transaction.pk,
        )

    candidates = get_reconciliation_candidates(
        transaction,
    )

    suggested_treatment = get_suggested_accounting_treatment(
        transaction,
    )

    if request.method == "POST":
        journal_entry_id = request.POST.get("journal_entry")

        if not journal_entry_id:
            messages.error(
                request,
                "Please select a journal entry to reconcile.",
            )

        else:
            journal_entry = get_object_or_404(
                candidates,
                pk=journal_entry_id,
            )

            try:
                reconcile_bank_transaction(
                    bank_transaction=transaction,
                    journal_entry=journal_entry,
                )

            except ValidationError as exc:
                messages.error(
                    request,
                    str(exc),
                )

            else:
                messages.success(
                    request,
                    "Bank transaction reconciled successfully.",
                )

                return redirect(
                    "banking:bank_transaction_detail",
                    pk=transaction.pk,
                )

    context = {
        "transaction": transaction,
        "candidates": candidates,
        "suggested_treatment": suggested_treatment,
    }

    return render(
        request,
        "banking/bank_transaction_reconcile.html",
        context,
    )


@login_required
def bank_transaction_create(request, pk):
    bank_transaction = get_object_or_404(
        BankTransaction.objects.select_related(
            "bank_account",
            "bank_account__account",
        ),
        pk=pk,
    )

    if bank_transaction.reconciled:
        messages.info(
            request,
            "This bank transaction has already been reconciled.",
        )

        return redirect(
            "banking:bank_account_detail",
            pk=bank_transaction.bank_account.pk,
        )

    if request.method == "POST":
        form = BankTransactionCreateForm(
            request.POST,
            bank_transaction=bank_transaction,
        )

        if form.is_valid():
            try:
                create_transaction_from_bank_transaction(
                    bank_transaction=bank_transaction,
                    counterpart_account=form.cleaned_data["counterpart_account"],
                )

            except ValidationError as exc:
                form.add_error(
                    "counterpart_account",
                    exc.message,
                )

            else:
                messages.success(
                    request,
                    "Accounting transaction created and bank transaction reconciled.",
                )

                return redirect(
                    "banking:bank_account_detail",
                    pk=bank_transaction.bank_account.pk,
                )

    else:
        form = BankTransactionCreateForm(
            bank_transaction=bank_transaction,
        )

    return render(
        request,
        "banking/bank_transaction_create.html",
        {
            "bank_transaction": bank_transaction,
            "form": form,
        },
    )


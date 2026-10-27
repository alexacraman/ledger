from datetime import timedelta
from decimal import Decimal
import re

from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import (
    Case,
    DecimalField,
    F,
    Q,
    Sum,
    Value,
    When,
)

from accounts.models import Account, JournalEntry
from accounts.services.journal import create_journal_entry

from ..models import BankTransaction


# ----------------------------------------------------------------------
# Helpers
# ----------------------------------------------------------------------

def _normalise_description(value):
    """
    Normalise a bank description for comparison.

    Matching is case-insensitive and repeated whitespace is ignored.

    Examples:

        "Cloudflare"
        "CLOUDFLARE"
        "Cloudflare   "

    are treated as the same description.
    """

    if not value:
        return ""

    value = value.casefold()
    value = re.sub(r"\s+", " ", value)

    return value.strip()


def _journal_bank_impact(journal_entry, bank_account):
    """
    Return the signed movement on a particular bank ledger account.

    Debit  = money into the bank.
    Credit = money out of the bank.

    Returns:
        (
            bank_impact,
            bank_items,
            counterpart_items,
        )

    bank_impact:
        Decimal movement for the supplied bank account.

    bank_items:
        Journal lines belonging to the supplied bank account.

    counterpart_items:
        All other journal lines.
    """

    items = list(
        journal_entry.items
        .select_related("account")
        .all()
    )

    bank_items = [
        item
        for item in items
        if item.account_id == bank_account.pk
    ]

    counterpart_items = [
        item
        for item in items
        if item.account_id != bank_account.pk
    ]

    debit = sum(
        (item.debit for item in bank_items),
        Decimal("0.00"),
    )

    credit = sum(
        (item.credit for item in bank_items),
        Decimal("0.00"),
    )

    bank_impact = debit - credit

    return (
        bank_impact,
        bank_items,
        counterpart_items,
    )


def _treatment_signature(counterpart_items):
    """
    Return a stable representation of an accounting treatment.

    The signature allows previous reconciliations to be grouped so that
    repeated use of the same treatment can be identified.

    Account plus debit/credit amount are included for every counterpart
    line, and the lines are sorted so their original order does not
    matter.
    """

    return tuple(
        sorted(
            (
                item.account_id,
                str(item.debit),
                str(item.credit),
            )
            for item in counterpart_items
        )
    )


# ----------------------------------------------------------------------
# Existing journal matching
# ----------------------------------------------------------------------

def get_reconciliation_candidates(
    bank_transaction,
    date_tolerance_days=7,
):
    """
    Return posted journal entries that could represent the supplied
    bank transaction.

    The journal must:

    - be posted
    - contain the bank account's ledger account
    - have the same signed bank impact
    - fall within the allowed date range

    This function finds an EXISTING journal entry for reconciliation.

    It does not create any accounting transaction.
    """

    if bank_transaction.reconciled:
        return JournalEntry.objects.none()

    start_date = (
        bank_transaction.transaction_date
        - timedelta(days=date_tolerance_days)
    )

    end_date = (
        bank_transaction.transaction_date
        + timedelta(days=date_tolerance_days)
    )

    account = bank_transaction.bank_account.account

    candidates = (
        JournalEntry.objects
        .filter(
            is_posted=True,
            transaction_date__range=(
                start_date,
                end_date,
            ),
            items__account=account,
        )
        .annotate(
            bank_impact=Sum(
                Case(
                    When(
                        items__account=account,
                        then=F("items__debit")
                        - F("items__credit"),
                    ),
                    default=Value(Decimal("0.00")),
                    output_field=DecimalField(
                        max_digits=12,
                        decimal_places=2,
                    ),
                )
            )
        )
        .filter(
            bank_impact=bank_transaction.amount,
        )
        .distinct()
        .order_by(
            "transaction_date",
            "id",
        )
    )

    return candidates


# ----------------------------------------------------------------------
# Suggested accounting treatment
# ----------------------------------------------------------------------

def get_suggested_accounting_treatment(
    bank_transaction,
):
    """
    Find a previous reconciled bank transaction with the same:

    - bank account
    - description
    - signed amount

    and return the most commonly used accounting treatment.

    The previous journal entry is NOT reused.

    Only its accounting treatment is returned so that a NEW journal
    entry can be created for the current bank transaction.

    Returns:

        None

    when no previous matching treatment exists.

    Otherwise a dictionary containing:

        matched_bank_transaction
        journal_entry
        counterpart_items
        counterpart_accounts
        match_count
        total_matches
        is_ambiguous

    ``match_count`` indicates how many previous reconciled
    transactions used this exact treatment.

    ``total_matches`` indicates how many previous reconciled
    transactions matched the description and amount.

    ``is_ambiguous`` is True where two or more treatments have the
    same highest usage count.
    """

    bank_transaction = (
        BankTransaction.objects
        .select_related(
            "bank_account__account",
            "journal_entry",
        )
        .get(
            pk=bank_transaction.pk,
        )
    )

    if bank_transaction.reconciled:
        return None

    bank_account = bank_transaction.bank_account.account
    description = _normalise_description(
        bank_transaction.description
    )
    amount = Decimal(bank_transaction.amount)

    previous_transactions = (
        BankTransaction.objects
        .filter(
            bank_account=bank_transaction.bank_account,
            amount=amount,
            reconciled=True,
            journal_entry__isnull=False,
        )
        .exclude(
            pk=bank_transaction.pk,
        )
        .select_related(
            "bank_account__account",
            "journal_entry",
        )
        .order_by(
            "-transaction_date",
            "-id",
        )
    )

    treatments = {}

    total_matches = 0

    for previous_transaction in previous_transactions:

        previous_description = _normalise_description(
            previous_transaction.description
        )

        if previous_description != description:
            continue

        journal_entry = previous_transaction.journal_entry

        if not journal_entry:
            continue

        if not journal_entry.is_posted:
            continue

        (
            journal_bank_impact,
            bank_items,
            counterpart_items,
        ) = _journal_bank_impact(
            journal_entry,
            bank_account,
        )

        # A previous reconciliation must genuinely represent the
        # physical bank transaction before it can be used as a model.
        if journal_bank_impact != amount:
            continue

        # For a reliable suggestion we expect one bank line for the
        # relevant bank account.
        if len(bank_items) != 1:
            continue

        if not counterpart_items:
            continue

        total_matches += 1

        signature = _treatment_signature(
            counterpart_items
        )

        if signature not in treatments:
            treatments[signature] = {
                "count": 0,
                "matched_bank_transaction": previous_transaction,
                "journal_entry": journal_entry,
                "counterpart_items": counterpart_items,
            }

        treatments[signature]["count"] += 1

    if not treatments:
        return None

    # Rank by frequency first, then retain the most recent example
    # when frequencies differ.
    ranked_treatments = sorted(
        treatments.values(),
        key=lambda treatment: (
            -treatment["count"],
            -treatment["matched_bank_transaction"].id,
        ),
    )

    best = ranked_treatments[0]

    highest_count = best["count"]

    equally_common = [
        treatment
        for treatment in ranked_treatments
        if treatment["count"] == highest_count
    ]

    is_ambiguous = len(equally_common) > 1

    counterpart_items = best["counterpart_items"]

    counterpart_accounts = [
        item.account
        for item in counterpart_items
    ]

    return {
        "matched_bank_transaction": (
            best["matched_bank_transaction"]
        ),
        "journal_entry": best["journal_entry"],
        "counterpart_items": counterpart_items,
        "counterpart_accounts": counterpart_accounts,
        "match_count": best["count"],
        "total_matches": total_matches,
        "is_ambiguous": is_ambiguous,
    }


# ----------------------------------------------------------------------
# Reconcile against an existing journal entry
# ----------------------------------------------------------------------

@transaction.atomic
def reconcile_bank_transaction(
    *,
    bank_transaction,
    journal_entry,
):
    """
    Reconcile a bank transaction against an existing posted
    journal entry.

    No new accounting entry is created.

    The journal entry must already contain the correct signed movement
    on this bank account's ledger account.
    """

    bank_transaction = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "bank_account__account",
        )
        .get(
            pk=bank_transaction.pk,
        )
    )

    journal_entry = (
        JournalEntry.objects
        .select_for_update()
        .get(
            pk=journal_entry.pk,
        )
    )

    if bank_transaction.reconciled:
        raise ValidationError(
            "This bank transaction has already been reconciled."
        )

    if bank_transaction.journal_entry_id:
        raise ValidationError(
            "This bank transaction is already linked to a journal entry."
        )

    if not journal_entry.is_posted:
        raise ValidationError(
            "Only posted journal entries can be reconciled."
        )

    bank_account = bank_transaction.bank_account
    ledger_account = bank_account.account

    # --------------------------------------------------------------
    # Calculate the journal's actual movement on this bank account.
    #
    # Debit = money into the bank.
    # Credit = money out of the bank.
    # --------------------------------------------------------------

    totals = journal_entry.items.filter(
        account=ledger_account,
    ).aggregate(
        debit=Sum("debit"),
        credit=Sum("credit"),
    )

    debit = totals["debit"] or Decimal("0.00")
    credit = totals["credit"] or Decimal("0.00")

    journal_bank_impact = debit - credit

    if journal_bank_impact != bank_transaction.amount:
        raise ValidationError(
            "The journal entry does not match "
            "the bank transaction amount."
        )

    # --------------------------------------------------------------
    # Prevent the same journal being used twice for the same
    # physical bank account.
    #
    # A transfer journal may legitimately be linked to transactions
    # from two different bank accounts, so we only prevent a second
    # link for this particular bank account.
    # --------------------------------------------------------------

    already_linked = (
        journal_entry.bank_transactions
        .filter(
            bank_account=bank_account,
        )
        .exclude(
            pk=bank_transaction.pk,
        )
        .exists()
    )

    if already_linked:
        raise ValidationError(
            "This journal entry is already reconciled "
            "to a transaction on this bank account."
        )

    bank_transaction.journal_entry = journal_entry
    bank_transaction.reconciled = True

    bank_transaction.save(
        update_fields=[
            "journal_entry",
            "reconciled",
        ]
    )

    return bank_transaction


# ----------------------------------------------------------------------
# Create a new transaction manually from a bank transaction
# ----------------------------------------------------------------------

@transaction.atomic
def create_transaction_from_bank_transaction(
    *,
    bank_transaction,
    counterpart_account,
):
    """
    Create and post an accounting entry from an unreconciled bank
    transaction, then reconcile the bank transaction to it.

    Positive bank amount:

        Dr Bank
            Cr Revenue

    Negative bank amount:

        Dr Expense
            Cr Bank

    This is the manual transaction-creation route.

    It does not use or depend on suggestions.
    """

    bank_transaction = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "bank_account__account",
        )
        .get(
            pk=bank_transaction.pk,
        )
    )

    counterpart_account = (
        Account.objects
        .select_for_update()
        .get(
            pk=counterpart_account.pk,
        )
    )

    if bank_transaction.reconciled:
        raise ValidationError(
            "This bank transaction has already been reconciled."
        )

    if bank_transaction.journal_entry_id:
        raise ValidationError(
            "This bank transaction is already linked to a journal entry."
        )

    amount = Decimal(bank_transaction.amount)

    if amount == Decimal("0.00"):
        raise ValidationError(
            "A zero-value bank transaction cannot be posted."
        )

    bank_account = bank_transaction.bank_account.account

    if not bank_account.is_active:
        raise ValidationError(
            "The bank ledger account is inactive."
        )

    if not counterpart_account.is_active:
        raise ValidationError(
            "The selected account is inactive."
        )

    if amount > 0:

        if counterpart_account.type != "REVENUE":
            raise ValidationError(
                "Money received must be posted to "
                "a revenue account."
            )

        items = [
            {
                "account": bank_account,
                "debit": amount,
            },
            {
                "account": counterpart_account,
                "credit": amount,
            },
        ]

    else:

        expense_amount = abs(amount)

        if counterpart_account.type != "EXPENSE":
            raise ValidationError(
                "Money paid out must be posted to "
                "an expense account."
            )

        items = [
            {
                "account": counterpart_account,
                "debit": expense_amount,
            },
            {
                "account": bank_account,
                "credit": expense_amount,
            },
        ]

    journal_entry = create_journal_entry(
        transaction_date=bank_transaction.transaction_date,
        description=bank_transaction.description,
        reference=bank_transaction.reference,
        items=items,
    )

    bank_transaction.journal_entry = journal_entry
    bank_transaction.reconciled = True

    bank_transaction.save(
        update_fields=[
            "journal_entry",
            "reconciled",
        ]
    )

    return journal_entry


# ----------------------------------------------------------------------
# Bulk reconcile multiple identical transactions using one treatment
# ----------------------------------------------------------------------

@transaction.atomic
def bulk_create_transactions_from_suggested_treatment(
    *,
    bank_transactions,
    source_bank_transaction,
):
    """
    Apply the same suggested accounting treatment to a group of similar
    unreconciled bank transactions.

    Each selected bank transaction is reconciled to a fresh journal entry
    created from the source treatment, so the data model remains one
    transaction -> one journal entry.
    """
    selected_transactions = list(bank_transactions)

    if not selected_transactions:
        raise ValidationError("Please select at least one bank transaction.")

    source_bank_transaction = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "bank_account__account",
            "journal_entry",
        )
        .get(
            pk=source_bank_transaction.pk,
        )
    )

    if not source_bank_transaction.reconciled:
        raise ValidationError(
            "The selected source transaction has not been reconciled yet."
        )

    source_amount = Decimal(source_bank_transaction.amount)
    source_description = _normalise_description(source_bank_transaction.description)
    source_bank_account_id = source_bank_transaction.bank_account_id

    transactions = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "bank_account__account",
            "journal_entry",
        )
        .filter(
            pk__in=[transaction.pk for transaction in selected_transactions],
        )
        .order_by("id")
    )

    if transactions.count() != len(selected_transactions):
        raise ValidationError("One or more selected transactions could not be found.")

    created_entries = []

    for transaction in transactions:
        if transaction.reconciled:
            raise ValidationError(
                f"Transaction {transaction.pk} has already been reconciled."
            )

        if transaction.journal_entry_id:
            raise ValidationError(
                f"Transaction {transaction.pk} is already linked to a journal entry."
            )

        if transaction.bank_account_id != source_bank_account_id:
            raise ValidationError(
                "Selected transactions must all belong to the same bank account."
            )

        if Decimal(transaction.amount) != source_amount:
            raise ValidationError(
                "Selected transactions must all have the same amount to use the same treatment."
            )

        if (
            _normalise_description(transaction.description)
            != source_description
        ):
            raise ValidationError(
                "Selected transactions must all share the same description pattern."
            )

        created_entries.append(
            create_transaction_from_suggested_treatment(
                bank_transaction=transaction,
                source_bank_transaction=source_bank_transaction,
            )
        )

    return created_entries


@transaction.atomic
def create_transaction_from_suggested_treatment(
    *,
    bank_transaction,
    source_bank_transaction,
):
    """
    Create a NEW accounting journal entry for ``bank_transaction``
    using the accounting treatment from ``source_bank_transaction``.

    The source transaction must:

    - already be reconciled
    - have a posted journal entry
    - belong to the same bank account
    - have the same signed amount
    - have the same normalised description

    The old journal entry is never reused.

    Its counterpart journal lines are copied into a new journal entry
    and the current bank transaction becomes the bank line.

    This supports multi-line treatments, for example:

        Dr Purchases             £500
        Dr VAT Reclaimable       £100
            Cr Bank              £600

    as well as simple two-line entries.
    """

    bank_transaction = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "bank_account__account",
        )
        .get(
            pk=bank_transaction.pk,
        )
    )

    source_bank_transaction = (
        BankTransaction.objects
        .select_for_update()
        .select_related(
            "bank_account__account",
            "journal_entry",
        )
        .get(
            pk=source_bank_transaction.pk,
        )
    )

    # --------------------------------------------------------------
    # Current transaction validation
    # --------------------------------------------------------------

    if bank_transaction.reconciled:
        raise ValidationError(
            "This bank transaction has already been reconciled."
        )

    if bank_transaction.journal_entry_id:
        raise ValidationError(
            "This bank transaction is already linked "
            "to a journal entry."
        )

    amount = Decimal(bank_transaction.amount)

    if amount == Decimal("0.00"):
        raise ValidationError(
            "A zero-value bank transaction cannot be posted."
        )

    bank_account = bank_transaction.bank_account.account

    if not bank_account.is_active:
        raise ValidationError(
            "The bank ledger account is inactive."
        )

    # --------------------------------------------------------------
    # Source validation
    # --------------------------------------------------------------

    if not source_bank_transaction.reconciled:
        raise ValidationError(
            "The suggested source transaction "
            "has not been reconciled."
        )

    if not source_bank_transaction.journal_entry_id:
        raise ValidationError(
            "The suggested source transaction "
            "has no linked journal entry."
        )

    source_journal_entry = (
        JournalEntry.objects
        .select_for_update()
        .get(
            pk=source_bank_transaction.journal_entry_id,
        )
    )

    if not source_journal_entry.is_posted:
        raise ValidationError(
            "The suggested source journal entry "
            "is not posted."
        )

    if (
        source_bank_transaction.bank_account_id
        != bank_transaction.bank_account_id
    ):
        raise ValidationError(
            "The suggested source transaction "
            "belongs to a different bank account."
        )

    if (
        Decimal(source_bank_transaction.amount)
        != amount
    ):
        raise ValidationError(
            "The suggested source transaction "
            "has a different amount."
        )

    if (
        _normalise_description(
            source_bank_transaction.description
        )
        != _normalise_description(
            bank_transaction.description
        )
    ):
        raise ValidationError(
            "The suggested source transaction "
            "has a different description."
        )

    # --------------------------------------------------------------
    # Examine the source journal.
    # --------------------------------------------------------------

    (
        source_bank_impact,
        source_bank_items,
        source_counterpart_items,
    ) = _journal_bank_impact(
        source_journal_entry,
        bank_account,
    )

    if source_bank_impact != amount:
        raise ValidationError(
            "The suggested source journal entry "
            "does not match the bank transaction amount."
        )

    if len(source_bank_items) != 1:
        raise ValidationError(
            "The suggested source journal entry does not "
            "contain exactly one bank line for this account."
        )

    if not source_counterpart_items:
        raise ValidationError(
            "The suggested source journal entry has no "
            "accounting treatment to copy."
        )

    # --------------------------------------------------------------
    # Build a NEW journal entry.
    #
    # The current bank transaction supplies the bank line.
    # Every non-bank line comes from the previous treatment.
    # --------------------------------------------------------------

    items = []

    if amount > 0:

        items.append(
            {
                "account": bank_account,
                "debit": amount,
            }
        )

    else:

        items.append(
            {
                "account": bank_account,
                "credit": abs(amount),
            }
        )

    for source_item in source_counterpart_items:

        account = source_item.account

        if not account.is_active:
            raise ValidationError(
                f"The suggested account "
                f"{account.code} - {account.name} "
                f"is inactive."
            )

        items.append(
            {
                "account": account,
                "debit": source_item.debit,
                "credit": source_item.credit,
            }
        )

    journal_entry = create_journal_entry(
        transaction_date=bank_transaction.transaction_date,
        description=bank_transaction.description,
        reference=bank_transaction.reference,
        items=items,
    )

    # --------------------------------------------------------------
    # Reconcile the current bank transaction to the NEW journal.
    # --------------------------------------------------------------

    bank_transaction.journal_entry = journal_entry
    bank_transaction.reconciled = True

    bank_transaction.save(
        update_fields=[
            "journal_entry",
            "reconciled",
        ]
    )

    return journal_entry


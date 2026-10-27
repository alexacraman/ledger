from datetime import date
from decimal import Decimal
from django.db.models import Q, Count, Sum
from django.shortcuts import get_object_or_404, render

from accounts.models import JournalEntry


def transaction_list(request):
    """
    Display posted journal entries, newest first.

    Optional filters:
        from_date
        to_date
        search
    """
    entries = (
        JournalEntry.objects
        .filter(is_posted=True)
        .select_related("period")
        .prefetch_related("items__account")
        .order_by("-transaction_date", "-id")
    )

    from_date = request.GET.get("from_date", "")
    to_date = request.GET.get("to_date", "")
    search = request.GET.get("search", "").strip()

    if from_date:
        try:
            from_date_obj = date.fromisoformat(from_date)
            entries = entries.filter(transaction_date__gte=from_date_obj)
        except ValueError:
            from_date = ""

    if to_date:
        try:
            to_date_obj = date.fromisoformat(to_date)
            entries = entries.filter(transaction_date__lte=to_date_obj)
        except ValueError:
            to_date = ""

    if search:
        entries = entries.filter(
            Q(description__icontains=search)
            | Q(reference__icontains=search)
        )

    # Protect against duplicate JournalEntry rows when filters
    # involve related tables.
    entries = entries.distinct()

    summary = entries.aggregate(
        transaction_count=Count("id", distinct=True),
        total=Sum("items__debit"),
    )

    context = {
        "entries": entries,
        "from_date": from_date,
        "to_date": to_date,
        "search": search,
        "summary": {
            "transaction_count": summary["transaction_count"] or 0,
            "total": summary["total"] or Decimal("0.00"),
        },
    }

    return render(
        request,
        "accounts/transactions/list.html",
        context,
    )




def transaction_detail(request, pk):
    """
    Display a single posted journal entry and all its lines.
    """
    entry = get_object_or_404(JournalEntry.objects.select_related("period").prefetch_related("items__account"), pk=pk, is_posted=True)

    return render( request, "accounts/transactions/detail.html", {"entry": entry}, )




from decimal import Decimal
from accounts.models import Expense, Invoice, Purchase
from accounts.services.reports import (
    balance_sheet,
    bank_cash_balances,
    profit_and_loss,
)

def get_dashboard_data(*, period):
    pnl = profit_and_loss( date_from=period.start_date, date_to=period.end_date, )

    return {
        "period": period,
        "total_revenue": pnl["total_revenue"],
        "total_expenses": pnl["total_expenses"],
        "net_profit": pnl["net_profit"],

        "balance_sheet": balance_sheet(
            as_at=period.end_date,
        ),

        "bank_cash": bank_cash_balances(
            as_at=period.end_date,
        ),

        **dashboard_document_data(
            as_at=period.end_date,
        ),
    }

def dashboard_document_data(*, as_at):
    """
    Return operational invoice, purchase and draft information
    for the dashboard.

    Accounting figures such as profit, assets and cash remain
    sourced from the accounting/reporting services.
    """

    invoices = Invoice.objects.filter( status__in={"POSTED", "SENT", "PARTIAL"}, ).prefetch_related("lines", "payments")

    outstanding_invoices = []
    overdue_invoices = []

    for invoice in invoices:
        if invoice.amount_outstanding > Decimal("0.00"):
            outstanding_invoices.append(invoice)

            if invoice.due_date and invoice.due_date < as_at:
                overdue_invoices.append(invoice)

    purchases = Purchase.objects.filter( status__in={"POSTED", "PARTIAL"}, ).prefetch_related("lines", "payments")
    

    outstanding_purchases = []
    overdue_purchases = []

    for purchase in purchases:
        if purchase.amount_outstanding > Decimal("0.00"):
            outstanding_purchases.append(purchase)

            if purchase.due_date and purchase.due_date < as_at:
                overdue_purchases.append(purchase)

    return {
        "outstanding_invoices": {
            "count": len(outstanding_invoices),
            "total": sum(
                (invoice.amount_outstanding for invoice in outstanding_invoices),
                Decimal("0.00"),
            ),
            "overdue_count": len(overdue_invoices),
            "overdue_total": sum(
                (invoice.amount_outstanding for invoice in overdue_invoices),
                Decimal("0.00"),
            ),
        },
        "outstanding_purchases": {
            "count": len(outstanding_purchases),
            "total": sum(
                (purchase.amount_outstanding for purchase in outstanding_purchases),
                Decimal("0.00"),
            ),
            "overdue_count": len(overdue_purchases),
            "overdue_total": sum(
                (purchase.amount_outstanding for purchase in overdue_purchases),
                Decimal("0.00"),
            ),
        },
        "drafts": {
            "invoices": Invoice.objects.filter(status="DRAFT").count(),
            "purchases": Purchase.objects.filter(status="DRAFT").count(),
            "expenses": Expense.objects.filter(status="DRAFT").count(),
        },
    }
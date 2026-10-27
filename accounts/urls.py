from django.urls import path

from .views import (
    dashboard_view,
    transaction_detail, transaction_list,
    trial_balance_view, profit_and_loss_view, balance_sheet_view, tax_view

) 
from . import views_invoice, views_purchases, views_expenses, views_periods

app_name = 'accounts'

urlpatterns = [
    path('', dashboard_view, name="dashboard"),

    path("transactions/", transaction_list, name="transaction_list"), 
    path("transactions/<int:pk>/", transaction_detail, name="transaction_detail"),

    path('reports/trial-balance/', trial_balance_view, name='trial_balance'),
    path('reports/profit-and-loss/', profit_and_loss_view, name='profit_and_loss'),
    path('reports/balance-sheet/', balance_sheet_view, name='balance_sheet'),
    path("reports/tax/", tax_view, name="tax"),

    path("invoices/",views_invoice.invoice_list, name="invoice_list"),
    path("invoices/add/", views_invoice.invoice_create, name="invoice_create"),
    path("invoices/<int:pk>/", views_invoice.invoice_detail, name="invoice_detail"),
    path("invoices/<int:pk>/edit/", views_invoice.invoice_update, name="invoice_update"),

    path("invoices/<int:pk>/lines/add/", views_invoice.invoice_line_create, name="invoice_line_create"),
    path("invoices/<int:invoice_pk>/lines/<int:line_pk>/edit/", views_invoice.invoice_line_update, name="invoice_line_update"),
    path("invoices/<int:invoice_pk>/lines/<int:line_pk>/delete/", views_invoice.invoice_line_delete, name="invoice_line_delete"),

    path("invoices/<int:pk>/post/", views_invoice.invoice_post, name="invoice_post"), 
    path("invoices/<int:pk>/mark-sent/", views_invoice.invoice_mark_sent, name="invoice_mark_sent"), 
    path("invoices/<int:pk>/payment/", views_invoice.invoice_payment_create, name="invoice_payment_create"),

    path("purchases/", views_purchases.purchase_list, name="purchase_list"),
    path("purchases/add/", views_purchases.purchase_create, name="purchase_create"), 
    path("purchases/<int:pk>/", views_purchases.purchase_detail, name="purchase_detail"), 
    path("purchases/<int:pk>/edit/", views_purchases.purchase_update, name="purchase_update"), 
    path("purchases/<int:purchase_id>/lines/add/", views_purchases.purchase_line_create, name="purchase_line_create"), 
    path("purchases/<int:purchase_id>/lines/<int:line_id>/edit/", views_purchases.purchase_line_update, name="purchase_line_update"), 
    path("purchases/<int:purchase_id>/lines/<int:line_id>/delete/", views_purchases.purchase_line_delete, name="purchase_line_delete"),
    path("purchases/<int:pk>/payment/add/", views_purchases.purchase_payment_create, name="purchase_payment_create"),
    path("purchases/<int:pk>/post/", views_purchases.purchase_post, name="purchase_post"),

    path("expenses/", views_expenses.expense_list, name="expense_list"),
    path("expenses/new/", views_expenses.expense_create, name="expense_create"), 
    path("expenses/<int:pk>/", views_expenses.expense_detail, name="expense_detail"), 
    path("expenses/<int:pk>/post/", views_expenses.expense_post, name="expense_post"), 
    path("expenses/<int:pk>/lines/new/", views_expenses.expense_line_create, name="expense_line_create"), 
    path("expenses/<int:expense_pk>/lines/<int:line_pk>/edit/", views_expenses.expense_line_update, name="expense_line_update"), 
    path("expenses/<int:expense_pk>/lines/<int:line_pk>/delete/", views_expenses.expense_line_delete, name="expense_line_delete"),

    path("periods/", views_periods.period_list, name="period_list"), 
    path("periods/<int:pk>/", views_periods.period_detail, name="period_detail"), 
    path("periods/<int:pk>/close/", views_periods.period_close, name="period_close"),

    path("invoices/<int:pk>/pdf/", views_invoice.invoice_pdf, name="invoice_pdf"), 
    path("invoices/<int:pk>/email/", views_invoice.invoice_email, name="invoice_email"),
]


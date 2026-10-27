from django.urls import path

from . import views


app_name = "banking"


urlpatterns = [
    path("", views.bank_account_list, name="bank_account_list"), 
    path("new/", views.bank_account_create, name="bank_account_create"), 
    path("<int:pk>/", views.bank_account_detail, name="bank_account_detail"), 
    path("<int:pk>/edit/", views.bank_account_update, name="bank_account_update"),
    path("import/", views.bank_statement_import, name="bank_statement_import"),
    path("transactions/<int:pk>/reconcile/", views.bank_transaction_reconcile, name="bank_transaction_reconcile"),
    path("transactions/<int:pk>/create/", views.bank_transaction_create, name="bank_transaction_create"),
]
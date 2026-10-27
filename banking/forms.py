from django import forms
from django.db import models

from accounts.models import Account, JournalEntry

from .models import BankAccount, BankTransaction
from .services.reconciliation import get_reconciliation_candidates


class BankAccountForm(forms.ModelForm):

    class Meta:
        model = BankAccount
        fields = [
            "name",
            "account",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-sm text-gray-900 "
                        "focus:border-[#224B75] focus:outline-none "
                        "focus:ring-1 focus:ring-[#224B75]"
                    ),
                }
            ),
            "account": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-sm text-gray-900 "
                        "focus:border-[#224B75] focus:outline-none "
                        "focus:ring-1 focus:ring-[#224B75]"
                    ),
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": (
                        "h-4 w-4 rounded border-gray-300 "
                        "text-[#224B75] focus:ring-[#224B75]"
                    ),
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        queryset = Account.objects.filter(
            type="ASSET",
            is_active=True,
        )

        if self.instance.pk and self.instance.account_id:
            queryset = queryset.filter(
                models.Q(bank_accounts__isnull=True)
                | models.Q(pk=self.instance.account_id)
            )
        else:
            queryset = queryset.filter(
                bank_accounts__isnull=True,
            )

        self.fields["account"].queryset = queryset.order_by("code")





class BankStatementImportForm(forms.Form):

    bank_account = forms.ModelChoiceField(
        queryset=BankAccount.objects.none(),
        empty_label=None,
        widget=forms.Select(
            attrs={
                "class": (
                    "w-full rounded-lg border border-gray-300 "
                    "bg-white px-3 py-2 text-sm text-gray-900 "
                    "focus:border-[#224B75] focus:outline-none "
                    "focus:ring-1 focus:ring-[#224B75]"
                ),
            }
        ),
    )

    file = forms.FileField(
        label="CSV bank statement",
        widget=forms.ClearableFileInput(
            attrs={
                "accept": ".csv,text/csv",
                "class": (
                    "block w-full text-sm text-gray-700 "
                    "file:mr-4 file:rounded-lg file:border-0 "
                    "file:bg-[#224B75] file:px-4 file:py-2 "
                    "file:text-sm file:font-semibold file:text-white "
                    "hover:file:bg-[#1b3d60]"
                ),
            }
        ),
        help_text=(
            "Upload the CSV statement downloaded from your bank. "
            "The file must contain Date, Transaction type, "
            "Description, Paid out, Paid in and Balance columns."
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["bank_account"].queryset = (
            BankAccount.objects
            .filter(is_active=True)
            .select_related("account")
            .order_by("name")
        )

    def clean_file(self):
        uploaded_file = self.cleaned_data["file"]

        if not uploaded_file.name.lower().endswith(".csv"):
            raise forms.ValidationError(
                "Please upload a CSV bank statement."
            )

        return uploaded_file




class BankTransactionReconciliationForm(forms.Form):

    journal_entry = forms.ModelChoiceField(
        queryset=JournalEntry.objects.none(),
        empty_label="Select a journal entry",
        widget=forms.Select(
            attrs={
                "class": (
                    "w-full rounded-lg border border-gray-300 "
                    "bg-white px-3 py-2 text-sm text-gray-900 "
                    "focus:border-[#224B75] focus:outline-none "
                    "focus:ring-1 focus:ring-[#224B75]"
                ),
            }
        ),
    )

    def __init__(
        self,
        *args,
        bank_transaction=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if bank_transaction is None:
            return

        self.fields[
            "journal_entry"
        ].queryset = get_reconciliation_candidates(
            bank_transaction,
        )

        self.fields[
            "journal_entry"
        ].label_from_instance = self._label_journal_entry

    @staticmethod
    def _label_journal_entry(entry):
        reference = (
            f" ({entry.reference})"
            if entry.reference
            else ""
        )

        return (
            f"{entry.transaction_date:%d %b %Y} - "
            f"{entry.description}"
            f"{reference}"
        )
    


class BankTransactionCreateForm(forms.Form):

    counterpart_account = forms.ModelChoiceField(
        queryset=Account.objects.none(),
        empty_label="Select an account",
        widget=forms.Select(
            attrs={
                "class": (
                    "w-full rounded-lg border border-gray-300 "
                    "bg-white px-3 py-2 text-sm text-gray-900 "
                    "focus:border-[#224B75] focus:outline-none "
                    "focus:ring-1 focus:ring-[#224B75]"
                ),
            }
        ),
    )

    def __init__(
        self,
        *args,
        bank_transaction=None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)

        if bank_transaction is None:
            return

        if bank_transaction.amount > 0:
            queryset = Account.objects.filter(
                type="REVENUE",
                is_active=True,
            ).order_by(
                "code"
            )
        else:
            queryset = Account.objects.filter(
                type="EXPENSE",
                is_active=True,
            ).order_by(
                "code"
            )

        self.fields[
            "counterpart_account"
        ].queryset = queryset

        self.fields[
            "counterpart_account"
        ].label_from_instance = self._label_account

    @staticmethod
    def _label_account(account):
        return f"{account.code} - {account.name}"
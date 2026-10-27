from django import forms

from accounts.models import Account


class YearEndAdjustmentForm(forms.Form):
    ADJUSTMENT_CHOICES = [
        ("accrued_expense", "Accrued expense"),
        ("accrued_income", "Accrued income"),
        ("prepayment", "Prepayment"),
        ("recognise_prepayment", "Recognise prepayment"),
        ("bad_debt_write_off", "Bad debt write-off"),
        ("doubtful_debt_allowance", "Doubtful debt allowance"),
    ]

    adjustment_type = forms.ChoiceField(choices=ADJUSTMENT_CHOICES)
    transaction_date = forms.DateField()
    amount = forms.DecimalField(min_value=0.01, max_digits=12, decimal_places=2)
    description = forms.CharField(max_length=255)
    reference = forms.CharField(max_length=50, required=False, strip=True)

    expense_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Expense account",
    )
    accrued_expense_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Accrued expense account",
    )
    revenue_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Revenue account",
    )
    accrued_income_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Accrued income account",
    )
    payment_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Payment account",
    )
    prepayment_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Prepayment account",
    )
    receivables_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Receivables account",
    )
    irrecoverable_debt_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Irrecoverable debt account",
    )
    bad_debt_expense_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Bad debt expense account",
    )
    allowance_account = forms.ModelChoiceField(
        queryset=Account.objects.filter(is_active=True),
        required=False,
        label="Allowance account",
    )

    def clean(self):
        cleaned_data = super().clean()
        adjustment_type = cleaned_data.get("adjustment_type")
        required_fields = {
            "accrued_expense": ["expense_account", "accrued_expense_account"],
            "accrued_income": ["revenue_account", "accrued_income_account"],
            "prepayment": ["payment_account", "prepayment_account"],
            "recognise_prepayment": ["expense_account", "prepayment_account"],
            "bad_debt_write_off": ["receivables_account", "irrecoverable_debt_account"],
            "doubtful_debt_allowance": ["bad_debt_expense_account", "allowance_account"],
        }

        for field_name in required_fields.get(adjustment_type, []):
            if not cleaned_data.get(field_name):
                self.add_error(field_name, "This field is required for the selected adjustment type.")

        return cleaned_data

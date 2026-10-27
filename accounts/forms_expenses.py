from decimal import Decimal

from django import forms

from .models import Account, Expense, ExpenseLineItem
from .services.calculations import calculate_vat


class ExpenseForm(forms.ModelForm):

    class Meta:
        model = Expense
        fields = [
            "expense_account",
            "payment_account",
            "expense_date",
            "description",
            "supplier_name",
            "reference",
        ]

        widgets = {
            "expense_account": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    )
                }
            ),
            "payment_account": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    )
                }
            ),
            "expense_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    )
                }
            ),
            "description": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    )
                }
            ),
            "supplier_name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    )
                }
            ),
            "reference": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    ),
                    "placeholder": "Optional reference",
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["expense_account"].queryset = (
            Account.objects
            .filter(
                type="EXPENSE",
                is_active=True,
            )
            .order_by("code")
        )

        self.fields["payment_account"].queryset = (
            Account.objects
            .filter(
                code__in=["1000", "1100"],
                is_active=True,
            )
            .order_by("code")
        )


class ExpenseLineItemForm(forms.ModelForm):

    class Meta:
        model = ExpenseLineItem
        fields = [
            "description",
            "quantity",
            "unit_price",
            "vat_rate",
        ]

        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 dark:border-slate-600 "
                        "dark:bg-slate-700 dark:text-white"
                    )
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 dark:border-slate-600 "
                        "dark:bg-slate-700 dark:text-white"
                    ),
                    "step": "0.01",
                    "min": "0.01",
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 dark:border-slate-600 "
                        "dark:bg-slate-700 dark:text-white"
                    ),
                    "step": "0.01",
                    "min": "0",
                }
            ),
            "vat_rate": forms.NumberInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 dark:border-slate-600 "
                        "dark:bg-slate-700 dark:text-white"
                    ),
                    "step": "0.01",
                    "min": "0",
                    "max": "100",
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        quantity = cleaned_data.get("quantity")
        unit_price = cleaned_data.get("unit_price")
        vat_rate = cleaned_data.get("vat_rate")

        if quantity is not None and quantity <= 0:
            self.add_error(
                "quantity",
                "Quantity must be greater than zero.",
            )

        if unit_price is not None and unit_price < 0:
            self.add_error(
                "unit_price",
                "Unit price cannot be negative.",
            )

        if vat_rate is not None and not 0 <= vat_rate <= 100:
            self.add_error(
                "vat_rate",
                "VAT rate must be between 0 and 100.",
            )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(commit=False)

        instance.vat_amount = calculate_vat(
            instance.net_amount,
            instance.vat_rate,
        )

        if commit:
            instance.save()

        return instance
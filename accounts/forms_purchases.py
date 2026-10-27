from django import forms
from contacts.models import Supplier
from .models import Purchase, PurchaseLineItem, PurchasePayment


class PurchaseForm(forms.ModelForm):

    class Meta:
        model = Purchase
        fields = [ "supplier", "purchase_date", "due_date", "reference", ]

        widgets = {
            "supplier": forms.Select(attrs={
                "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
            }),
            "purchase_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                }
            ),
            "reference": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["supplier"].queryset = Supplier.objects.filter(
            is_active=True
        )

    def clean(self):
        cleaned_data = super().clean()

        supplier = cleaned_data.get("supplier")

        if supplier:
            self.instance.supplier_name = supplier.name
            self.instance.supplier_email = supplier.email

        return cleaned_data

    
class PurchaseLineItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseLineItem
        fields = [
            "description",
            "quantity",
            "unit_price",
            "vat_rate",
            "vat_amount",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    )
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    ),
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    ),
                }
            ),
            "vat_rate": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    ),
                }
            ),
            "vat_amount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    ),
                }
            ),
        }

class PurchaseLineItemForm(forms.ModelForm):
    class Meta:
        model = PurchaseLineItem
        fields = [
            "description",
            "quantity",
            "unit_price",
        ]
        widgets = {
            "description": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    )
                }
            ),
            "quantity": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    ),
                }
            ),
            "unit_price": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0",
                    "class": (
                        "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                        "text-sm text-gray-900 dark:border-slate-600 dark:bg-slate-700 "
                        "dark:text-white"
                    )
                }
            ),
        }

class PurchasePaymentForm(forms.ModelForm):

    class Meta:
        model = PurchasePayment
        fields = [
            "payment_date",
            "amount",
            "reference",
        ]

        widgets = {
            "payment_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                }
            ),
            "reference": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 text-sm text-gray-900 focus:border-[#224B75] focus:outline-none focus:ring-1 focus:ring-[#224B75] dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                }
            ),
        }
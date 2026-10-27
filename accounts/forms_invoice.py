from django import forms

from .models import Invoice, InvoiceLineItem,Payment
from contacts.models import Customer
from .services.calculations import calculate_vat

class InvoiceForm(forms.ModelForm):

    class Meta:
        model = Invoice
        fields = [ "customer", "client_name", "client_email", "issue_date", "due_date"]

        widgets = {
            "customer": forms.Select(
                attrs={
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                             "text-gray-900 focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "client_name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                             "text-gray-900 focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "client_email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                             "text-gray-900 focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "issue_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                             "text-gray-900 focus:border-blue-500 focus:ring-blue-500"
                }
            ),
            "due_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-lg border border-gray-300 bg-white px-3 py-2 "
                             "text-gray-900 focus:border-blue-500 focus:ring-blue-500"
                }
            ),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.fields["customer"].queryset = Customer.objects.filter( is_active=True )

        # When creating a new invoice, populate the historical snapshot
        # from the selected customer.
        if not self.instance.pk:
            self.fields["client_name"].required = False
            self.fields["client_email"].required = False

    def clean(self):
        cleaned_data = super().clean()
        customer     = cleaned_data.get("customer")

        if customer:
            cleaned_data["client_name"] = customer.name
            cleaned_data["client_email"] = customer.email

        return cleaned_data


class InvoiceLineItemForm(forms.ModelForm):

    class Meta:
        model = InvoiceLineItem
        fields = [
            "description",
            "quantity",
            "unit_price",
            "vat_rate",
        ]

        widgets = {
            "description": forms.TextInput(attrs={
                "class": "w-full rounded-lg border border-gray-300 px-3 py-2 "
                         "dark:border-slate-600 dark:bg-slate-700 dark:text-white",
            }),
            "quantity": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-gray-300 px-3 py-2 "
                         "dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                "step": "0.01",
                "min": "0.01",
            }),
            "unit_price": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-gray-300 px-3 py-2 "
                         "dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                "step": "0.01",
                "min": "0",
            }),
            "vat_rate": forms.NumberInput(attrs={
                "class": "w-full rounded-lg border border-gray-300 px-3 py-2 "
                         "dark:border-slate-600 dark:bg-slate-700 dark:text-white",
                "step": "0.01",
                "min": "0",
                "max": "100",
            }),
        }

    from decimal import Decimal

from django.core.exceptions import ValidationError


def clean(self):
    super().clean()

    if self.quantity is not None and self.quantity <= 0:
        raise ValidationError({
            "quantity": "Quantity must be greater than zero."
        })

    if self.unit_price is not None and self.unit_price < 0:
        raise ValidationError({
            "unit_price": "Unit price cannot be negative."
        })

    if self.vat_rate is not None:
        if not Decimal("0") <= self.vat_rate <= Decimal("100"):
            raise ValidationError({
                "vat_rate": "VAT rate must be between 0 and 100."
            })

    # Existing line: check the CURRENT invoice status and ORIGINAL
    # database values, rather than relying on cached relationships.
    if self.pk and self.invoice_id:
        invoice_status = (
            Invoice.objects
            .filter(pk=self.invoice_id)
            .values_list("status", flat=True)
            .first()
        )

        if invoice_status in {
            "POSTED",
            "SENT",
            "PARTIAL",
            "PAID",
            "VOID",
        }:
            original = (
                type(self)
                .objects
                .filter(pk=self.pk)
                .values(
                    "description",
                    "quantity",
                    "unit_price",
                    "vat_rate",
                    "vat_amount",
                )
                .first()
            )

            if original is None:
                return

            changed = (
                self.description != original["description"]
                or self.quantity != original["quantity"]
                or self.unit_price != original["unit_price"]
                or self.vat_rate != original["vat_rate"]
                or self.vat_amount != original["vat_amount"]
            )

            if changed:
                raise ValidationError(
                    "Invoice lines cannot be changed after "
                    "the invoice has been posted."
                )

from decimal import Decimal

from django import forms

from .models import Invoice, InvoiceLineItem, Payment
from contacts.models import Customer
from .services.calculations import calculate_vat


class InvoicePaymentForm(forms.ModelForm):

    class Meta:
        model = Payment
        fields = [
            "payment_date",
            "amount",
            "reference",
        ]

        widgets = {
            "payment_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    ),
                }
            ),
            "amount": forms.NumberInput(
                attrs={
                    "step": "0.01",
                    "min": "0.01",
                    "inputmode": "decimal",
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    ),
                }
            ),
            "reference": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "bg-white px-3 py-2 text-gray-900 "
                        "focus:border-blue-500 focus:ring-blue-500"
                    ),
                    "placeholder": "Bank/payment reference",
                }
            ),
        }

    def clean_amount(self):
        amount = self.cleaned_data.get("amount")

        if amount is None:
            raise forms.ValidationError(
                "Enter a payment amount."
            )

        if amount <= 0:
            raise forms.ValidationError(
                "Payment amount must be greater than zero."
            )

        return amount.quantize(Decimal("0.01"))
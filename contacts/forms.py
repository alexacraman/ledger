from django import forms

from .models import Customer, Supplier


class CustomerForm(forms.ModelForm):
    class Meta:
        model = Customer
        fields = [
            "name",
            "email",
            "phone",
            "address",
            "postcode",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "postcode": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-slate-300",
                }
            ),
        }

class SupplierForm(forms.ModelForm):
    class Meta:
        model = Supplier
        fields = [
            "name",
            "email",
            "phone",
            "address",
            "postcode",
            "is_active",
        ]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "rows": 4,
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "postcode": forms.TextInput(
                attrs={
                    "class": "w-full rounded-lg border border-slate-300 px-3 py-2 "
                             "focus:border-sky-500 focus:outline-none focus:ring-1 focus:ring-sky-500",
                }
            ),
            "is_active": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-slate-300",
                }
            ),
        }


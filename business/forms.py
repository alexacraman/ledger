from django import forms

from .models import BusinessSettings


class BusinessSettingsForm(forms.ModelForm):

    class Meta:
        model = BusinessSettings
        fields = [
            "business_name",
            "accounting_basis",
            "vat_registered",
            "vat_scheme",
        ]

        widgets = {
            "business_name": forms.TextInput(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 focus:border-[#224B75] "
                        "focus:ring-[#224B75]"
                    ),
                }
            ),
            "accounting_basis": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 focus:border-[#224B75] "
                        "focus:ring-[#224B75]"
                    ),
                }
            ),
            "vat_registered": forms.CheckboxInput(
                attrs={
                    "class": "h-4 w-4 rounded border-gray-300",
                }
            ),
            "vat_scheme": forms.Select(
                attrs={
                    "class": (
                        "w-full rounded-lg border border-gray-300 "
                        "px-3 py-2 focus:border-[#224B75] "
                        "focus:ring-[#224B75]"
                    ),
                }
            ),
        }

    def clean(self):
        cleaned_data = super().clean()

        vat_registered = cleaned_data.get("vat_registered")
        vat_scheme = cleaned_data.get("vat_scheme")

        if not vat_registered:
            cleaned_data["vat_scheme"] = ""

        elif not vat_scheme:
            raise forms.ValidationError(
                "Please select a VAT scheme."
            )

        return cleaned_data
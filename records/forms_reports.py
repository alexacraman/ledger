from decimal import Decimal

from django import forms
from django.utils import timezone

class WorkReportForm(forms.Form):
    start_date = forms.DateField(
        label="From",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    end_date = forms.DateField(
        label="To",
        widget=forms.DateInput(attrs={"type": "date"}),
    )
    monthly_allowance = forms.DecimalField(
        label="Paid hours per month",
        initial=Decimal("2.00"),
        min_value=Decimal("0"),
        max_digits=5,
        decimal_places=2,
        help_text="Your agreed monthly paid-hours allowance.",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        today = timezone.localdate()

        if not self.is_bound:
            self.initial.setdefault("start_date", today.replace(day=1))
            self.initial.setdefault("end_date", today)

        for field in self.fields.values():
            field.widget.attrs.update({
                "class": (
                    "w-full rounded-lg border border-slate-300 "
                    "bg-white px-3 py-2.5 text-sm text-slate-700 "
                    "focus:border-[#224B75] focus:outline-none "
                    "focus:ring-2 focus:ring-[#224B75]/20"
                )
            })

    def clean(self):
        cleaned_data = super().clean()
        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            self.add_error(
                "end_date",
                "The end date must be on or after the start date.",
            )

        return cleaned_data

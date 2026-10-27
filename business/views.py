from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .forms import BusinessSettingsForm
from .services.settings import (
    financial_activity_exists,
    get_business_settings,
    update_business_settings,
)


@login_required
def settings_view(request):

    settings = get_business_settings()

    if request.method == "POST":

        form = BusinessSettingsForm(
            request.POST,
            instance=settings,
        )

        if form.is_valid():

            try:
                update_business_settings(
                    business_name=form.cleaned_data["business_name"],
                    accounting_basis=form.cleaned_data["accounting_basis"],
                    vat_registered=form.cleaned_data["vat_registered"],
                    vat_scheme=form.cleaned_data["vat_scheme"],
                )

            except ValidationError as exc:
                form.add_error(
                    None,
                    exc.message,
                )

            else:
                messages.success(
                    request,
                    "Business settings have been updated.",
                )

                return redirect(
                    "business:settings",
                )

    else:
        form = BusinessSettingsForm(
            instance=settings,
        )

    return render(
        request,
        "business/settings.html",
        {
            "form": form,
            "financial_activity_exists": financial_activity_exists(),
        },
    )
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.core.exceptions import ValidationError

from contacts.models import Supplier
from .forms_purchases import PurchaseForm, PurchaseLineItemForm, PurchasePaymentForm
from .models import Purchase, PurchaseLineItem, Account

from django.db import transaction

from .services.purchase_numbers import allocate_purchase_number, get_next_purchase_number
from .services.purchases import record_purchase_payment, post_purchase

@login_required
def purchase_list(request):
    purchases = Purchase.objects .select_related("supplier").order_by("-purchase_number", "-id") 

    return render( request, "accounts/purchases/list.html", {"purchases": purchases}, )

@login_required
def purchase_create(request):
    if request.method == "POST":
        form = PurchaseForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                purchase = form.save(commit=False)
                purchase.purchase_number = allocate_purchase_number()
                purchase.status = "DRAFT"
                purchase.save()
            return redirect( "accounts:purchase_detail", pk=purchase.pk, )
    else:
        form = PurchaseForm()

        supplier_id = request.GET.get("supplier")

        if supplier_id:
            supplier = get_object_or_404( Supplier, pk=supplier_id, is_active=True, )
            form.initial["supplier"] = supplier

    return render( request, "accounts/purchases/form.html", { "form": form, "purchase_number_preview": get_next_purchase_number(), }, )

@login_required
def purchase_detail(request, pk):
    purchase = get_object_or_404( Purchase.objects.select_related("supplier"), pk=pk)
    return render( request, "accounts/purchases/detail.html", {"purchase": purchase}, )

@login_required
def purchase_update(request, pk):
    purchase = get_object_or_404(Purchase, pk=pk)

    if purchase.status != "DRAFT":
        messages.error( request, "Only draft purchases can be edited.", )
        return redirect( "accounts:purchase_detail", pk=purchase.pk, )

    if request.method == "POST":
        form = PurchaseForm(request.POST, instance=purchase)
        if form.is_valid():
            form.save()
            return redirect( "accounts:purchase_detail", pk=purchase.pk, )
    else:
        form = PurchaseForm(instance=purchase)
    return render( request, "accounts/purchases/form.html", { "form": form, "purchase": purchase, }, )

@login_required
def purchase_line_create(request, purchase_id):
    purchase = get_object_or_404( Purchase, pk=purchase_id)

    if purchase.status != "DRAFT":
        messages.error( request, "Line items can only be added to draft purchases.", )
        return redirect( "accounts:purchase_detail", pk=purchase.pk, )

    if request.method == "POST":
        form = PurchaseLineItemForm(request.POST)

        if form.is_valid():
            line = form.save(commit=False)
            line.purchase = purchase
            # Currently not VAT registered.
            line.vat_rate = 0
            line.vat_amount = 0
            line.save()
            return redirect( "accounts:purchase_detail", pk=purchase.pk, )
    else:
        form = PurchaseLineItemForm()
    return render( request, "accounts/purchases/line_form.html", { "form": form, "purchase": purchase, }, )

@login_required
def purchase_line_update(request, purchase_id, line_id):
    purchase = get_object_or_404( Purchase, pk=purchase_id, )
    line     = get_object_or_404( PurchaseLineItem, pk=line_id, purchase=purchase, )

    if purchase.status != "DRAFT":
        messages.error( request, "Line items can only be edited on draft purchases.", )
        return redirect( "accounts:purchase_detail", pk=purchase.pk, )

    if request.method == "POST":
        form = PurchaseLineItemForm( request.POST, instance=line, )
        if form.is_valid():
            line = form.save(commit=False)
            line.vat_rate = 0
            line.vat_amount = 0
            line.save()
            return redirect( "accounts:purchase_detail", pk=purchase.pk, )
    else:
        form = PurchaseLineItemForm(instance=line)
    return render( request, "accounts/purchases/line_form.html", { "form": form, "purchase": purchase, "line": line, }, )

@login_required
def purchase_line_delete(request, purchase_id, line_id):
    purchase = get_object_or_404( Purchase, pk=purchase_id, )
    line     = get_object_or_404( PurchaseLineItem, pk=line_id, purchase=purchase, )

    if purchase.status != "DRAFT":
        messages.error( request, "Line items can only be deleted from draft purchases.", )
        return redirect( "accounts:purchase_detail", pk=purchase.pk, )

    if request.method == "POST":
        line.delete()
        return redirect( "accounts:purchase_detail", pk=purchase.pk, )
    return render( request, "accounts/purchases/line_confirm_delete.html", { "purchase": purchase, "line": line, }, )



#payments
@login_required
def purchase_payment_create(request, pk):
    purchase = get_object_or_404( Purchase.objects.select_related("supplier"), pk=pk, )

    if purchase.status not in ("POSTED", "PARTIAL"):
        messages.error( request, "Payments can only be added to posted purchases.", )
        return redirect( "accounts:purchase_detail", pk=purchase.pk, )

    if request.method == "POST":
        form = PurchasePaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            try:
                bank_account         = Account.objects.get(code="1000")
                accounts_payable_acc = Account.objects.get(code="2000")
                purchases_acc        = Account.objects.get(code="5000")

                record_purchase_payment(
                    purchase=purchase,
                    amount=payment.amount,
                    bank_account=bank_account,
                    accounts_payable_acc=accounts_payable_acc,
                    purchases_acc=purchases_acc,
                    payment_date=payment.payment_date,
                    reference=payment.reference,
                )

            except (Account.DoesNotExist, ValidationError) as exc:
                form.add_error(None, str(exc))

            else:
                messages.success( request, "Purchase payment recorded successfully.", )
                return redirect( "accounts:purchase_detail", pk=purchase.pk, )
    else:
        form = PurchasePaymentForm(
            initial={
                "payment_date": purchase.purchase_date,
                "amount": purchase.amount_outstanding,
            }
        )
    return render( request, "accounts/purchases/payment_form.html", { "form": form, "purchase": purchase, }, )

@login_required
def purchase_post(request, pk):
    if request.method != "POST":
        return redirect( "accounts:purchase_detail", pk=pk, )

    purchase = get_object_or_404(Purchase, pk=pk)
    try:
        accounts_payable_acc = Account.objects.get(code="2000")
        purchases_acc = Account.objects.get(code="5000")

        post_purchase(
            purchase=purchase,
            purchases_acc=purchases_acc,
            vat_reclaimable_acc=None,
            accounts_payable_acc=accounts_payable_acc,
        )
    except (Account.DoesNotExist, ValidationError) as exc:
        messages.error(request, str(exc))
    else:
        messages.success( request, f"Purchase {purchase.purchase_number} posted successfully.", )
    return redirect( "accounts:purchase_detail", pk=purchase.pk, )
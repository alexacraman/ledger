from decimal import Decimal
from django.contrib import messages
from django.db import transaction
from django.core.exceptions import ValidationError
from django.http import HttpResponse
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render


from accounts.services.invoice_numbers import get_next_invoice_number, allocate_invoice_number 
from accounts.services.invoice_delivery import email_invoice
from accounts.services.invoice_documents import build_invoice_pdf
from accounts.services.sales import post_invoice, mark_invoice_sent, record_invoice_payment

from contacts.models import Customer

from .forms_invoice import InvoiceForm, InvoiceLineItemForm, InvoicePaymentForm
from .models import Invoice, InvoiceLineItem, Account


@login_required
def invoice_list(request):
    invoices = Invoice.objects.select_related("customer").order_by("-issue_date", "-id") 
    return render(request, "accounts/invoices/invoice_list.html", { "invoices": invoices, })

@login_required
def invoice_create(request):
    if request.method == "POST":
        form = InvoiceForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                invoice = form.save(commit=False)
                invoice.invoice_number = allocate_invoice_number()
                invoice.status = "DRAFT"
                invoice.save()
            return redirect( "accounts:invoice_detail", pk=invoice.pk)
    else:
        form = InvoiceForm()
        customer_id = request.GET.get("customer")
        
        if customer_id: 
            customer = get_object_or_404(Customer, pk=customer_id, is_active=True)
            form.initial["customer"] = customer

    return render( request, "accounts/invoices/invoice_form.html", { "form": form, "invoice_number_preview": get_next_invoice_number(), }, )

@login_required
def invoice_detail(request, pk):
    invoice = get_object_or_404( Invoice.objects.select_related("customer"), pk=pk, )
    return render( request, "accounts/invoices/invoice_detail.html", { "invoice": invoice, }, )


@login_required
def invoice_update(request, pk):
    invoice = get_object_or_404( Invoice.objects.select_related("customer"), pk=pk, )

    if invoice.status != "DRAFT":
        messages.error( request, "Only draft invoices can be edited.", )
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    if request.method == "POST":
        form = InvoiceForm( request.POST, instance=invoice, )

        if form.is_valid():
            form.save()

            messages.success( request, f"Invoice {invoice.invoice_number} updated.", )

            return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    else:
        form = InvoiceForm(instance=invoice)

    return render( request, "accounts/invoices/invoice_form.html", { "form": form, "invoice": invoice, "title": "Edit Invoice", }, )


# Line items for the invoice
@login_required
def invoice_line_create(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if invoice.status != "DRAFT":
        messages.error( request, "Line items can only be added to draft invoices.", )
        return redirect("accounts:invoice_detail", pk=invoice.pk)

    if request.method == "POST":
        form = InvoiceLineItemForm(request.POST)

        if form.is_valid():
            line = form.save(commit=False)
            line.invoice = invoice
            line.vat_rate = 0
            line.vat_amount = 0
            line.save()

            messages.success( request, "Invoice line added.", )
            return redirect( "accounts:invoice_detail", pk=invoice.pk, )
    else:
        form = InvoiceLineItemForm()

    return render( request, "accounts/invoices/line_form.html", { "form": form, "invoice": invoice, }, )

@login_required
def invoice_line_update(request, invoice_pk, line_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)
    line    = get_object_or_404(InvoiceLineItem, pk=line_pk, invoice=invoice, )

    if invoice.status != "DRAFT":
        messages.error( request, "Line items can only be changed on draft invoices.", )
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    if request.method == "POST":
        form = InvoiceLineItemForm( request.POST, instance=line, )

        if form.is_valid():
            form.save()

            messages.success( request, "Invoice line updated.", )

            return redirect( "accounts:invoice_detail", pk=invoice.pk, )
    else:
        form = InvoiceLineItemForm(instance=line)

    return render( request, "accounts/invoices/line_form.html", { "form": form, "invoice": invoice, "line": line, }, )

@login_required
def invoice_line_delete(request, invoice_pk, line_pk):
    invoice = get_object_or_404(Invoice, pk=invoice_pk)

    line = get_object_or_404( InvoiceLineItem, pk=line_pk, invoice=invoice, )

    if invoice.status != "DRAFT":
        messages.error( request, "Line items cannot be deleted from a finalised invoice.", )
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    if request.method == "POST":
        line.delete()
        messages.success( request, "Invoice line deleted.", )
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    return render( request, "accounts/invoices/line_confirm_delete.html", { "invoice": invoice, "line": line, }, )


@login_required
def invoice_post(request, pk):
    if request.method != "POST":
        return redirect("accounts:invoice_detail", pk=pk)

    invoice = get_object_or_404(Invoice, pk=pk)

    try:
        accounts_receivable_acc = Account.objects.get(code="1200")
        sales_revenue_acc = Account.objects.get(code="4000")
        vat_liability_acc = Account.objects.get(code="2100")

        post_invoice(
            invoice=invoice,
            accounts_receivable_acc=accounts_receivable_acc,
            sales_revenue_acc=sales_revenue_acc,
            vat_liability_acc=vat_liability_acc,
        )

    except (Account.DoesNotExist, ValidationError, NotImplementedError) as exc:
        messages.error(request, str(exc))

    else:
        messages.success( request, f"Invoice {invoice.invoice_number} posted successfully.", )

    return redirect( "accounts:invoice_detail", pk=invoice.pk, )


@login_required
def invoice_mark_sent(request, pk):
    if request.method != "POST":
        return redirect("accounts:invoice_detail", pk=pk)
    invoice = get_object_or_404(Invoice, pk=pk)
    try:
        mark_invoice_sent(invoice)
    except ValidationError as exc:
        messages.error(request, str(exc))
    else:
        messages.success( request, f"Invoice {invoice.invoice_number} marked as sent.", )
    return redirect( "accounts:invoice_detail", pk=invoice.pk, )


@login_required
def invoice_payment_create(request, pk):
    invoice = get_object_or_404( Invoice.objects.select_related("customer"), pk=pk, )

    if invoice.status not in ("POSTED", "SENT", "PARTIAL"):
        messages.error( request, "Payments can only be added to posted invoices.", )
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    if invoice.amount_outstanding <= 0:
        messages.error( request, "This invoice has no outstanding balance.", )
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    if request.method == "POST":
        form = InvoicePaymentForm(request.POST)

        if form.is_valid():
            payment = form.save(commit=False)

            try:
                bank_account = Account.objects.get(code="1000")
                accounts_receivable_acc = Account.objects.get(code="1200")
                sales_revenue_acc = Account.objects.get(code="4000")

                record_invoice_payment(
                    invoice=invoice,
                    amount=payment.amount,
                    bank_account=bank_account,
                    accounts_receivable_acc=accounts_receivable_acc,
                    sales_revenue_acc=sales_revenue_acc,
                    payment_date=payment.payment_date,
                    reference=payment.reference,
                )

            except ( Account.DoesNotExist, ValidationError, NotImplementedError, ) as exc:
                form.add_error(None, str(exc))

            else:
                messages.success( request, "Invoice payment recorded successfully.", )
                return redirect( "accounts:invoice_detail", pk=invoice.pk, )
    else:
        form = InvoicePaymentForm(
        initial={ "payment_date": invoice.due_date, "amount": invoice.amount_outstanding.quantize( Decimal("0.01") ), }
        )

    return render( request, "accounts/invoices/payment_form.html", { "form": form, "invoice": invoice, }, )


@login_required
def invoice_pdf(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    try:
        pdf = build_invoice_pdf(invoice)
    except ValidationError as exc:
        messages.error(request, exc.message)
        return redirect("accounts:invoice_detail", pk=invoice.pk)

    response = HttpResponse( pdf, content_type="application/pdf", )

    response["Content-Disposition"] = (
        f'inline; filename="{invoice.invoice_number}.pdf"'
    )
    return response

@login_required
def invoice_email(request, pk):
    invoice = get_object_or_404(Invoice, pk=pk)

    if request.method != "POST":
        return redirect( "accounts:invoice_detail", pk=invoice.pk, )

    try:
        delivery = email_invoice(invoice=invoice)
    except ValidationError as exc:
        messages.error(request, exc.message)
    else:
        messages.success( request, f"Invoice emailed to {delivery.recipient}.", )

    return redirect( "accounts:invoice_detail", pk=invoice.pk, )
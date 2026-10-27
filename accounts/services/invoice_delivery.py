from django.core.exceptions import ValidationError
from django.core.mail import EmailMessage
from django.utils import timezone

from accounts.models import Invoice, InvoiceEmail
from .invoice_documents import build_invoice_pdf


VALID_EMAIL_STATUSES = {
    "POSTED",
    "SENT",
    "PARTIAL",
    "PAID",
}


def email_invoice(*, invoice):
    """
    Generate the invoice PDF, email it to the customer,
    record the delivery attempt, and mark the invoice as SENT
    when appropriate.
    """

    invoice = Invoice.objects.get(pk=invoice.pk)

    if invoice.status not in VALID_EMAIL_STATUSES:
        raise ValidationError( "Only posted invoices can be emailed." )

    if not invoice.client_email:
        raise ValidationError( "This invoice does not have a customer email address." )

    pdf = build_invoice_pdf(invoice)

    subject = f"Invoice {invoice.invoice_number}"

    body = (
    f"Dear {invoice.client_name},\n\n"
    f"Please find attached invoice {invoice.invoice_number}.\n\n"
    f"Invoice total: £{invoice.total_gross:.2f}\n"
    f"Due date: {invoice.due_date.strftime('%d/%m/%Y')}\n\n"
    f"Kind regards"
)

    email = EmailMessage(subject=subject, body=body, to=[invoice.client_email])
    email.attach( f"{invoice.invoice_number}.pdf", pdf, "application/pdf",)

    try:
        sent_count = email.send(fail_silently=False)

        if sent_count != 1:
            raise RuntimeError( "The email backend did not report a successful send." )

    except Exception as exc:
        InvoiceEmail.objects.create(invoice=invoice, recipient=invoice.client_email, subject=subject, status="FAILED", error_message=str(exc)[:5000], )
        raise ValidationError(
            "The invoice email could not be sent."
        ) from exc

    delivery = InvoiceEmail.objects.create(invoice=invoice, recipient=invoice.client_email, subject=subject, status="SENT", sent_at=timezone.now(), )

    if invoice.status == "POSTED":
        invoice.status = "SENT"
        invoice.save(update_fields=["status"])

    return delivery
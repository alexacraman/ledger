from django.db import transaction
from accounts.models import Invoice, InvoiceNumberSequence

SEQUENCE_NAME = "INVOICE"

def get_next_invoice_number():
    """
    Return the next invoice number without consuming it.
    """

    sequence, _ = InvoiceNumberSequence.objects.get_or_create(
        name=SEQUENCE_NAME,
        defaults={"next_number": 1},
    )

    highest_invoice_number = Invoice.objects.filter(invoice_number__startswith="INV-").values_list("invoice_number", flat=True)

    highest_number = 0

    for invoice_number in highest_invoice_number:
        try:
            number = int(invoice_number.removeprefix("INV-"))
            highest_number = max(highest_number, number)
        except ValueError:
            continue

    next_number = max(sequence.next_number, highest_number + 1)

    return f"INV-{next_number:04d}"


@transaction.atomic
def allocate_invoice_number():
    """
    Atomically allocate the next invoice number.
    """

    sequence, _ = InvoiceNumberSequence.objects.select_for_update().get_or_create( name=SEQUENCE_NAME, defaults={"next_number": 1}, )
    
    # Make sure the sequence cannot fall behind existing invoices.
    existing_numbers = Invoice.objects.filter(invoice_number__startswith="INV-").values_list("invoice_number", flat=True)

    highest_number = 0

    for invoice_number in existing_numbers:
        try:
            number = int(invoice_number.removeprefix("INV-"))
            highest_number = max(highest_number, number)
        except ValueError:
            continue

    number = max(sequence.next_number, highest_number + 1)

    sequence.next_number = number + 1
    sequence.save(update_fields=["next_number"])

    return f"INV-{number:04d}"
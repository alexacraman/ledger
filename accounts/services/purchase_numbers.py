from django.db import transaction

from accounts.models import Purchase, PurchaseNumberSequence


SEQUENCE_NAME = "PURCHASE"


def get_next_purchase_number():
    """
    Return the next purchase number without allocating it.

    Used for displaying a preview before a purchase is saved.
    """

    sequence, _ = PurchaseNumberSequence.objects.get_or_create( name=SEQUENCE_NAME, defaults={"next_number": 1}, )

    highest_purchase_number = Purchase.objects.filter(purchase_number__startswith="PUR-").values_list("purchase_number", flat=True)
    
    highest_number = 0

    for purchase_number in highest_purchase_number:
        try:
            number = int(purchase_number.removeprefix("PUR-"))
            highest_number = max(highest_number, number)
        except ValueError:
            continue

    next_number = max( sequence.next_number, highest_number + 1, )

    return f"PUR-{next_number:04d}"


@transaction.atomic
def allocate_purchase_number():
    """
    Allocate and return the next purchase number.

    Uses row locking so that two purchases cannot receive
    the same number.

    Also self-heals if the sequence falls behind the highest
    existing purchase number.
    """

    sequence, _ = PurchaseNumberSequence.objects.select_for_update().get_or_create( name=SEQUENCE_NAME, defaults={"next_number": 1}, )
    
    existing_numbers = Purchase.objects.filter(purchase_number__startswith="PUR-").values_list("purchase_number", flat=True)
    
    highest_number = 0

    for purchase_number in existing_numbers:
        try:
            number = int(purchase_number.removeprefix("PUR-"))
            highest_number = max(highest_number, number)
        except ValueError:
            continue

    number = max( sequence.next_number, highest_number + 1, )

    sequence.next_number = number + 1
    sequence.save(update_fields=["next_number"])

    return f"PUR-{number:04d}"
from decimal import Decimal, ROUND_HALF_UP

MONEY_PLACES = Decimal("0.01")

def calculate_vat(net_amount, vat_rate):
    """
    Calculate VAT from a net amount and VAT rate.
    Returns a monetary value rounded to 2 decimal places.
    """

    net_amount = Decimal(str(net_amount))
    vat_rate   = Decimal(str(vat_rate))

    vat_amount = net_amount * vat_rate / Decimal("100")

    return vat_amount.quantize( MONEY_PLACES, rounding=ROUND_HALF_UP, )
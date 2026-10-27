
from decimal import Decimal

from .periods import get_or_create_period_for_date
from .reports import profit_and_loss


# ============================================================================
# 2026/27 UK TAX ASSUMPTIONS
# ============================================================================

PERSONAL_ALLOWANCE = Decimal("12570.00")

INCOME_TAX_BASIC_RATE = Decimal("0.20")
INCOME_TAX_BASIC_RATE_LIMIT = Decimal("50270.00")

CLASS_4_LOWER_PROFITS_LIMIT = Decimal("12570.00")
CLASS_4_UPPER_PROFITS_LIMIT = Decimal("50270.00")
CLASS_4_MAIN_RATE = Decimal("0.06")
CLASS_4_ADDITIONAL_RATE = Decimal("0.02")


# ============================================================================
# INCOME TAX
# ============================================================================

def calculate_income_tax(
    *,
    total_net_income,
):
    """
    Calculate estimated Income Tax from total net income.

    Current supported assumptions:

    - England, Wales or Northern Ireland
    - Standard Personal Allowance
    - No other taxable income
    - No additional tax reliefs or adjustments
    - Income does not exceed the basic-rate band
    """

    income = Decimal(total_net_income)

    if income <= Decimal("0.00"):
        return Decimal("0.00")

    if income <= PERSONAL_ALLOWANCE:
        return Decimal("0.00")

    if income > INCOME_TAX_BASIC_RATE_LIMIT:
        raise NotImplementedError(
            "Income above the basic-rate band is not yet supported."
        )

    taxable_income = income - PERSONAL_ALLOWANCE

    return (
        taxable_income * INCOME_TAX_BASIC_RATE
    ).quantize(Decimal("0.01"))


# ============================================================================
# CLASS 4 NATIONAL INSURANCE
# ============================================================================

def calculate_class_4_national_insurance(
    *,
    self_employment_profit,
):
    """
    Calculate estimated Class 4 National Insurance.

    2026/27 rates:

    - 0% up to £12,570
    - 6% on profits above £12,570 up to £50,270
    - 2% on profits above £50,270

    Class 4 is calculated from self-employed profits, not from
    taxable income after the Income Tax Personal Allowance.
    """

    profit = Decimal(self_employment_profit)

    if profit <= Decimal("0.00"):
        return Decimal("0.00")

    if profit <= CLASS_4_LOWER_PROFITS_LIMIT:
        return Decimal("0.00")

    # Profit within the main Class 4 band.
    main_band_profit = min(
        profit,
        CLASS_4_UPPER_PROFITS_LIMIT,
    ) - CLASS_4_LOWER_PROFITS_LIMIT

    main_band_contribution = (
        main_band_profit * CLASS_4_MAIN_RATE
    )

    # Profit above the Upper Profits Limit.
    additional_band_profit = max(
        profit - CLASS_4_UPPER_PROFITS_LIMIT,
        Decimal("0.00"),
    )

    additional_band_contribution = (
        additional_band_profit * CLASS_4_ADDITIONAL_RATE
    )

    return (
        main_band_contribution
        + additional_band_contribution
    ).quantize(Decimal("0.01"))


# ============================================================================
# TAX POSITION
# ============================================================================

def calculate_tax_position(
    *,
    total_net_income,
):
    """
    Return the figures used to calculate estimated Income Tax.

    Class 4 National Insurance is not included here because this
    function represents the Income Tax calculation itself.
    """

    income = Decimal(total_net_income)

    if income < Decimal("0.00"):
        income = Decimal("0.00")

    if income <= PERSONAL_ALLOWANCE:
        taxable_income = Decimal("0.00")
    else:
        taxable_income = (
            income - PERSONAL_ALLOWANCE
        ).quantize(Decimal("0.01"))

    income_tax = calculate_income_tax(
        total_net_income=income,
    )

    class_4_national_insurance = (
        calculate_class_4_national_insurance(
            self_employment_profit=income,
        )
    )

    return {
        "total_net_income": income,
        "personal_allowance": PERSONAL_ALLOWANCE,
        "taxable_income": taxable_income,
        "income_tax": income_tax,
        "class_4_national_insurance": class_4_national_insurance,
        "estimated_tax_and_class_4": (
            income_tax + class_4_national_insurance
        ).quantize(Decimal("0.01")),
    }


# ============================================================================
# TAX YEAR
# ============================================================================

def calculate_tax_position_for_tax_year(
    *,
    for_date,
):
    """
    Calculate the estimated tax position for the UK tax year
    containing `for_date`.

    The existing AccountingPeriod infrastructure defines the tax
    year as:

        6 April → 5 April

    Current assumptions:

    - cash-basis business accounting
    - business profit is taken from the posted ledger
    - England, Wales or Northern Ireland
    - standard Personal Allowance
    - no other personal taxable income
    - no additional tax reliefs or adjustments
    """

    period = get_or_create_period_for_date(
        for_date,
    )

    report = profit_and_loss(
        date_from=period.start_date,
        date_to=period.end_date,
    )

    tax_position = calculate_tax_position(
        total_net_income=report["net_profit"],
    )

    return {
        "period": period,
        "date_from": period.start_date,
        "date_to": period.end_date,
        "total_revenue": report["total_revenue"],
        "total_expenses": report["total_expenses"],
        "net_profit": report["net_profit"],
        **tax_position,
    }


def get_tax_year_label(period):
    """
    Return a standard UK tax-year label.

    Example:
        6 April 2026 → 5 April 2027
        becomes:
        2026/27
    """

    start_year = period.start_date.year
    end_year = period.end_date.year

    return f"{start_year}/{str(end_year)[-2:]}"


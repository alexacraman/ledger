
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase

from accounts.models import (
    Account,
    AccountingPeriod,
)
from accounts.services.journal import create_journal_entry
from accounts.services.tax import (
    CLASS_4_ADDITIONAL_RATE,
    CLASS_4_LOWER_PROFITS_LIMIT,
    CLASS_4_MAIN_RATE,
    CLASS_4_UPPER_PROFITS_LIMIT,
    INCOME_TAX_BASIC_RATE_LIMIT,
    PERSONAL_ALLOWANCE,
    calculate_class_4_national_insurance,
    calculate_income_tax,
    calculate_tax_position,
    calculate_tax_position_for_tax_year,
    get_tax_year_label,
)


# ============================================================================
# INCOME TAX
# ============================================================================

class IncomeTaxCalculationTests(SimpleTestCase):

    def test_zero_income(self):
        tax = calculate_income_tax(
            total_net_income=Decimal("0.00"),
        )

        self.assertEqual(
            tax,
            Decimal("0.00"),
        )

    def test_negative_income(self):
        tax = calculate_income_tax(
            total_net_income=Decimal("-500.00"),
        )

        self.assertEqual(
            tax,
            Decimal("0.00"),
        )

    def test_income_below_personal_allowance(self):
        tax = calculate_income_tax(
            total_net_income=Decimal("10000.00"),
        )

        self.assertEqual(
            tax,
            Decimal("0.00"),
        )

    def test_income_at_personal_allowance(self):
        tax = calculate_income_tax(
            total_net_income=PERSONAL_ALLOWANCE,
        )

        self.assertEqual(
            tax,
            Decimal("0.00"),
        )

    def test_one_pound_above_personal_allowance(self):
        tax = calculate_income_tax(
            total_net_income=Decimal("12571.00"),
        )

        self.assertEqual(
            tax,
            Decimal("0.20"),
        )

    def test_income_of_twenty_thousand(self):
        tax = calculate_income_tax(
            total_net_income=Decimal("20000.00"),
        )

        self.assertEqual(
            tax,
            Decimal("1486.00"),
        )

    def test_income_at_basic_rate_limit(self):
        tax = calculate_income_tax(
     
            total_net_income=INCOME_TAX_BASIC_RATE_LIMIT,
        )

        self.assertEqual(
            tax,
            Decimal("7540.00"),
        )

    def test_income_above_basic_rate_limit_not_supported(self):
        with self.assertRaises(NotImplementedError):
            calculate_income_tax(
                total_net_income=Decimal("50271.00"),
            )


# ============================================================================
# CLASS 4 NATIONAL INSURANCE
# ============================================================================

class Class4NationalInsuranceTests(SimpleTestCase):

    def test_zero_profit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=Decimal("0.00"),
        )

        self.assertEqual(
            ni,
            Decimal("0.00"),
        )

    def test_negative_profit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=Decimal("-500.00"),
        )

        self.assertEqual(
            ni,
            Decimal("0.00"),
        )

    def test_profit_below_lower_profits_limit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=Decimal("10000.00"),
        )

        self.assertEqual(
            ni,
            Decimal("0.00"),
        )

    def test_profit_at_lower_profits_limit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=CLASS_4_LOWER_PROFITS_LIMIT,
        )

        self.assertEqual(
            ni,
            Decimal("0.00"),
        )

    def test_one_pound_above_lower_profits_limit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=Decimal("12571.00"),
        )

        self.assertEqual(
            ni,
            Decimal("0.06"),
        )

    def test_profit_of_twenty_thousand(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=Decimal("20000.00"),
        )

        self.assertEqual(
            ni,
            Decimal("445.80"),
        )

    def test_profit_at_upper_profits_limit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=CLASS_4_UPPER_PROFITS_LIMIT,
        )

        expected = (
            (
                CLASS_4_UPPER_PROFITS_LIMIT
                - CLASS_4_LOWER_PROFITS_LIMIT
            )
            * CLASS_4_MAIN_RATE
        ).quantize(Decimal("0.01"))

        self.assertEqual(
            ni,
            expected,
        )

        self.assertEqual(
            ni,
            Decimal("2262.00"),
        )

    def test_profit_above_upper_profits_limit(self):
        ni = calculate_class_4_national_insurance(
            self_employment_profit=Decimal("60000.00"),
        )

        main_band_profit = (
            CLASS_4_UPPER_PROFITS_LIMIT
            - CLASS_4_LOWER_PROFITS_LIMIT
        )

        additional_band_profit = (
            Decimal("60000.00")
            - CLASS_4_UPPER_PROFITS_LIMIT
        )

        expected = (
            (
                main_band_profit * CLASS_4_MAIN_RATE
            )
            + (
                additional_band_profit
                * CLASS_4_ADDITIONAL_RATE
            )
        ).quantize(Decimal("0.01"))

        self.assertEqual(
            ni,
            expected,
        )

        self.assertEqual(
            ni,
            Decimal("2456.60"),
        )


# ============================================================================
# TAX POSITION
# ============================================================================

class TaxPositionTests(SimpleTestCase):

    def test_income_below_personal_allowance(self):
        position = calculate_tax_position(
            total_net_income=Decimal("10000.00"),
        )

        self.assertEqual(
            position["total_net_income"],
            Decimal("10000.00"),
        )

        self.assertEqual(
            position["personal_allowance"],
            Decimal("12570.00"),
        )

        self.assertEqual(
            position["taxable_income"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["estimated_tax_and_class_4"],
            Decimal("0.00"),
        )

    def test_income_of_twenty_thousand(self):
        position = calculate_tax_position(
            total_net_income=Decimal("20000.00"),
        )

        self.assertEqual(
            position["total_net_income"],
            Decimal("20000.00"),
        )

        self.assertEqual(
            position["personal_allowance"],
            PERSONAL_ALLOWANCE,
        )

        self.assertEqual(
            position["taxable_income"],
            Decimal("7430.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("1486.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("445.80"),
        )

        self.assertEqual(
            position["estimated_tax_and_class_4"],
            Decimal("1931.80"),
        )

    def test_income_at_basic_rate_limit(self):
        position = calculate_tax_position(
         
            total_net_income=INCOME_TAX_BASIC_RATE_LIMIT,
        )

        self.assertEqual(
            position["total_net_income"],
            Decimal("50270.00"),
        )

        self.assertEqual(
            position["taxable_income"],
            Decimal("37700.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("7540.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("2262.00"),
        )

        self.assertEqual(
            position["estimated_tax_and_class_4"],
            Decimal("9802.00"),
        )

    def test_negative_income_is_normalised(self):
        position = calculate_tax_position(
            total_net_income=Decimal("-500.00"),
        )

        self.assertEqual(
            position["total_net_income"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["taxable_income"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("0.00"),
        )

        self.assertEqual(
            position["estimated_tax_and_class_4"],
            Decimal("0.00"),
        )

    def test_income_above_basic_rate_limit_is_not_supported(self):
        with self.assertRaises(NotImplementedError):
            calculate_tax_position(
                total_net_income=Decimal("50271.00"),
            )


# ============================================================================
# TAX YEAR LABEL
# ============================================================================

class TaxYearLabelTests(SimpleTestCase):

    def test_tax_year_label(self):
        period = AccountingPeriod(
            start_date=date(2026, 4, 6),
            end_date=date(2027, 4, 5),
            name="2026/27",
        )

        self.assertEqual(
            get_tax_year_label(period),
            "2026/27",
        )


# ============================================================================
# TAX YEAR / LEDGER INTEGRATION
# ============================================================================

class TaxYearCalculationTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.bank = Account.objects.create(
            code="1000",
            name="Bank",
            type="ASSET",
        )

        cls.sales = Account.objects.create(
            code="4000",
            name="Sales",
            type="REVENUE",
        )

        cls.expenses = Account.objects.create(
            code="5300",
            name="General Expenses",
            type="EXPENSE",
        )

    def create_income(
        self,
        *,
        transaction_date,
        amount,
        description="Business income",
    ):
        return create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            items=[
                {
                    "account": self.bank,
                    "debit": Decimal(amount),
                },
                {
                    "account": self.sales,
                    "credit": Decimal(amount),
                },
            ],
        )

    def create_expense(
        self,
        *,
        transaction_date,
        amount,
        description="Business expense",
    ):
        return create_journal_entry(
            transaction_date=transaction_date,
            description=description,
            items=[
                {
                    "account": self.expenses,
                    "debit": Decimal(amount),
                },
                {
                    "account": self.bank,
                    "credit": Decimal(amount),
                },
            ],
        )

    def test_tax_year_uses_6_april_to_5_april(self):
        position = calculate_tax_position_for_tax_year(
            for_date=date(2026, 9, 1),
        )

        period = position["period"]

        self.assertEqual(
            period.start_date,
            date(2026, 4, 6),
        )

        self.assertEqual(
            period.end_date,
            date(2027, 4, 5),
        )

        self.assertEqual(
            position["date_from"],
            date(2026, 4, 6),
        )

        self.assertEqual(
            position["date_to"],
            date(2027, 4, 5),
        )

    def test_tax_year_calculation_uses_business_profit(self):
        self.create_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("20000.00"),
        )

        self.create_expense(
            transaction_date=date(2026, 9, 2),
            amount=Decimal("5000.00"),
        )

        position = calculate_tax_position_for_tax_year(
            for_date=date(2026, 9, 15),
        )

        self.assertEqual(
            position["total_revenue"],
            Decimal("20000.00"),
        )

        self.assertEqual(
            position["total_expenses"],
            Decimal("5000.00"),
        )

        self.assertEqual(
            position["net_profit"],
            Decimal("15000.00"),
        )

        self.assertEqual(
            position["taxable_income"],
            Decimal("2430.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("486.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("145.80"),
        )

        self.assertEqual(
            position["estimated_tax_and_class_4"],
            Decimal("631.80"),
        )

    def test_previous_tax_year_is_excluded(self):
        self.create_income(
            transaction_date=date(2026, 4, 5),
            amount=Decimal("10000.00"),
            description="Previous tax year",
        )

        self.create_income(
            transaction_date=date(2026, 4, 6),
            amount=Decimal("20000.00"),
            description="Current tax year",
        )

        position = calculate_tax_position_for_tax_year(
            for_date=date(2026, 9, 1),
        )

        self.assertEqual(
            position["net_profit"],
            Decimal("20000.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("1486.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("445.80"),
        )

    def test_5_april_is_included_in_tax_year(self):
        self.create_income(
            transaction_date=date(2027, 4, 5),
            amount=Decimal("20000.00"),
            description="Final day of tax year",
        )

        position = calculate_tax_position_for_tax_year(
            for_date=date(2027, 4, 5),
        )

        self.assertEqual(
            position["net_profit"],
            Decimal("20000.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("1486.00"),
        )

    def test_6_april_starts_new_tax_year(self):
        self.create_income(
            transaction_date=date(2027, 4, 5),
            amount=Decimal("10000.00"),
            description="2026/27",
        )

        self.create_income(
            transaction_date=date(2027, 4, 6),
            amount=Decimal("20000.00"),
            description="2027/28",
        )

        position = calculate_tax_position_for_tax_year(
            for_date=date(2027, 4, 6),
        )

        self.assertEqual(
            position["date_from"],
            date(2027, 4, 6),
        )

        self.assertEqual(
            position["date_to"],
            date(2028, 4, 5),
        )

        self.assertEqual(
            position["net_profit"],
            Decimal("20000.00"),
        )

        self.assertEqual(
            position["income_tax"],
            Decimal("1486.00"),
        )

        self.assertEqual(
            position["class_4_national_insurance"],
            Decimal("445.80"),
        )

    def test_tax_year_period_is_created(self):
        self.assertEqual(
            AccountingPeriod.objects.count(),
            0,
        )

        position = calculate_tax_position_for_tax_year(
            for_date=date(2026, 9, 1),
        )

        self.assertIsNotNone(
            position["period"],
        )

        self.assertEqual(
            AccountingPeriod.objects.count(),
            1,
        )


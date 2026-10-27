
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.services.income import record_income


class TestIncome(AccountingTestBase):

    # ------------------------------------------------------------------
    # Income
    # ------------------------------------------------------------------

    def test_record_income(self):
        entry = record_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("250.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Client income",
        )

        self.assertJournalBalanced(entry)

        debit = entry.items.get(account=self.bank)
        credit = entry.items.get(account=self.sales)

        self.assertEqual(
            debit.debit,
            Decimal("250.00"),
        )

        self.assertEqual(
            credit.credit,
            Decimal("250.00"),
        )

    def test_record_income_accepts_string_amount(self):
        entry = record_income(
            transaction_date=date(2026, 9, 1),
            amount="250.00",
            income_account=self.sales,
            payment_account=self.bank,
            description="String amount",
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.total_debits,
            Decimal("250.00"),
        )

    def test_record_income_accepts_float_amount(self):
        entry = record_income(
            transaction_date=date(2026, 9, 1),
            amount=250.10,
            income_account=self.sales,
            payment_account=self.bank,
            description="Float amount",
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.total_debits,
            Decimal("250.10"),
        )

    def test_record_income_rejects_zero(self):
        with self.assertRaises(ValidationError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("0.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="Zero income",
            )

    def test_record_income_rejects_negative(self):
        with self.assertRaises(ValidationError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("-10.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="Negative income",
            )

    def test_record_income_rejects_non_revenue_account(self):
        with self.assertRaises(ValidationError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.general_expenses,
                payment_account=self.bank,
                description="Invalid income account",
            )

    def test_record_income_rejects_non_payment_account(self):
        with self.assertRaises(ValidationError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.sales,
                payment_account=self.sales,
                description="Invalid payment account",
            )

    # ------------------------------------------------------------------
    # Business settings
    # ------------------------------------------------------------------

    def test_income_rejects_accrual_basis(self):
        self.settings.accounting_basis = "ACCRUAL"
        self.settings.save(
            update_fields=["accounting_basis"]
        )

        with self.assertRaises(NotImplementedError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="Accrual income",
            )

    def test_income_rejects_vat_registered_cash_basis(self):
        self.settings.vat_registered = True
        self.settings.vat_scheme = "STANDARD"
        self.settings.save(
            update_fields=[
                "vat_registered",
                "vat_scheme",
            ]
        )

        with self.assertRaises(NotImplementedError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="VAT income",
            )


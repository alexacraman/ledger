
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.services.capital import (
    record_capital,
    record_drawing,
)
from accounts.services.reports import profit_and_loss


class CapitalTests(AccountingTestBase):
    # ------------------------------------------------------------------
    # Capital
    # ------------------------------------------------------------------

    def test_record_capital(self):
        entry = record_capital(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("1000.00"),
            capital_account=self.capital,
            payment_account=self.bank,
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.items.get(account=self.bank).debit,
            Decimal("1000.00"),
        )

        self.assertEqual(
            entry.items.get(account=self.capital).credit,
            Decimal("1000.00"),
        )

    def test_capital_does_not_affect_profit(self):
        record_capital(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("1000.00"),
            capital_account=self.capital,
            payment_account=self.bank,
        )

        report = profit_and_loss(
            date(2026, 1, 1),
            date(2026, 12, 31),
        )

        self.assertEqual(
            report["total_revenue"],
            Decimal("0.00"),
        )

        self.assertEqual(
            report["total_expenses"],
            Decimal("0.00"),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("0.00"),
        )

    def test_capital_rejects_zero(self):
        with self.assertRaises(ValidationError):
            record_capital(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("0.00"),
                capital_account=self.capital,
                payment_account=self.bank,
            )

    def test_capital_rejects_non_equity_account(self):
        with self.assertRaises(ValidationError):
            record_capital(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                capital_account=self.sales,
                payment_account=self.bank,
            )

    # ------------------------------------------------------------------
    # Drawings
    # ------------------------------------------------------------------

    def test_record_drawing(self):
        entry = record_drawing(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("200.00"),
            drawings_account=self.drawings,
            payment_account=self.bank,
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.items.get(account=self.drawings).debit,
            Decimal("200.00"),
        )

        self.assertEqual(
            entry.items.get(account=self.bank).credit,
            Decimal("200.00"),
        )

    def test_drawing_does_not_affect_profit(self):
        record_drawing(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("200.00"),
            drawings_account=self.drawings,
            payment_account=self.bank,
        )

        report = profit_and_loss(
            date(2026, 1, 1),
            date(2026, 12, 31),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("0.00"),
        )

    def test_drawing_rejects_zero(self):
        with self.assertRaises(ValidationError):
            record_drawing(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("0.00"),
                drawings_account=self.drawings,
                payment_account=self.bank,
            )

    def test_drawing_rejects_non_equity_account(self):
        with self.assertRaises(ValidationError):
            record_drawing(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                drawings_account=self.sales,
                payment_account=self.bank,
            )


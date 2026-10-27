
from datetime import date
from decimal import Decimal

from .test_setup import AccountingTestBase

from accounts.services.capital import record_capital
from accounts.services.income import record_income
from accounts.services.reports import (
    balance_sheet,
    profit_and_loss,
    trial_balance,
)
from accounts.services.transfers import record_transfer


class TestReports(AccountingTestBase):

    # ------------------------------------------------------------------
    # Profit and loss
    # ------------------------------------------------------------------

    def test_income_appears_in_profit_and_loss(self):
        record_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("250.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Sales",
        )

        report = profit_and_loss(
            date(2026, 1, 1),
            date(2026, 12, 31),
        )

        self.assertEqual(
            report["total_revenue"],
            Decimal("250.00"),
        )

        self.assertEqual(
            report["total_expenses"],
            Decimal("0.00"),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("250.00"),
        )

    def test_profit_and_loss_respects_date_range(self):
        record_income(
            transaction_date=date(2026, 4, 5),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Previous tax year",
        )

        record_income(
            transaction_date=date(2026, 4, 6),
            amount=Decimal("200.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="New tax year",
        )

        previous_year = profit_and_loss(
            date(2025, 4, 6),
            date(2026, 4, 5),
        )

        new_year = profit_and_loss(
            date(2026, 4, 6),
            date(2027, 4, 5),
        )

        self.assertEqual(
            previous_year["total_revenue"],
            Decimal("100.00"),
        )

        self.assertEqual(
            new_year["total_revenue"],
            Decimal("200.00"),
        )

    def test_profit_and_loss_does_not_include_transactions_outside_range(self):
        record_income(
            transaction_date=date(2026, 3, 31),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="March income",
        )

        record_income(
            transaction_date=date(2026, 4, 10),
            amount=Decimal("200.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="April income",
        )

        report = profit_and_loss(
            date(2026, 4, 1),
            date(2026, 4, 9),
        )

        self.assertEqual(
            report["total_revenue"],
            Decimal("0.00"),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("0.00"),
        )

    # ------------------------------------------------------------------
    # Trial balance
    # ------------------------------------------------------------------

    def test_income_appears_in_trial_balance(self):
        record_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("250.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Sales",
        )

        report = trial_balance(
            as_at=date(2026, 12, 31),
        )

        bank_row = next(
            row
            for row in report
            if row["account"] == self.bank
        )

        sales_row = next(
            row
            for row in report
            if row["account"] == self.sales
        )

        self.assertEqual(
            bank_row["debit"],
            Decimal("250.00"),
        )

        self.assertEqual(
            sales_row["credit"],
            Decimal("250.00"),
        )

    def test_trial_balance_respects_as_at_date(self):
        record_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Early income",
        )

        record_income(
            transaction_date=date(2026, 9, 10),
            amount=Decimal("200.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Later income",
        )

        report = trial_balance(
            as_at=date(2026, 9, 5),
        )

        sales_row = next(
            row
            for row in report
            if row["account"].pk == self.sales.pk
        )

        bank_row = next(
            row
            for row in report
            if row["account"].pk == self.bank.pk
        )

        self.assertEqual(
            sales_row["credit"],
            Decimal("100.00"),
        )

        self.assertEqual(
            bank_row["debit"],
            Decimal("100.00"),
        )

    # ------------------------------------------------------------------
    # Balance sheet
    # ------------------------------------------------------------------

    def test_capital_appears_in_balance_sheet(self):
        record_capital(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("1000.00"),
            capital_account=self.capital,
            payment_account=self.bank,
        )

        report = balance_sheet(
            as_at=date(2026, 12, 31),
        )

        self.assertEqual(
            report["total_assets"],
            Decimal("1000.00"),
        )

        self.assertEqual(
            report["total_liabilities"],
            Decimal("0.00"),
        )

        self.assertEqual(
            report["total_equity"],
            Decimal("1000.00"),
        )

        self.assertEqual(
            report["total_liabilities_and_equity"],
            Decimal("1000.00"),
        )

    def test_balance_sheet_respects_as_at_date(self):
        record_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Early income",
        )

        record_income(
            transaction_date=date(2026, 9, 10),
            amount=Decimal("200.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Later income",
        )

        report = balance_sheet(
            as_at=date(2026, 9, 5),
        )

        self.assertEqual(
            report["total_assets"],
            Decimal("100.00"),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("100.00"),
        )

    # ------------------------------------------------------------------
    # Transfers
    # ------------------------------------------------------------------

    def test_transfer_does_not_change_total_assets(self):
        record_capital(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("1000.00"),
            capital_account=self.capital,
            payment_account=self.bank,
        )

        record_transfer(
            transaction_date=date(2026, 9, 2),
            amount=Decimal("300.00"),
            from_account=self.bank,
            to_account=self.cash,
        )

        report = balance_sheet(
            as_at=date(2026, 12, 31),
        )

        self.assertEqual(
            report["total_assets"],
            Decimal("1000.00"),
        )

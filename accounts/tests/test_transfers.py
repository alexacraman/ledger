from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from accounts.services.reports import profit_and_loss
from accounts.services.transfers import record_transfer

from .test_setup import AccountingTestBase

class TestTransfers(AccountingTestBase):
# ------------------------------------------------------------------
# Transfers
# ------------------------------------------------------------------

    def test_bank_to_cash_transfer(self):
        entry = record_transfer(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("300.00"),
            from_account=self.bank,
            to_account=self.cash,
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.items.get(account=self.cash).debit,
            Decimal("300.00"),
        )

        self.assertEqual(
            entry.items.get(account=self.bank).credit,
            Decimal("300.00"),
        )

    def test_cash_to_bank_transfer(self):
        entry = record_transfer(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("150.00"),
            from_account=self.cash,
            to_account=self.bank,
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.items.get(account=self.bank).debit,
            Decimal("150.00"),
        )

        self.assertEqual(
            entry.items.get(account=self.cash).credit,
            Decimal("150.00"),
        )

    def test_transfer_does_not_affect_profit(self):
        record_transfer(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("300.00"),
            from_account=self.bank,
            to_account=self.cash,
        )

        report = profit_and_loss(
            date(2026, 1, 1),
            date(2026, 12, 31),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("0.00"),
        )

    def test_transfer_rejects_zero(self):
        with self.assertRaises(ValidationError):
            record_transfer(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("0.00"),
                from_account=self.bank,
                to_account=self.cash,
            )

    def test_transfer_rejects_same_account(self):
        with self.assertRaises(ValidationError):
            record_transfer(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                from_account=self.bank,
                to_account=self.bank,
            )

    def test_transfer_rejects_non_payment_source(self):
        with self.assertRaises(ValidationError):
            record_transfer(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                from_account=self.sales,
                to_account=self.bank,
            )


from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.models import (
    AccountingPeriod,
    JournalEntry,
)
from accounts.services.journal import create_journal_entry


class TestJournal(AccountingTestBase):

    # ------------------------------------------------------------------
    # Journal
    # ------------------------------------------------------------------

    def test_create_journal_entry(self):
        entry = create_journal_entry(
            transaction_date=date(2026, 9, 1),
            description="Test journal",
            items=[
                {
                    "account": self.bank,
                    "debit": Decimal("100.00"),
                },
                {
                    "account": self.sales,
                    "credit": Decimal("100.00"),
                },
            ],
        )

        self.assertJournalBalanced(entry)

        self.assertEqual(
            entry.items.count(),
            2,
        )

    def test_journal_entry_creates_accounting_period(self):
        self.assertEqual(
            AccountingPeriod.objects.count(),
            0,
        )

        entry = create_journal_entry(
            transaction_date=date(2026, 9, 1),
            description="Test period creation",
            items=[
                {
                    "account": self.bank,
                    "debit": Decimal("100.00"),
                },
                {
                    "account": self.sales,
                    "credit": Decimal("100.00"),
                },
            ],
        )

        self.assertIsNotNone(entry.period)

        self.assertEqual(
            AccountingPeriod.objects.count(),
            1,
        )

        period = entry.period

        self.assertEqual(
            period.start_date,
            date(2026, 4, 6),
        )

        self.assertEqual(
            period.end_date,
            date(2027, 4, 5),
        )

    def test_journal_rejects_unbalanced_entry(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=date(2026, 9, 1),
                description="Unbalanced journal",
                items=[
                    {
                        "account": self.bank,
                        "debit": Decimal("100.00"),
                    },
                    {
                        "account": self.sales,
                        "credit": Decimal("90.00"),
                    },
                ],
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_journal_rejects_empty_entry(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=date(2026, 9, 1),
                description="Empty journal",
                items=[],
            )

    def test_journal_rejects_negative_debit(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=date(2026, 9, 1),
                description="Negative debit",
                items=[
                    {
                        "account": self.bank,
                        "debit": Decimal("-10.00"),
                    },
                    {
                        "account": self.sales,
                        "credit": Decimal("-10.00"),
                    },
                ],
            )

    def test_journal_rejects_line_with_both_debit_and_credit(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=date(2026, 9, 1),
                description="Invalid line",
                items=[
                    {
                        "account": self.bank,
                        "debit": Decimal("100.00"),
                        "credit": Decimal("100.00"),
                    },
                ],
            )

    def test_journal_rejects_zero_line(self):
        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=date(2026, 9, 1),
                description="Zero line",
                items=[
                    {
                        "account": self.bank,
                        "debit": Decimal("0.00"),
                    },
                    {
                        "account": self.sales,
                        "credit": Decimal("0.00"),
                    },
                ],
            )

    def test_inactive_account_cannot_be_used(self):
        self.bank.is_active = False
        self.bank.save()

        with self.assertRaises(ValidationError):
            create_journal_entry(
                transaction_date=date(2026, 9, 1),
                description="Inactive account",
                items=[
                    {
                        "account": self.bank,
                        "debit": Decimal("100.00"),
                    },
                    {
                        "account": self.sales,
                        "credit": Decimal("100.00"),
                    },
                ],
            )

    def test_posted_journal_entry_cannot_be_deleted(self):
        entry = create_journal_entry(
            transaction_date=date(2026, 9, 1),
            description="Posted entry",
            items=[
                {
                    "account": self.bank,
                    "debit": Decimal("100.00"),
                },
                {
                    "account": self.sales,
                    "credit": Decimal("100.00"),
                },
            ],
        )

        with self.assertRaises(ValidationError):
            entry.delete()

        self.assertTrue(
            JournalEntry.objects.filter(
                pk=entry.pk
            ).exists()
        )

    def test_posted_journal_item_cannot_be_changed(self):
        entry = create_journal_entry(
            transaction_date=date(2026, 9, 1),
            description="Posted entry",
            items=[
                {
                    "account": self.bank,
                    "debit": Decimal("100.00"),
                },
                {
                    "account": self.sales,
                    "credit": Decimal("100.00"),
                },
            ],
        )

        item = entry.items.first()
        item.debit = Decimal("200.00")

        with self.assertRaises(ValidationError):
            item.save()

    def test_posted_journal_item_cannot_be_deleted(self):
        entry = create_journal_entry(
            transaction_date=date(2026, 9, 1),
            description="Posted entry",
            items=[
                {
                    "account": self.bank,
                    "debit": Decimal("100.00"),
                },
                {
                    "account": self.sales,
                    "credit": Decimal("100.00"),
                },
            ],
        )

        item = entry.items.first()

        with self.assertRaises(ValidationError):
            item.delete()



from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.models import (
    AccountingPeriod,
    JournalEntry,
)
from accounts.services.income import record_income
from accounts.services.period_management import close_accounting_period
from accounts.services.periods import get_or_create_period_for_date


class PeriodTests(AccountingTestBase):

    # ------------------------------------------------------------------
    # Accounting period creation
    # ------------------------------------------------------------------

    def test_get_or_create_period_returns_existing_period(self):
        first = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        second = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        self.assertEqual(
            first.pk,
            second.pk,
        )

        self.assertEqual(
            AccountingPeriod.objects.count(),
            1,
        )

    def test_accounting_period_dates(self):
        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        self.assertEqual(
            period.start_date,
            date(2026, 4, 6),
        )

        self.assertEqual(
            period.end_date,
            date(2027, 4, 5),
        )

    def test_april_5_belongs_to_previous_tax_year(self):
        period = get_or_create_period_for_date(
            date(2026, 4, 5)
        )

        self.assertEqual(
            period.start_date,
            date(2025, 4, 6),
        )

        self.assertEqual(
            period.end_date,
            date(2026, 4, 5),
        )

    def test_april_6_begins_new_tax_year(self):
        period = get_or_create_period_for_date(
            date(2026, 4, 6)
        )

        self.assertEqual(
            period.start_date,
            date(2026, 4, 6),
        )

        self.assertEqual(
            period.end_date,
            date(2027, 4, 5),
        )

    def test_april_5_and_april_6_are_different_periods(self):
        previous_year = get_or_create_period_for_date(
            date(2026, 4, 5)
        )

        new_year = get_or_create_period_for_date(
            date(2026, 4, 6)
        )

        self.assertNotEqual(
            previous_year.pk,
            new_year.pk,
        )

        self.assertEqual(
            AccountingPeriod.objects.count(),
            2,
        )

    def test_period_boundary_dates_can_belong_to_different_periods(self):
        previous_period = get_or_create_period_for_date(
            date(2026, 4, 5)
        )

        next_period = get_or_create_period_for_date(
            date(2026, 4, 6)
        )

        self.assertEqual(
            previous_period.end_date,
            date(2026, 4, 5),
        )

        self.assertEqual(
            next_period.start_date,
            date(2026, 4, 6),
        )

        self.assertNotEqual(
            previous_period.pk,
            next_period.pk,
        )

    # ------------------------------------------------------------------
    # Closed periods
    # ------------------------------------------------------------------

    def test_closed_period_rejects_new_posting(self):
        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        period.is_closed = True
        period.save(
            update_fields=["is_closed"]
        )

        with self.assertRaisesMessage(
            ValidationError,
            f"Accounting period {period.name} is closed.",
        ):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="Should fail",
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_closed_period_does_not_block_new_period(self):
        old_period = get_or_create_period_for_date(
            date(2026, 4, 5)
        )

        old_period.is_closed = True
        old_period.save(
            update_fields=["is_closed"]
        )

        record_income(
            transaction_date=date(2026, 4, 6),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="New tax year income",
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            1,
        )

        entry = JournalEntry.objects.first()

        self.assertEqual(
            entry.period_id,
            get_or_create_period_for_date(
                date(2026, 4, 6)
            ).pk,
        )

    def test_closed_period_remains_unchanged_after_failed_posting(self):
        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        period.is_closed = True
        period.save(
            update_fields=["is_closed"]
        )

        with self.assertRaises(ValidationError):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="Should fail",
            )

        period.refresh_from_db()

        self.assertTrue(
            period.is_closed
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    # ------------------------------------------------------------------
    # Period management
    # ------------------------------------------------------------------

    def test_open_period_can_be_closed(self):
        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        self.assertFalse(
            period.is_closed
        )

        result = close_accounting_period(
            period
        )

        result.refresh_from_db()

        self.assertTrue(
            result.is_closed
        )

    def test_closed_period_cannot_be_closed_again(self):
        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        close_accounting_period(
            period
        )

        with self.assertRaisesMessage(
            ValidationError,
            f"Accounting period {period.name} is already closed.",
        ):
            close_accounting_period(
                period
            )

    def test_closed_period_prevents_new_journal_posting(self):
        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        close_accounting_period(
            period
        )

        with self.assertRaisesMessage(
            ValidationError,
            f"Accounting period {period.name} is closed.",
        ):
            record_income(
                transaction_date=date(2026, 9, 1),
                amount=Decimal("100.00"),
                income_account=self.sales,
                payment_account=self.bank,
                description="Should not post",
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_closing_period_does_not_affect_next_period(self):
        previous_period = get_or_create_period_for_date(
            date(2026, 4, 5)
        )

        next_period = get_or_create_period_for_date(
            date(2026, 4, 6)
        )

        close_accounting_period(
            previous_period
        )

        record_income(
            transaction_date=date(2026, 4, 6),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="New tax year income",
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            1,
        )

        entry = JournalEntry.objects.first()

        self.assertEqual(
            entry.period_id,
            next_period.pk,
        )

    def test_closing_period_does_not_change_existing_entries(self):
        record_income(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("100.00"),
            income_account=self.sales,
            payment_account=self.bank,
            description="Existing income",
        )

        period = get_or_create_period_for_date(
            date(2026, 9, 1)
        )

        entry = JournalEntry.objects.first()

        self.assertTrue(
            entry.is_posted
        )

        close_accounting_period(
            period
        )

        entry.refresh_from_db()

        self.assertTrue(
            entry.is_posted
        )

        self.assertEqual(
            entry.period_id,
            period.pk,
        )

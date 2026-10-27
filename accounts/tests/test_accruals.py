from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase
from accounts.models import Account, JournalEntry
from accounts.services.accruals import (
    create_year_end_adjustment,
    record_accrued_expense,
    record_accrued_income,
    record_bad_debt_write_off,
    record_doubtful_debt_allowance,
    record_prepayment,
    recognise_prepayment,
)


class TestAccrualAdjustments(AccountingTestBase):

    def test_record_accrued_expense_posts_to_accrued_liability(self):
        entry = record_accrued_expense(
            transaction_date=date(2026, 9, 30),
            amount=Decimal("100.00"),
            expense_account=self.general_expenses,
            accrued_expense_account=self.accrued_expenses,
            description="Accrued office rent",
        )

        self.assertJournalBalanced(entry)
        self.assertEqual(
            entry.items.get(account=self.general_expenses).debit,
            Decimal("100.00"),
        )
        self.assertEqual(
            entry.items.get(account=self.accrued_expenses).credit,
            Decimal("100.00"),
        )

    def test_record_accrued_income_posts_to_accrued_asset(self):
        entry = record_accrued_income(
            transaction_date=date(2026, 9, 30),
            amount=Decimal("200.00"),
            revenue_account=self.sales,
            accrued_income_account=self.accrued_income,
            description="Accrued commission",
        )

        self.assertJournalBalanced(entry)
        self.assertEqual(
            entry.items.get(account=self.accrued_income).debit,
            Decimal("200.00"),
        )
        self.assertEqual(
            entry.items.get(account=self.sales).credit,
            Decimal("200.00"),
        )

    def test_record_prepayment_posts_to_asset_and_is_reversed_on_use(self):
        initial = record_prepayment(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("300.00"),
            payment_account=self.bank,
            prepayment_account=self.prepayments,
            description="Insurance premium",
        )

        self.assertJournalBalanced(initial)
        self.assertEqual(
            initial.items.get(account=self.prepayments).debit,
            Decimal("300.00"),
        )

        reversal = recognise_prepayment(
            transaction_date=date(2026, 10, 1),
            amount=Decimal("300.00"),
            expense_account=self.general_expenses,
            prepayment_account=self.prepayments,
            description="Insurance used",
        )

        self.assertJournalBalanced(reversal)
        self.assertEqual(
            reversal.items.get(account=self.general_expenses).debit,
            Decimal("300.00"),
        )
        self.assertEqual(
            reversal.items.get(account=self.prepayments).credit,
            Decimal("300.00"),
        )

    def test_write_off_bad_debt_is_posted_to_irrecoverable_debts(self):
        entry = record_bad_debt_write_off(
            transaction_date=date(2026, 9, 30),
            amount=Decimal("75.00"),
            receivables_account=self.accounts_receivable,
            irrecoverable_debt_account=self.irrecoverable_debts,
            description="Customer default",
        )

        self.assertJournalBalanced(entry)
        self.assertEqual(
            entry.items.get(account=self.irrecoverable_debts).debit,
            Decimal("75.00"),
        )
        self.assertEqual(
            entry.items.get(account=self.accounts_receivable).credit,
            Decimal("75.00"),
        )

    def test_doubtful_debt_allowance_posts_to_contra_asset(self):
        entry = record_doubtful_debt_allowance(
            transaction_date=date(2026, 9, 30),
            amount=Decimal("50.00"),
            bad_debt_expense_account=self.irrecoverable_debts,
            allowance_account=self.allowance_for_doubtful_debts,
            description="Provision for doubtful debts",
        )

        self.assertJournalBalanced(entry)
        self.assertEqual(
            entry.items.get(account=self.irrecoverable_debts).debit,
            Decimal("50.00"),
        )
        self.assertEqual(
            entry.items.get(account=self.allowance_for_doubtful_debts).credit,
            Decimal("50.00"),
        )

    def test_year_end_adjustment_dispatches_to_accrued_expense(self):
        entry = create_year_end_adjustment(
            adjustment_type="accrued_expense",
            transaction_date=date(2026, 9, 30),
            amount=Decimal("120.00"),
            expense_account=self.general_expenses,
            accrued_expense_account=self.accrued_expenses,
            description="Accrued rent",
        )

        self.assertJournalBalanced(entry)
        self.assertEqual(
            entry.items.get(account=self.general_expenses).debit,
            Decimal("120.00"),
        )

    def test_accrual_adjustment_rejects_non_balanced_amounts(self):
        with self.assertRaises(ValidationError):
            record_accrued_expense(
                transaction_date=date(2026, 9, 30),
                amount=Decimal("-10.00"),
                expense_account=self.general_expenses,
                accrued_expense_account=self.accrued_expenses,
                description="Invalid accrual",
            )

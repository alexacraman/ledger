
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.models import (
    JournalEntry,
    JournalItem,
    Expense,
    ExpenseLineItem,
)
from accounts.services.expenses import record_expense
from accounts.services.reports import profit_and_loss


class TestExpenses(AccountingTestBase):

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def create_expense(self, amount="100.00"):
        expense = Expense.objects.create(
            expense_account=self.general_expenses,
            payment_account=self.bank,
            expense_date=date(2026, 9, 1),
            description="Test expense",
            supplier_name="Test Supplier",
            reference="EXP-123",
            status="DRAFT",
        )

        ExpenseLineItem.objects.create(
            expense=expense,
            description="Test expense item",
            quantity=Decimal("1.00"),
            unit_price=Decimal(amount),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return expense

    # ------------------------------------------------------------------
    # Basic posting
    # ------------------------------------------------------------------

    def test_cash_basis_expense_posts_to_ledger(self):
        expense = self.create_expense("100.00")

        result = record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        expense.refresh_from_db()

        self.assertEqual(result.pk, expense.pk)
        self.assertEqual(expense.status, "POSTED")
        self.assertIsNotNone(expense.journal_entry_id)

        journal = expense.journal_entry

        self.assertTrue(journal.is_posted)

        self.assertEqual(
            JournalItem.objects.filter(
                entry=journal,
                account=self.general_expenses,
                debit=Decimal("100.00"),
                credit=Decimal("0.00"),
            ).count(),
            1,
        )

        self.assertEqual(
            JournalItem.objects.filter(
                entry=journal,
                account=self.bank,
                debit=Decimal("0.00"),
                credit=Decimal("100.00"),
            ).count(),
            1,
        )

    def test_expense_requires_lines(self):
        expense = Expense.objects.create(
            expense_account=self.general_expenses,
            payment_account=self.bank,
            expense_date=date(2026, 9, 1),
            description="Empty expense",
            supplier_name="Test Supplier",
            reference="EXP-EMPTY",
            status="DRAFT",
        )

        with self.assertRaises(ValidationError):
            record_expense(
                expense=expense,
                expense_account=self.general_expenses,
                payment_account=self.bank,
                reference=expense.reference,
            )

        self.assertIsNone(expense.journal_entry_id)

    def test_zero_expense_is_rejected(self):
        expense = self.create_expense("0.00")

        with self.assertRaises(ValidationError):
            record_expense(
                expense=expense,
                expense_account=self.general_expenses,
                payment_account=self.bank,
                reference=expense.reference,
            )

        expense.refresh_from_db()

        self.assertEqual(
            expense.status,
            "DRAFT",
        )

        self.assertIsNone(
            expense.journal_entry_id,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_expense_cannot_be_posted_twice(self):
        expense = self.create_expense("100.00")

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        with self.assertRaises(ValidationError):
            record_expense(
                expense=expense,
                expense_account=self.general_expenses,
                payment_account=self.bank,
                reference=expense.reference,
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            1,
        )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def test_negative_expense_line_is_rejected(self):
        expense = Expense.objects.create(
            expense_account=self.general_expenses,
            payment_account=self.bank,
            expense_date=date(2026, 9, 1),
            description="Invalid expense",
            supplier_name="Test Supplier",
            reference="EXP-NEG",
            status="DRAFT",
        )

        with self.assertRaises(ValidationError):
            ExpenseLineItem.objects.create(
                expense=expense,
                description="Negative amount",
                quantity=Decimal("1.00"),
                unit_price=Decimal("-10.00"),
                vat_rate=Decimal("0.00"),
                vat_amount=Decimal("0.00"),
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_invalid_expense_account_is_rejected(self):
        expense = self.create_expense("100.00")

        with self.assertRaises(ValidationError):
            record_expense(
                expense=expense,
                expense_account=self.sales,
                payment_account=self.bank,
                reference=expense.reference,
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_invalid_payment_account_is_rejected(self):
        expense = self.create_expense("100.00")

        with self.assertRaises(ValidationError):
            record_expense(
                expense=expense,
                expense_account=self.general_expenses,
                payment_account=self.sales,
                reference=expense.reference,
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_cash_account_can_be_used_for_expense(self):
        expense = self.create_expense("75.00")

        expense.payment_account = self.cash
        expense.save()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.cash,
            reference=expense.reference,
        )

        expense.refresh_from_db()

        self.assertEqual(
            expense.status,
            "POSTED",
        )

        self.assertEqual(
            JournalItem.objects.filter(
                entry=expense.journal_entry,
                account=self.cash,
                debit=Decimal("0.00"),
                credit=Decimal("75.00"),
            ).count(),
            1,
        )

    # ------------------------------------------------------------------
    # Journal details
    # ------------------------------------------------------------------

    def test_expense_reference_is_stored_on_journal(self):
        expense = self.create_expense("120.00")

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference="BANK-EXP-001",
        )

        expense.refresh_from_db()

        self.assertEqual(
            expense.journal_entry.reference,
            "BANK-EXP-001",
        )

    def test_expense_journal_uses_expense_date_and_description(self):
        expense = self.create_expense("120.00")

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        journal = expense.journal_entry

        self.assertEqual(
            journal.transaction_date,
            date(2026, 9, 1),
        )

        self.assertEqual(
            journal.description,
            "Test expense",
        )

    # ------------------------------------------------------------------
    # Accounting effects
    # ------------------------------------------------------------------

    def test_expense_appears_in_profit_and_loss(self):
        expense = self.create_expense("100.00")

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        pnl = profit_and_loss(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 30),
        )

        expense_row = next(
            row
            for row in pnl["expenses"]
            if row["account"] == self.general_expenses
        )

        self.assertEqual(
            expense_row["amount"],
            Decimal("100.00"),
        )

        self.assertEqual(
            pnl["total_expenses"],
            Decimal("100.00"),
        )

        self.assertEqual(
            pnl["net_profit"],
            Decimal("-100.00"),
        )

    def test_expense_reduces_bank_balance(self):
        expense = self.create_expense("100.00")

        initial_balance = self.get_account_balance(
            self.bank
        )

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        final_balance = self.get_account_balance(
            self.bank
        )

        self.assertEqual(
            final_balance,
            initial_balance - Decimal("100.00"),
        )

    def test_expense_increases_expense_account_balance(self):
        expense = self.create_expense("100.00")

        initial_balance = self.get_account_balance(
            self.general_expenses
        )

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        final_balance = self.get_account_balance(
            self.general_expenses
        )

        self.assertEqual(
            final_balance,
            initial_balance + Decimal("100.00"),
        )

    # ------------------------------------------------------------------
    # VAT and accounting basis
    # ------------------------------------------------------------------

    def test_vat_expense_is_rejected_for_non_vat_registered_business(self):
        expense = self.create_expense("100.00")

        line = expense.lines.first()
        line.vat_amount = Decimal("20.00")
        line.save(update_fields=["vat_amount"])

        with self.assertRaises(ValidationError):
            record_expense(
                expense=expense,
                expense_account=self.general_expenses,
                payment_account=self.bank,
                reference=expense.reference,
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_accrual_basis_expense_is_not_supported(self):
        expense = self.create_expense("100.00")

        self.settings.accounting_basis = "ACCRUAL"
        self.settings.save(
            update_fields=["accounting_basis"]
        )

        with self.assertRaises(NotImplementedError):
            record_expense(
                expense=expense,
                expense_account=self.general_expenses,
                payment_account=self.bank,
                reference=expense.reference,
            )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

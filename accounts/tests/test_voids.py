from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from accounts.models import (
Expense,
ExpenseLineItem,
Invoice,
InvoiceLineItem,
JournalEntry,
Purchase,
PurchaseLineItem,
)
from accounts.services.expenses import record_expense, void_expense
from accounts.services.purchases import post_purchase, record_purchase_payment, void_purchase
from accounts.services.reports import profit_and_loss
from accounts.services.sales import (
mark_invoice_sent,
post_invoice,
record_invoice_payment,
void_invoice,
)

from contacts.models import Customer, Supplier

from .test_setup import AccountingTestBase

class ExpenseVoidTests(AccountingTestBase):


    def make_expense(self):
        expense = Expense.objects.create(
            expense_date=date(2026, 9, 10),
            description="Test expense",
            supplier_name="Test Supplier",
            reference="EXP-VOID-001",
            status="DRAFT",
            expense_account=self.general_expenses,
            payment_account=self.bank,
        )

        ExpenseLineItem.objects.create(
            expense=expense,
            description="Office supplies",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return expense

    def test_posted_expense_can_be_voided(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        expense.refresh_from_db()

        self.assertEqual(expense.status, "POSTED")
        self.assertIsNotNone(expense.journal_entry_id)

        original_entry = expense.journal_entry

        self.assertTrue(original_entry.is_posted)

        expense, reversal_entry = void_expense(
            expense=expense
        )

        expense.refresh_from_db()

        self.assertEqual(expense.status, "VOID")
        self.assertEqual(
            expense.journal_entry_id,
            original_entry.pk,
        )

        self.assertNotEqual(
            reversal_entry.pk,
            original_entry.pk,
        )

    def test_void_creates_reversing_journal(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        original_entry = expense.journal_entry

        _, reversal_entry = void_expense(
            expense=expense
        )

        original_items = list(
            original_entry.items.order_by("id")
        )

        reversal_items = list(
            reversal_entry.items.order_by("id")
        )

        self.assertEqual(
            len(original_items),
            len(reversal_items),
        )

        for original, reversal in zip(
            original_items,
            reversal_items,
        ):
            self.assertEqual(
                reversal.account_id,
                original.account_id,
            )

            self.assertEqual(
                reversal.debit,
                original.credit,
            )

            self.assertEqual(
                reversal.credit,
                original.debit,
            )

    def test_original_expense_journal_is_untouched(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        original_entry = expense.journal_entry

        original_items = list(
            original_entry.items.order_by("id").values(
                "account_id",
                "debit",
                "credit",
            )
        )

        void_expense(expense=expense)

        original_entry.refresh_from_db()

        self.assertTrue(original_entry.is_posted)

        self.assertEqual(
            list(
                original_entry.items.order_by("id").values(
                    "account_id",
                    "debit",
                    "credit",
                )
            ),
            original_items,
        )

    def test_reversal_journal_is_balanced(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        _, reversal_entry = void_expense(
            expense=expense
        )

        self.assertTrue(reversal_entry.is_posted)

        self.assertJournalBalanced(reversal_entry)

    def test_voided_expense_cannot_be_voided_again(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        void_expense(expense=expense)

        expense.refresh_from_db()

        self.assertEqual(
            expense.status,
            "VOID",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted expenses can be voided.",
        ):
            void_expense(expense=expense)

    def test_draft_expense_cannot_be_voided(self):
        expense = self.make_expense()

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted expenses can be voided.",
        ):
            void_expense(expense=expense)

        expense.refresh_from_db()

        self.assertEqual(
            expense.status,
            "DRAFT",
        )

    def test_void_reverses_expense_and_bank_balances(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        self.assertEqual(
            self.get_account_balance(self.general_expenses),
            Decimal("100.00"),
        )

        self.assertEqual(
            self.get_account_balance(self.bank),
            Decimal("-100.00"),
        )

        void_expense(expense=expense)

        self.assertEqual(
            self.get_account_balance(self.general_expenses),
            Decimal("0.00"),
        )

        self.assertEqual(
            self.get_account_balance(self.bank),
            Decimal("0.00"),
        )

    def test_voided_expense_does_not_remove_original_journal(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        original_entry_id = expense.journal_entry_id
        journal_count_before_void = JournalEntry.objects.count()

        void_expense(expense=expense)

        self.assertEqual(
            JournalEntry.objects.count(),
            journal_count_before_void + 1,
        )

        self.assertTrue(
            JournalEntry.objects.filter(
                pk=original_entry_id,
                is_posted=True,
            ).exists()
        )

    def test_voided_expense_reverses_profit_and_loss(self):
        expense = self.make_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        pnl_before = profit_and_loss(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 30),
        )

        self.assertEqual(
            pnl_before["total_expenses"],
            Decimal("100.00"),
        )

        void_expense(expense=expense)

        pnl_after = profit_and_loss(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 30),
        )

        self.assertEqual(
            pnl_after["total_expenses"],
            Decimal("0.00"),
        )

        self.assertEqual(
            pnl_after["net_profit"],
            Decimal("0.00"),
        )


class PurchaseVoidTests(AccountingTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.supplier = Supplier.objects.create(
            name="Void Test Supplier",
            email="supplier@example.com",
        )

    def make_purchase(self):
        purchase = Purchase.objects.create(
            purchase_number=f"VOID-PUR-{Purchase.objects.count() + 1}",
            supplier=self.supplier,
            supplier_name=self.supplier.name,
            supplier_email=self.supplier.email,
            purchase_date=date(2026, 9, 10),
            due_date=date(2026, 9, 24),
            status="DRAFT",
        )

        PurchaseLineItem.objects.create(
            purchase=purchase,
            description="Test purchase",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return purchase

    def test_unpaid_posted_purchase_can_be_voided(self):
        purchase = self.make_purchase()

        post_purchase(purchase)

        purchase.refresh_from_db()

        self.assertEqual(purchase.status, "POSTED")
        self.assertIsNone(purchase.journal_entry_id)
        self.assertEqual(purchase.payments.count(), 0)

        void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertEqual(purchase.status, "VOID")
        self.assertIsNone(purchase.journal_entry_id)
        self.assertEqual(purchase.payments.count(), 0)

    def test_draft_purchase_cannot_be_voided(self):
        purchase = self.make_purchase()

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted purchases can be voided.",
        ):
            void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "DRAFT",
        )

    def test_partially_paid_purchase_cannot_be_voided(self):
        purchase = self.make_purchase()

        post_purchase(purchase)

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("40.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
        )

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PARTIAL",
        )

        self.assertEqual(
            purchase.payments.count(),
            1,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted purchases can be voided.",
        ):
            void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PARTIAL",
        )

        self.assertEqual(
            purchase.payments.count(),
            1,
        )

    def test_paid_purchase_cannot_be_voided(self):
        purchase = self.make_purchase()

        post_purchase(purchase)

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("100.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
        )

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PAID",
        )

        self.assertEqual(
            purchase.payments.count(),
            1,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted purchases can be voided.",
        ):
            void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PAID",
        )

        self.assertEqual(
            purchase.payments.count(),
            1,
        )

    def test_voided_purchase_cannot_be_voided_again(self):
        purchase = self.make_purchase()

        post_purchase(purchase)
        void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "VOID",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted purchases can be voided.",
        ):
            void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "VOID",
        )

    def test_voiding_cash_purchase_does_not_create_ledger_entry(self):
        purchase = self.make_purchase()

        post_purchase(purchase)

        self.assertIsNone(
            Purchase.objects.get(
                pk=purchase.pk
            ).journal_entry_id
        )

        void_purchase(purchase=purchase)

        purchase.refresh_from_db()

        self.assertIsNone(
            purchase.journal_entry_id
        )

        self.assertEqual(
            purchase.payments.count(),
            0,
        )

        self.assertEqual(
            self.purchases.journal_items.count(),
            0,
        )


class InvoiceVoidTests(AccountingTestBase):


    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.customer = Customer.objects.create(
            name="Void Test Customer",
            email="void@example.com",
        )

    def make_invoice(self):
        invoice = Invoice.objects.create(
            invoice_number=f"VOID-INV-{Invoice.objects.count() + 1}",
            customer=self.customer,
            client_name=self.customer.name,
            client_email=self.customer.email,
            issue_date=date(2026, 9, 10),
            due_date=date(2026, 9, 24),
            status="DRAFT",
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Test sale",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return invoice

    def test_unpaid_posted_invoice_can_be_voided(self):
        invoice = self.make_invoice()

        post_invoice(invoice)

        invoice.refresh_from_db()

        self.assertEqual(invoice.status, "POSTED")
        self.assertIsNone(invoice.journal_entry_id)
        self.assertEqual(invoice.payments.count(), 0)

        void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(invoice.status, "VOID")
        self.assertIsNone(invoice.journal_entry_id)
        self.assertEqual(invoice.payments.count(), 0)

    def test_unpaid_sent_invoice_can_be_voided(self):
        invoice = self.make_invoice()

        post_invoice(invoice)
        mark_invoice_sent(invoice)

        invoice.refresh_from_db()

        self.assertEqual(invoice.status, "SENT")
        self.assertIsNone(invoice.journal_entry_id)
        self.assertEqual(invoice.payments.count(), 0)

        void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(invoice.status, "VOID")
        self.assertIsNone(invoice.journal_entry_id)
        self.assertEqual(invoice.payments.count(), 0)

    def test_draft_invoice_cannot_be_voided(self):
        invoice = self.make_invoice()

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted or sent invoices can be voided.",
        ):
            void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "DRAFT",
        )

    def test_partially_paid_invoice_cannot_be_voided(self):
        invoice = self.make_invoice()

        post_invoice(invoice)

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("40.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 10),
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PARTIAL",
        )

        self.assertEqual(
            invoice.payments.count(),
            1,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted or sent invoices can be voided.",
        ):
            void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PARTIAL",
        )

        self.assertEqual(
            invoice.payments.count(),
            1,
        )

    def test_paid_invoice_cannot_be_voided(self):
        invoice = self.make_invoice()

        post_invoice(invoice)

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("100.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 10),
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PAID",
        )

        self.assertEqual(
            invoice.payments.count(),
            1,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted or sent invoices can be voided.",
        ):
            void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PAID",
        )

        self.assertEqual(
            invoice.payments.count(),
            1,
        )

    def test_voided_invoice_cannot_be_voided_again(self):
        invoice = self.make_invoice()

        post_invoice(invoice)
        void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "VOID",
        )

        with self.assertRaisesMessage(
            ValidationError,
            "Only posted or sent invoices can be voided.",
        ):
            void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "VOID",
        )

    def test_voiding_cash_invoice_does_not_create_ledger_entry(self):
        invoice = self.make_invoice()

        post_invoice(invoice)

        self.assertIsNone(
            Invoice.objects.get(
                pk=invoice.pk
            ).journal_entry_id
        )

        void_invoice(invoice=invoice)

        invoice.refresh_from_db()

        self.assertIsNone(
            invoice.journal_entry_id
        )

        self.assertEqual(
            invoice.payments.count(),
            0,
        )

        self.assertEqual(
            self.sales.journal_items.count(),
            0,
        )

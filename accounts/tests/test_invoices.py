
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.models import (
    Invoice,
    InvoiceLineItem,
    JournalEntry,
    JournalItem,
    Payment,
)
from accounts.services.sales import (
    post_invoice,
    record_invoice_payment,
)
from accounts.services.reports import (
    profit_and_loss,
    trial_balance,
)
from contacts.models import Customer


class InvoiceTests(AccountingTestBase):

    # ------------------------------------------------------------------
    # Setup and helpers
    # ------------------------------------------------------------------

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.customer = Customer.objects.create(
            name="Test Customer",
            email="customer@example.com",
            phone="01234567890",
            address="1 Test Street",
            postcode="TE1 1ST",
            is_active=True,
        )

    def create_invoice(self, amount="600.00"):
        invoice = Invoice.objects.create(
            invoice_number="INV-0001",
            customer=self.customer,
            client_name=self.customer.name,
            client_email=self.customer.email,
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
            status="DRAFT",
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Test sale",
            quantity=Decimal("1.00"),
            unit_price=Decimal(amount),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return invoice

    # ------------------------------------------------------------------
    # Invoice posting
    # ------------------------------------------------------------------

    def test_cash_basis_invoice_finalisation_does_not_create_journal_entry(self):
        invoice = self.create_invoice()

        before = JournalEntry.objects.count()

        result = post_invoice(invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            result.pk,
            invoice.pk,
        )

        self.assertEqual(
            invoice.status,
            "POSTED",
        )

        self.assertIsNone(
            invoice.journal_entry_id,
        )

        self.assertEqual(
            invoice.total_gross,
            Decimal("600.00"),
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            before,
        )

    def test_cash_basis_invoice_requires_lines(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-0001",
            customer=self.customer,
            client_name=self.customer.name,
            client_email=self.customer.email,
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
            status="DRAFT",
        )

        with self.assertRaises(ValidationError):
            post_invoice(invoice)

    def test_cash_basis_zero_invoice_rejected(self):
        invoice = self.create_invoice(
            amount="0.00"
        )

        with self.assertRaises(ValidationError):
            post_invoice(invoice)

    def test_cash_basis_invoice_cannot_be_posted_twice(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        with self.assertRaises(ValidationError):
            post_invoice(invoice)

    # ------------------------------------------------------------------
    # Invoice payments
    # ------------------------------------------------------------------

    def test_cash_basis_invoice_payment_reduces_outstanding_amount(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        journal = record_invoice_payment(
            invoice=invoice,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
            reference="BANK-001",
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PARTIAL",
        )

        self.assertEqual(
            invoice.total_paid,
            Decimal("250.00"),
        )

        self.assertEqual(
            invoice.amount_outstanding,
            Decimal("350.00"),
        )

        self.assertIsNotNone(journal)
        self.assertTrue(journal.is_posted)

        self.assertEqual(
            JournalItem.objects.filter(
                entry=journal,
                account=self.bank,
                debit=Decimal("250.00"),
                credit=Decimal("0.00"),
            ).count(),
            1,
        )

        self.assertEqual(
            JournalItem.objects.filter(
                entry=journal,
                account=self.sales,
                debit=Decimal("0.00"),
                credit=Decimal("250.00"),
            ).count(),
            1,
        )

    def test_cash_basis_final_payment_marks_invoice_paid(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
            reference="BANK-001",
        )

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("350.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 5),
            reference="BANK-002",
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PAID",
        )

        self.assertEqual(
            invoice.total_paid,
            Decimal("600.00"),
        )

        self.assertEqual(
            invoice.amount_outstanding,
            Decimal("0.00"),
        )

        self.assertEqual(
            Payment.objects.filter(
                invoice=invoice
            ).count(),
            2,
        )

        self.assertEqual(
            JournalItem.objects.filter(
                account=self.sales,
                entry__is_posted=True,
            ).values("entry").distinct().count(),
            2,
        )

    def test_invoice_overpayment_is_rejected(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        with self.assertRaises(ValidationError):
            record_invoice_payment(
                invoice=invoice,
                amount=Decimal("600.01"),
                bank_account=self.bank,
                accounts_receivable_acc=self.accounts_receivable,
                sales_revenue_acc=self.sales,
                payment_date=date(2026, 9, 2),
                reference="OVERPAY",
            )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.total_paid,
            Decimal("0.00"),
        )

        self.assertEqual(
            Payment.objects.filter(
                invoice=invoice
            ).count(),
            0,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_invoice_payment_requires_posted_invoice(self):
        invoice = self.create_invoice()

        with self.assertRaises(ValidationError):
            record_invoice_payment(
                invoice=invoice,
                amount=Decimal("100.00"),
                bank_account=self.bank,
                accounts_receivable_acc=self.accounts_receivable,
                sales_revenue_acc=self.sales,
                payment_date=date(2026, 9, 2),
            )

        self.assertEqual(
            Payment.objects.count(),
            0,
        )

    def test_zero_invoice_payment_is_rejected(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        with self.assertRaises(ValidationError):
            record_invoice_payment(
                invoice=invoice,
                amount=Decimal("0.00"),
                bank_account=self.bank,
                accounts_receivable_acc=self.accounts_receivable,
                sales_revenue_acc=self.sales,
                payment_date=date(2026, 9, 2),
            )

    def test_negative_invoice_payment_is_rejected(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        with self.assertRaises(ValidationError):
            record_invoice_payment(
                invoice=invoice,
                amount=Decimal("-10.00"),
                bank_account=self.bank,
                accounts_receivable_acc=self.accounts_receivable,
                sales_revenue_acc=self.sales,
                payment_date=date(2026, 9, 2),
            )

    def test_invoice_payment_reference_is_stored(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("600.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
            reference="HSBC-ABC123",
        )

        payment = Payment.objects.get(
            invoice=invoice
        )

        self.assertEqual(
            payment.reference,
            "HSBC-ABC123",
        )

    def test_partial_and_final_invoice_payments_create_separate_journals(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        first_journal = record_invoice_payment(
            invoice=invoice,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
            reference="PAY-001",
        )

        second_journal = record_invoice_payment(
            invoice=invoice,
            amount=Decimal("350.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 5),
            reference="PAY-002",
        )

        self.assertNotEqual(
            first_journal.pk,
            second_journal.pk,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            2,
        )

    # ------------------------------------------------------------------
    # Accounting effects
    # ------------------------------------------------------------------

    def test_cash_basis_invoice_payments_appear_in_profit_and_loss(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
        )

        pnl = profit_and_loss(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 9, 30),
        )

        sales_row = next(
            row
            for row in pnl["revenue"]
            if row["account"] == self.sales
        )

        self.assertEqual(
            sales_row["amount"],
            Decimal("250.00"),
        )

        self.assertEqual(
            pnl["total_revenue"],
            Decimal("250.00"),
        )

        self.assertEqual(
            pnl["net_profit"],
            Decimal("250.00"),
        )

    def test_cash_basis_invoice_payment_increases_bank_balance(self):
        invoice = self.create_invoice()

        post_invoice(invoice)

        initial_balance = self.get_account_balance(
            self.bank
        )

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
        )

        final_balance = self.get_account_balance(
            self.bank
        )

        self.assertEqual(
            final_balance,
            initial_balance + Decimal("250.00"),
        )

    def test_cash_invoice_does_not_recognise_income_on_issue_date(self):
        invoice = self.create_invoice(
            amount="100.00"
        )

        post_invoice(invoice)

        tb = trial_balance(
            as_at=date(2026, 6, 1)
        )

        sales_row = next(
            row
            for row in tb
            if row["account"] == self.sales
        )

        self.assertEqual(
            sales_row["credit"],
            Decimal("0.00"),
        )

        record_invoice_payment(
            invoice=invoice,
            amount=Decimal("100.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 6, 5),
        )

        tb = trial_balance(
            as_at=date(2026, 6, 5)
        )

        sales_row = next(
            row
            for row in tb
            if row["account"] == self.sales
        )

        self.assertEqual(
            sales_row["credit"],
            Decimal("100.00"),
        )

    def test_cash_basis_invoice_partial_payments_only_recognise_cash_received(self):
        invoice = self.create_invoice(
            amount="100.00"
        )

        post_invoice(invoice)

        first_payment = record_invoice_payment(
            invoice=invoice,
            amount=Decimal("40.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 6, 5),
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PARTIAL",
        )

        self.assertEqual(
            invoice.total_paid,
            Decimal("40.00"),
        )

        self.assertEqual(
            invoice.amount_outstanding,
            Decimal("60.00"),
        )

        self.assertIsNone(
            invoice.journal_entry_id
        )

        self.assertEqual(
            self.get_account_balance(self.bank),
            Decimal("40.00"),
        )

        self.assertEqual(
            self.get_account_balance(self.sales),
            Decimal("40.00"),
        )

        second_payment = record_invoice_payment(
            invoice=invoice,
            amount=Decimal("60.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 6, 10),
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PAID",
        )

        self.assertEqual(
            invoice.total_paid,
            Decimal("100.00"),
        )

        self.assertEqual(
            invoice.amount_outstanding,
            Decimal("0.00"),
        )

        self.assertIsNone(
            invoice.journal_entry_id
        )

        self.assertEqual(
            self.get_account_balance(self.bank),
            Decimal("100.00"),
        )

        self.assertEqual(
            self.get_account_balance(self.sales),
            Decimal("100.00"),
        )

        self.assertEqual(
            Payment.objects.filter(
                invoice=invoice
            ).count(),
            2,
        )

        self.assertNotEqual(
            first_payment.pk,
            second_payment.pk,
        )


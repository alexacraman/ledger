
from datetime import date
from decimal import Decimal

from django.core.exceptions import ValidationError

from .test_setup import AccountingTestBase

from accounts.models import (
    JournalEntry,
    Purchase,
    PurchaseLineItem,
    PurchasePayment,
)
from accounts.services.purchases import (
    post_purchase,
    record_purchase_payment,
)
from accounts.services.reports import (
    profit_and_loss,
    trial_balance,
)
from contacts.models import Supplier


class TestPurchases(AccountingTestBase):

    # ------------------------------------------------------------------
    # Setup and helpers
    # ------------------------------------------------------------------

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.supplier = Supplier.objects.create(
            name="Test Supplier",
            email="supplier@example.com",
            is_active=True,
        )

    def create_purchase(self, amount="600.00"):
        purchase = Purchase.objects.create(
            purchase_number="PUR-0001",
            supplier=self.supplier,
            supplier_name=self.supplier.name,
            supplier_email=self.supplier.email,
            reference="SUP-12345",
            purchase_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
            status="DRAFT",
        )

        PurchaseLineItem.objects.create(
            purchase=purchase,
            description="Test purchase",
            quantity=Decimal("1.00"),
            unit_price=Decimal(amount),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return purchase

    # ------------------------------------------------------------------
    # Purchase posting
    # ------------------------------------------------------------------

    def test_cash_basis_purchase_posting_creates_no_journal(self):
        purchase = self.create_purchase()

        result = post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        purchase.refresh_from_db()

        self.assertEqual(
            result.pk,
            purchase.pk,
        )

        self.assertEqual(
            purchase.status,
            "POSTED",
        )

        self.assertIsNone(
            purchase.journal_entry_id,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_cannot_post_purchase_without_lines(self):
        purchase = Purchase.objects.create(
            purchase_number="PUR-0001",
            supplier=self.supplier,
            supplier_name=self.supplier.name,
            supplier_email=self.supplier.email,
            reference="SUP-12345",
            purchase_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
            status="DRAFT",
        )

        with self.assertRaises(ValidationError):
            post_purchase(
                purchase=purchase,
                purchases_acc=self.purchases,
                vat_reclaimable_acc=self.vat_reclaimable,
                accounts_payable_acc=self.accounts_payable,
            )

    def test_cannot_post_zero_value_purchase(self):
        purchase = self.create_purchase("0.00")

        with self.assertRaises(ValidationError):
            post_purchase(
                purchase=purchase,
                purchases_acc=self.purchases,
                vat_reclaimable_acc=self.vat_reclaimable,
                accounts_payable_acc=self.accounts_payable,
            )

    def test_cannot_post_purchase_twice(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        with self.assertRaises(ValidationError):
            post_purchase(
                purchase=purchase,
                purchases_acc=self.purchases,
                vat_reclaimable_acc=self.vat_reclaimable,
                accounts_payable_acc=self.accounts_payable,
            )

    # ------------------------------------------------------------------
    # Purchase payments
    # ------------------------------------------------------------------

    def test_partial_purchase_payment_creates_cash_basis_journal(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        result = record_purchase_payment(
            purchase=purchase,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
            reference="BANK-001",
        )

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PARTIAL",
        )

        self.assertEqual(
            purchase.total_paid,
            Decimal("250.00"),
        )

        self.assertEqual(
            purchase.amount_outstanding,
            Decimal("350.00"),
        )

        self.assertIsNotNone(
            result
        )

        self.assertEqual(
            PurchasePayment.objects.count(),
            1,
        )

        self.assertJournalBalanced(
            result
        )

        debit = result.items.get(
            account=self.purchases,
        )

        credit = result.items.get(
            account=self.bank,
        )

        self.assertEqual(
            debit.debit,
            Decimal("250.00"),
        )

        self.assertEqual(
            credit.credit,
            Decimal("250.00"),
        )

    def test_final_payment_changes_purchase_to_paid(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
            reference="BANK-001",
        )

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("350.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 11),
            reference="BANK-002",
        )

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PAID",
        )

        self.assertEqual(
            purchase.total_paid,
            Decimal("600.00"),
        )

        self.assertEqual(
            purchase.amount_outstanding,
            Decimal("0.00"),
        )

        self.assertEqual(
            PurchasePayment.objects.count(),
            2,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            2,
        )

    def test_purchase_payment_cannot_exceed_outstanding_balance(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        with self.assertRaises(ValidationError):
            record_purchase_payment(
                purchase=purchase,
                amount=Decimal("600.01"),
                bank_account=self.bank,
                accounts_payable_acc=self.accounts_payable,
                purchases_acc=self.purchases,
                payment_date=date(2026, 9, 10),
                reference="BANK-001",
            )

        self.assertEqual(
            PurchasePayment.objects.count(),
            0,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_purchase_payment_cannot_be_recorded_against_draft(self):
        purchase = self.create_purchase()

        with self.assertRaises(ValidationError):
            record_purchase_payment(
                purchase=purchase,
                amount=Decimal("100.00"),
                bank_account=self.bank,
                accounts_payable_acc=self.accounts_payable,
                purchases_acc=self.purchases,
                payment_date=date(2026, 9, 10),
                reference="BANK-001",
            )

        self.assertEqual(
            PurchasePayment.objects.count(),
            0,
        )

        self.assertEqual(
            JournalEntry.objects.count(),
            0,
        )

    def test_purchase_payment_rejects_zero_amount(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        with self.assertRaises(ValidationError):
            record_purchase_payment(
                purchase=purchase,
                amount=Decimal("0.00"),
                bank_account=self.bank,
                accounts_payable_acc=self.accounts_payable,
                purchases_acc=self.purchases,
                payment_date=date(2026, 9, 10),
                reference="BANK-001",
            )

    def test_purchase_payment_rejects_negative_amount(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        with self.assertRaises(ValidationError):
            record_purchase_payment(
                purchase=purchase,
                amount=Decimal("-10.00"),
                bank_account=self.bank,
                accounts_payable_acc=self.accounts_payable,
                purchases_acc=self.purchases,
                payment_date=date(2026, 9, 10),
                reference="BANK-001",
            )

    def test_purchase_payment_reference_is_stored(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("100.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
            reference="BANK-12345",
        )

        payment = PurchasePayment.objects.get(
            purchase=purchase,
        )

        self.assertEqual(
            payment.reference,
            "BANK-12345",
        )

    def test_partial_and_final_payments_create_separate_journal_entries(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        first_entry = record_purchase_payment(
            purchase=purchase,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
            reference="BANK-001",
        )

        second_entry = record_purchase_payment(
            purchase=purchase,
            amount=Decimal("350.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 11),
            reference="BANK-002",
        )

        self.assertNotEqual(
            first_entry.pk,
            second_entry.pk,
        )

        self.assertJournalBalanced(
            first_entry
        )

        self.assertJournalBalanced(
            second_entry
        )

        self.assertEqual(
            first_entry.items.get(
                account=self.purchases
            ).debit,
            Decimal("250.00"),
        )

        self.assertEqual(
            second_entry.items.get(
                account=self.purchases
            ).debit,
            Decimal("350.00"),
        )

        self.assertEqual(
            first_entry.items.get(
                account=self.bank
            ).credit,
            Decimal("250.00"),
        )

        self.assertEqual(
            second_entry.items.get(
                account=self.bank
            ).credit,
            Decimal("350.00"),
        )

    # ------------------------------------------------------------------
    # Cash-basis accounting effects
    # ------------------------------------------------------------------

    def test_cash_basis_purchase_payments_appear_in_profit_and_loss(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
            reference="BANK-001",
        )

        report = profit_and_loss(
            date_from=date(2026, 1, 1),
            date_to=date(2026, 12, 31),
        )

        self.assertEqual(
            report["total_expenses"],
            Decimal("250.00"),
        )

        self.assertEqual(
            report["net_profit"],
            Decimal("-250.00"),
        )

    def test_cash_basis_purchase_payment_reduces_bank_balance(self):
        purchase = self.create_purchase()

        post_purchase(
            purchase=purchase,
            purchases_acc=self.purchases,
            vat_reclaimable_acc=self.vat_reclaimable,
            accounts_payable_acc=self.accounts_payable,
        )

        initial_balance = self.get_account_balance(
            self.bank
        )

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("250.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 10),
            reference="BANK-001",
        )

        final_balance = self.get_account_balance(
            self.bank
        )

        self.assertEqual(
            final_balance,
            initial_balance - Decimal("250.00"),
        )

    def test_cash_purchase_does_not_recognise_expense_on_purchase_date(self):
        purchase = self.create_purchase(
            amount="100.00"
        )

        post_purchase(purchase)

        tb = trial_balance(
            as_at=date(2026, 9, 1)
        )

        purchases_row = next(
            row
            for row in tb
            if row["account"] == self.purchases
        )

        self.assertEqual(
            purchases_row["debit"],
            Decimal("0.00"),
        )

        record_purchase_payment(
            purchase=purchase,
            amount=Decimal("100.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 5),
        )

        tb = trial_balance(
            as_at=date(2026, 9, 5)
        )

        purchases_row = next(
            row
            for row in tb
            if row["account"] == self.purchases
        )

        self.assertEqual(
            purchases_row["debit"],
            Decimal("100.00"),
        )


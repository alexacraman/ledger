
from datetime import date
from decimal import Decimal

from .test_setup import AccountingTestBase

from accounts.models import (
    Expense,
    ExpenseLineItem,
    Invoice,
    InvoiceLineItem,
    JournalEntry,
    Purchase,
    PurchaseLineItem,
)
from accounts.services.capital import (
    record_capital,
    record_drawing,
)
from accounts.services.expenses import record_expense
from accounts.services.purchases import (
    post_purchase,
    record_purchase_payment,
)
from accounts.services.reports import (
    balance_sheet,
    profit_and_loss,
)
from accounts.services.sales import (
    post_invoice,
    record_invoice_payment,
)
from accounts.services.transfers import record_transfer
from contacts.models import Customer, Supplier


class FullCashBasisIntegrationTestCase(AccountingTestBase):

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()

        cls.customer = Customer.objects.create(
            name="Integration Customer",
            email="customer@example.com",
            is_active=True,
        )

        cls.supplier = Supplier.objects.create(
            name="Integration Supplier",
            email="supplier@example.com",
            is_active=True,
        )

    def create_invoice(self):
        invoice = Invoice.objects.create(
            invoice_number="INV-TEST-001",
            customer=self.customer,
            client_name=self.customer.name,
            client_email=self.customer.email,
            issue_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
            status="DRAFT",
        )

        InvoiceLineItem.objects.create(
            invoice=invoice,
            description="Integration sale",
            quantity=Decimal("1.00"),
            unit_price=Decimal("750.00"),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return invoice

    def create_purchase(self):
        purchase = Purchase.objects.create(
            purchase_number="PUR-TEST-001",
            supplier=self.supplier,
            supplier_name=self.supplier.name,
            supplier_email=self.supplier.email,
            reference="SUP-TEST-001",
            purchase_date=date(2026, 9, 1),
            due_date=date(2026, 9, 30),
            status="DRAFT",
        )

        PurchaseLineItem.objects.create(
            purchase=purchase,
            description="Integration purchase",
            quantity=Decimal("1.00"),
            unit_price=Decimal("300.00"),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return purchase

    def create_expense(self):
        expense = Expense.objects.create(
            expense_account=self.general_expenses,
            payment_account=self.bank,
            expense_date=date(2026, 9, 1),
            description="Integration expense",
            supplier_name="Integration Supplier",
            reference="EXP-TEST-001",
            status="DRAFT",
        )

        ExpenseLineItem.objects.create(
            expense=expense,
            description="Integration expense",
            quantity=Decimal("1.00"),
            unit_price=Decimal("100.00"),
            vat_rate=Decimal("0.00"),
            vat_amount=Decimal("0.00"),
        )

        return expense

    def test_complete_business_workflow_reconciles(self):

        # --------------------------------------------------------------
        # Opening capital
        #
        # Dr Bank 2,000
        #     Cr Capital 2,000
        # --------------------------------------------------------------

        record_capital(
            transaction_date=date(2026, 9, 1),
            amount=Decimal("2000.00"),
            capital_account=self.capital,
            payment_account=self.bank,
        )

        # --------------------------------------------------------------
        # Customer invoice £750, fully paid
        #
        # Cash basis:
        # posting invoice = no journal
        # payment = Dr Bank / Cr Sales
        # --------------------------------------------------------------

        invoice = self.create_invoice()

        post_invoice(invoice)

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "POSTED",
        )

        self.assertIsNone(
            invoice.journal_entry_id,
        )

        payment_journal = record_invoice_payment(
            invoice=invoice,
            amount=Decimal("750.00"),
            bank_account=self.bank,
            accounts_receivable_acc=self.accounts_receivable,
            sales_revenue_acc=self.sales,
            payment_date=date(2026, 9, 2),
            reference="CUSTOMER-001",
        )

        self.assertJournalBalanced(
            payment_journal
        )

        invoice.refresh_from_db()

        self.assertEqual(
            invoice.status,
            "PAID",
        )

        self.assertEqual(
            invoice.amount_outstanding,
            Decimal("0.00"),
        )

        # --------------------------------------------------------------
        # Supplier purchase £300, fully paid
        #
        # Cash basis:
        # posting purchase = no journal
        # payment = Dr Purchases / Cr Bank
        # --------------------------------------------------------------

        purchase = self.create_purchase()

        post_purchase(purchase)

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "POSTED",
        )

        self.assertIsNone(
            purchase.journal_entry_id,
        )

        purchase_payment_journal = record_purchase_payment(
            purchase=purchase,
            amount=Decimal("300.00"),
            bank_account=self.bank,
            accounts_payable_acc=self.accounts_payable,
            purchases_acc=self.purchases,
            payment_date=date(2026, 9, 3),
            reference="SUPPLIER-001",
        )

        self.assertJournalBalanced(
            purchase_payment_journal
        )

        purchase.refresh_from_db()

        self.assertEqual(
            purchase.status,
            "PAID",
        )

        self.assertEqual(
            purchase.amount_outstanding,
            Decimal("0.00"),
        )

        # --------------------------------------------------------------
        # Direct business expense £100
        #
        # Dr General Expenses / Cr Bank
        # --------------------------------------------------------------

        expense = self.create_expense()

        record_expense(
            expense=expense,
            expense_account=self.general_expenses,
            payment_account=self.bank,
            reference=expense.reference,
        )

        expense.refresh_from_db()

        self.assertEqual(
            expense.status,
            "POSTED",
        )

        self.assertIsNotNone(
            expense.journal_entry_id,
        )

        self.assertJournalBalanced(
            expense.journal_entry
        )

        # --------------------------------------------------------------
        # Owner drawing £250
        #
        # Dr Drawings / Cr Bank
        # --------------------------------------------------------------

        drawing_journal = record_drawing(
            transaction_date=date(2026, 9, 4),
            amount=Decimal("250.00"),
            drawings_account=self.drawings,
            payment_account=self.bank,
        )

        self.assertJournalBalanced(
            drawing_journal
        )

        # --------------------------------------------------------------
        # Transfer £200 Bank -> Cash
        # --------------------------------------------------------------

        transfer_journal = record_transfer(
            transaction_date=date(2026, 9, 5),
            amount=Decimal("200.00"),
            from_account=self.bank,
            to_account=self.cash,
        )

        self.assertJournalBalanced(
            transfer_journal
        )

        # --------------------------------------------------------------
        # Expected closing position
        #
        # Bank:
        #   +2,000 capital
        #   +750 sales receipt
        #   -300 purchase
        #   -100 expense
        #   -250 drawing
        #   -200 transfer
        #   = 1,900
        #
        # Cash:
        #   +200 transfer
        #
        # Total assets = 2,100
        #
        # Profit:
        #   750 revenue
        #   -300 purchases
        #   -100 expense
        #   = 350
        #
        # Equity:
        #   2,000 capital
        #   -250 drawings
        #   +350 profit
        #   = 2,100
        # --------------------------------------------------------------

        self.assertEqual(
            self.get_account_balance(self.bank),
            Decimal("1900.00"),
        )

        self.assertEqual(
            self.get_account_balance(self.cash),
            Decimal("200.00"),
        )

        pnl = profit_and_loss(
            date_from=date(2026, 9, 1),
            date_to=date(2026, 12, 31),
        )

        self.assertEqual(
            pnl["total_revenue"],
            Decimal("750.00"),
        )

        self.assertEqual(
            pnl["total_expenses"],
            Decimal("400.00"),
        )

        self.assertEqual(
            pnl["net_profit"],
            Decimal("350.00"),
        )

        balance_sheet_report = balance_sheet(
            as_at=date(2026, 12, 31),
        )

        self.assertEqual(
            balance_sheet_report["total_assets"],
            Decimal("2100.00"),
        )

        self.assertEqual(
            balance_sheet_report["total_liabilities"],
            Decimal("0.00"),
        )

        self.assertEqual(
            balance_sheet_report["total_equity"],
            Decimal("2100.00"),
        )

        self.assertEqual(
            balance_sheet_report[
                "total_liabilities_and_equity"
            ],
            Decimal("2100.00"),
        )

        # Final global accounting check:
        # every posted journal must balance.

        for entry in JournalEntry.objects.filter(
            is_posted=True
        ):
            self.assertJournalBalanced(entry)


from decimal import Decimal
from django.test import TestCase
from accounts.models import Account, JournalItem
from business.models import BusinessSettings

class AccountingTestBase(TestCase):
    """
    Shared setup for accounting service tests.
    """

    @classmethod
    def setUpTestData(cls):
        cls.bank = Account.objects.create(
            code="1000",
            name="Bank",
            type="ASSET",
        )

        cls.cash = Account.objects.create(
            code="1100",
            name="Cash",
            type="ASSET",
        )

        cls.accounts_receivable = Account.objects.create(
            code="1200",
            name="Accounts Receivable",
            type="ASSET",
        )

        cls.allowance_for_doubtful_debts = Account.objects.create(
            code="1210",
            name="Allowance for Doubtful Debts",
            type="ASSET",
        )

        cls.accrued_income = Account.objects.create(
            code="1230",
            name="Accrued Income",
            type="ASSET",
        )

        cls.vat_reclaimable = Account.objects.create(
            code="1300",
            name="VAT Reclaimable",
            type="ASSET",
        )

        cls.prepayments = Account.objects.create(
            code="1350",
            name="Prepayments",
            type="ASSET",
        )

        cls.accounts_payable = Account.objects.create(
            code="2000",
            name="Accounts Payable",
            type="LIABILITY",
        )

        cls.vat_liability = Account.objects.create(
            code="2100",
            name="VAT Liability",
            type="LIABILITY",
        )

        cls.accrued_expenses = Account.objects.create(
            code="2200",
            name="Accrued Expenses",
            type="LIABILITY",
        )

        cls.capital = Account.objects.create(
            code="3000",
            name="Capital",
            type="EQUITY",
        )

        cls.drawings = Account.objects.create(
            code="3100",
            name="Drawings",
            type="EQUITY",
        )

        cls.sales = Account.objects.create(
            code="4000",
            name="Sales",
            type="REVENUE",
        )

        cls.purchases = Account.objects.create(
            code="5000",
            name="Purchases",
            type="EXPENSE",
        )

        cls.general_expenses = Account.objects.create(
            code="5300",
            name="General Expenses",
            type="EXPENSE",
        )

        cls.irrecoverable_debts = Account.objects.create(
            code="5400",
            name="Irrecoverable Debts",
            type="EXPENSE",
        )

        cls.settings = BusinessSettings.objects.create(
            business_name="Test Business",
            accounting_basis="CASH",
            vat_registered=False,
            vat_scheme="",
        )

    def setUp(self):
        """
        Reset business settings before each test.
        """
        self.settings.refresh_from_db()

        self.settings.accounting_basis = "CASH"
        self.settings.vat_registered = False
        self.settings.vat_scheme = ""
        self.settings.save()

    def assertJournalBalanced(self, entry):
        self.assertTrue(entry.is_posted)
        self.assertTrue(entry.is_balanced())
        self.assertEqual(
            entry.total_debits,
            entry.total_credits,
        )

    def get_account_balance(self, account):
        """
        Return the net balance for an account from posted journal entries.

        Asset / expense:
            debit - credit

        Liability / equity / revenue:
            credit - debit
        """
        items = JournalItem.objects.filter(
            entry__is_posted=True,
            account=account,
        )

        debit = sum(
            (item.debit for item in items),
            Decimal("0.00"),
        )

        credit = sum(
            (item.credit for item in items),
            Decimal("0.00"),
        )

        if account.type in (
            "ASSET",
            "EXPENSE",
        ):
            return debit - credit

        return credit - debit


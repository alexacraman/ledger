from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Account
from accounts.services.income import record_income

from .models import BusinessSettings
from .services.settings import (
    financial_activity_exists,
    update_business_settings,
)


class BusinessSettingsTests(TestCase):

    def setUp(self):
        self.settings = BusinessSettings.objects.create(
            business_name="Test Business",
            accounting_basis="CASH",
            vat_registered=False,
            vat_scheme="",
        )

        self.bank_account = Account.objects.create(
            code="1000",
            name="Bank",
            type="ASSET",
        )

        self.income_account = Account.objects.create(
            code="4000",
            name="Sales",
            type="REVENUE",
        )

    def test_settings_can_be_updated_before_financial_activity(self):
        settings = update_business_settings(
            business_name="Updated Business",
            accounting_basis="ACCRUAL",
            vat_registered=False,
            vat_scheme="",
        )

        self.assertEqual(settings.business_name, "Updated Business")
        self.assertEqual(settings.accounting_basis, "ACCRUAL")
        self.assertFalse(settings.vat_registered)
        self.assertEqual(settings.vat_scheme, "")

    def test_vat_scheme_is_cleared_when_not_registered(self):
        self.settings.vat_registered = True
        self.settings.vat_scheme = "STANDARD"
        self.settings.save()

        settings = update_business_settings(
            business_name="Test Business",
            accounting_basis="CASH",
            vat_registered=False,
            vat_scheme="STANDARD",
        )

        self.assertFalse(settings.vat_registered)
        self.assertEqual(settings.vat_scheme, "")

    def test_vat_registered_requires_valid_scheme(self):
        with self.assertRaises(ValidationError):
            update_business_settings(
                business_name="Test Business",
                accounting_basis="CASH",
                vat_registered=True,
                vat_scheme="",
            )

    def test_accounting_basis_can_change_before_financial_activity(self):
        settings = update_business_settings(
            business_name="Test Business",
            accounting_basis="ACCRUAL",
            vat_registered=False,
            vat_scheme="",
        )

        self.assertEqual(settings.accounting_basis, "ACCRUAL")

    def test_accounting_basis_cannot_change_after_financial_activity(self):
        record_income(
            income_account=self.income_account,
            payment_account=self.bank_account,
            amount=Decimal("100.00"),
            transaction_date=self._date(),
            description="Test income",
        )

        with self.assertRaises(ValidationError):
            update_business_settings(
                business_name="Test Business",
                accounting_basis="ACCRUAL",
                vat_registered=False,
                vat_scheme="",
            )

    def test_vat_registration_cannot_change_after_financial_activity(self):
        income_account = Account.objects.get(code="4000")
        bank_account = Account.objects.get(code="1000")

        record_income(
            income_account=income_account,
            payment_account=bank_account,
            amount=Decimal("100.00"),
            transaction_date=self._date(),
            description="Test income",
        )

        with self.assertRaises(ValidationError):
            update_business_settings(
                business_name="Test Business",
                accounting_basis="CASH",
                vat_registered=True,
                vat_scheme="STANDARD",
            )

    def test_business_name_can_change_after_financial_activity(self):
        income_account = Account.objects.get(code="4000")
        bank_account = Account.objects.get(code="1000")

        record_income(
            income_account=income_account,
            payment_account=bank_account,
            amount=Decimal("100.00"),
            transaction_date=self._date(),
            description="Test income",
        )

        settings = update_business_settings(
            business_name="New Business Name",
            accounting_basis="CASH",
            vat_registered=False,
            vat_scheme="",
        )

        self.assertEqual(settings.business_name, "New Business Name")

    def test_vat_scheme_can_change_when_registration_status_is_unchanged(self):
        self.settings.vat_registered = True
        self.settings.vat_scheme = "STANDARD"
        self.settings.save()

        settings = update_business_settings(
            business_name="Test Business",
            accounting_basis="CASH",
            vat_registered=True,
            vat_scheme="CASH",
        )

        self.assertEqual(settings.vat_scheme, "CASH")

    def test_financial_activity_exists_false_initially(self):
        self.assertFalse(financial_activity_exists())

    def test_financial_activity_exists_after_journal_entry(self):
        income_account = Account.objects.get(code="4000")
        bank_account = Account.objects.get(code="1000")

        record_income(
            income_account=income_account,
            payment_account=bank_account,
            amount=Decimal("100.00"),
            transaction_date=self._date(),
            description="Test income",
        )

        self.assertTrue(financial_activity_exists())

    @staticmethod
    def _date():
        from datetime import date
        return date(2026, 7, 1)
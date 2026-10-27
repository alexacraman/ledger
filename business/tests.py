from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import TestCase

from accounts.models import Account
from accounts.services.income import record_income

from .models import AccountingBasisPeriod, Business, BusinessSettings, VATRegistrationPeriod
from .services.settings import (
    financial_activity_exists,
    get_accounting_basis_for_date,
    get_vat_registration_for_date,
    update_business_settings,
)


class BusinessIsolationTests(TestCase):

    def test_each_user_can_have_multiple_businesses_with_isolated_accounts(self):
        user = get_user_model().objects.create_user(
            username="soletrader1",
            email="soletrader1@example.com",
            password="secret123",
        )

        first_business = Business.objects.create(owner=user, name="First business")
        second_business = Business.objects.create(owner=user, name="Second business")

        first_account = Account.objects.create(
            business=first_business,
            code="1000",
            name="Bank - First",
            type="ASSET",
        )
        second_account = Account.objects.create(
            business=second_business,
            code="1000",
            name="Bank - Second",
            type="ASSET",
        )

        self.assertEqual(Account.objects.filter(business=first_business).count(), 1)
        self.assertEqual(Account.objects.filter(business=second_business).count(), 1)
        self.assertNotEqual(first_account.pk, second_account.pk)


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

    def test_accounting_basis_can_change_after_financial_activity_if_effective_today(self):
        record_income(
            income_account=self.income_account,
            payment_account=self.bank_account,
            amount=Decimal("100.00"),
            transaction_date=self._date(),
            description="Test income",
        )

        settings = update_business_settings(
            business_name="Test Business",
            accounting_basis="ACCRUAL",
            vat_registered=False,
            vat_scheme="",
        )

        self.assertEqual(settings.accounting_basis, "ACCRUAL")

    def test_vat_registration_can_change_after_financial_activity_if_effective_today(self):
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
            business_name="Test Business",
            accounting_basis="CASH",
            vat_registered=True,
            vat_scheme="STANDARD",
        )

        self.assertTrue(settings.vat_registered)
        self.assertEqual(settings.vat_scheme, "STANDARD")

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

    def test_accounting_basis_is_effective_by_date(self):
        AccountingBasisPeriod.objects.create(
            effective_from="2025-10-01",
            accounting_basis="ACCRUAL",
        )

        before = get_accounting_basis_for_date(self._date_from_iso("2025-09-30"))
        after = get_accounting_basis_for_date(self._date_from_iso("2025-10-15"))

        self.assertEqual(before, "CASH")
        self.assertEqual(after, "ACCRUAL")

    def test_accounting_basis_periods_cannot_overlap(self):
        AccountingBasisPeriod.objects.create(
            effective_from="2025-10-01",
            accounting_basis="ACCRUAL",
        )

        with self.assertRaises(ValidationError):
            AccountingBasisPeriod.objects.create(
                effective_from="2025-09-15",
                effective_to="2025-11-01",
                accounting_basis="CASH",
            )

    def test_vat_registration_is_effective_by_date(self):
        VATRegistrationPeriod.objects.create(
            effective_from="2025-10-01",
            vat_registered=True,
            vat_scheme="STANDARD",
        )

        before = get_vat_registration_for_date(self._date_from_iso("2025-09-30"))
        after = get_vat_registration_for_date(self._date_from_iso("2025-10-15"))

        self.assertFalse(before["vat_registered"])
        self.assertTrue(after["vat_registered"])
        self.assertEqual(after["vat_scheme"], "STANDARD")

    def test_vat_registration_periods_cannot_overlap(self):
        VATRegistrationPeriod.objects.create(
            effective_from="2025-10-01",
            vat_registered=True,
            vat_scheme="STANDARD",
        )

        with self.assertRaises(ValidationError):
            VATRegistrationPeriod.objects.create(
                effective_from="2025-09-15",
                effective_to="2025-11-01",
                vat_registered=False,
                vat_scheme="",
            )

    @staticmethod
    def _date_from_iso(value):
        from datetime import date
        return date.fromisoformat(value)

    @staticmethod
    def _date():
        from datetime import date
        return date(2026, 7, 1)
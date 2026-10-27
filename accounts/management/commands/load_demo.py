import json
from datetime import date
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from accounts.models import Account, Expense, ExpenseLineItem, Invoice, InvoiceLineItem, Purchase, PurchaseLineItem
from accounts.services.expenses import record_expense
from accounts.services.purchases import post_purchase, record_purchase_payment
from accounts.services.sales import mark_invoice_sent, post_invoice, record_invoice_payment

from business.models import BusinessSettings
from contacts.models import Customer, Supplier


class Command(BaseCommand):
    help = "Load dummy bookkeeping data for development."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default="bookkeeping_dummy_data.json",
            help="Path to the dummy data JSON file.",
        )

    def handle(self, *args, **options):
        file_path = Path(options["file"])

        if not file_path.is_absolute():
            file_path = Path(settings.BASE_DIR) / file_path

        if not file_path.exists():
            raise CommandError(
                f"Dummy data file not found: {file_path}"
            )

        try:
            with file_path.open("r", encoding="utf-8") as file:
                data = json.load(file)
        except json.JSONDecodeError as exc:
            raise CommandError(
                f"Invalid JSON: {exc}"
            )

        self.stdout.write(
            self.style.WARNING(
                f"Loading demo data from {file_path}"
            )
        )

        with transaction.atomic():
            accounts = self.load_accounts(
                data.get("accounts", [])
            )

            self.load_business_settings(
                data.get("business_settings", {})
            )

            customers = self.load_customers(
                data.get("customers", [])
            )

            suppliers = self.load_suppliers(
                data.get("suppliers", [])
            )

            self.load_invoices(
                data.get("invoices", []),
                customers,
                accounts,
            )

            self.load_purchases(
                data.get("purchases", []),
                suppliers,
                accounts,
            )

            self.load_expenses(
                data.get("expenses", []),
                accounts,
            )

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(
                "Demo bookkeeping data loaded successfully."
            )
        )

    # ------------------------------------------------------------------
    # Business settings
    # ------------------------------------------------------------------

    def load_business_settings(self, data):
        business_settings, created = (
            BusinessSettings.objects.get_or_create(
                pk=1,
                defaults=data,
            )
        )

        if not created:
            business_settings.business_name = data.get(
                "business_name",
                business_settings.business_name,
            )
            business_settings.accounting_basis = data.get(
                "accounting_basis",
                business_settings.accounting_basis,
            )
            business_settings.vat_registered = data.get(
                "vat_registered",
                business_settings.vat_registered,
            )
            business_settings.vat_scheme = data.get(
                "vat_scheme",
                business_settings.vat_scheme,
            )
            business_settings.save()

        self.stdout.write(
            "  ✓ Business settings"
        )

    # ------------------------------------------------------------------
    # Accounts
    # ------------------------------------------------------------------

    def load_accounts(self, data):
        accounts = {}

        for item in data:
            account, created = Account.objects.update_or_create(
                code=item["code"],
                defaults={
                    "name": item["name"],
                    "type": item["type"],
                    "is_active": item.get(
                        "is_active",
                        True,
                    ),
                },
            )

            accounts[item["code"]] = account

        self.stdout.write(
            f"  ✓ Accounts ({len(accounts)})"
        )

        return accounts

    # ------------------------------------------------------------------
    # Customers
    # ------------------------------------------------------------------

    def load_customers(self, data):
        customers = {}

        for item in data:
            customer, created = (
                Customer.objects.update_or_create(
                    name=item["name"],
                    defaults={
                        "email": item.get("email", ""),
                        "phone": item.get("phone", ""),
                        "address": item.get("address", ""),
                        "postcode": item.get("postcode", ""),
                        "is_active": item.get(
                            "is_active",
                            True,
                        ),
                    },
                )
            )

            customers[item["name"]] = customer

        self.stdout.write(
            f"  ✓ Customers ({len(customers)})"
        )

        return customers

    # ------------------------------------------------------------------
    # Suppliers
    # ------------------------------------------------------------------

    def load_suppliers(self, data):
        suppliers = {}

        for item in data:
            supplier, created = (
                Supplier.objects.update_or_create(
                    name=item["name"],
                    defaults={
                        "email": item.get("email", ""),
                        "phone": item.get("phone", ""),
                        "address": item.get("address", ""),
                        "postcode": item.get("postcode", ""),
                        "is_active": item.get(
                            "is_active",
                            True,
                        ),
                    },
                )
            )

            suppliers[item["name"]] = supplier

        self.stdout.write(
            f"  ✓ Suppliers ({len(suppliers)})"
        )

        return suppliers

    # ------------------------------------------------------------------
    # Invoices
    # ------------------------------------------------------------------

    def load_invoices(self, data, customers, accounts):
        bank = accounts["1000"]
        sales = accounts["4000"]
        accounts_receivable = accounts["1200"]

        count = 0

        for item in data:
            invoice_number = item["invoice_number"]

            if Invoice.objects.filter( invoice_number=invoice_number ).exists():
                self.stdout.write( f"    - {invoice_number} already exists; skipping" )
                continue

            customer = customers[item["customer"]]

            invoice = Invoice.objects.create(
                invoice_number=invoice_number,
                customer=customer,
                client_name=item["client_name"],
                client_email=item["client_email"],
                issue_date=self.parse_date(
                    item["issue_date"]
                ),
                due_date=self.parse_date(
                    item["due_date"]
                ),
                status="DRAFT",
            )

            for line in item.get("lines", []):
                InvoiceLineItem.objects.create(
                    invoice=invoice,
                    description=line["description"],
                    quantity=Decimal(
                        line["quantity"]
                    ),
                    unit_price=Decimal(
                        line["unit_price"]
                    ),
                    vat_rate=Decimal(
                        line.get("vat_rate", "0.00")
                    ),
                    vat_amount=Decimal("0.00"),
                )

            # Draft invoices stay as drafts.
            if item["status"] != "DRAFT":
                post_invoice(invoice)

                invoice.refresh_from_db()

                if item["status"] == "SENT":
                    mark_invoice_sent(invoice)

            # PARTIAL / PAID invoices need real payments.
            for payment in item.get("payments", []):
                record_invoice_payment(
                    invoice=invoice,
                    amount=Decimal(payment["amount"]),
                    bank_account=bank,
                    accounts_receivable_acc=accounts_receivable,
                    sales_revenue_acc=sales,
                    payment_date=self.parse_date(
                        payment["payment_date"]
                    ),
                    reference=payment.get(
                        "reference",
                        "",
                    ),
                )

            count += 1

            self.stdout.write(
                f"    ✓ Invoice {invoice_number}"
            )

        self.stdout.write(
            f"  ✓ Invoices ({count})"
        )

    # ------------------------------------------------------------------
    # Purchases
    # ------------------------------------------------------------------

    def load_purchases(self, data, suppliers, accounts):
        bank = accounts["1000"]
        purchases_account = accounts["5000"]
        accounts_payable = accounts["2000"]

        count = 0

        for item in data:
            reference = item["reference"]
            print(item)
            purchase_number = item["purchase_number"]
            if Purchase.objects.filter( reference=reference ).exists():
                self.stdout.write( f"    - {reference} already exists; skipping" )
                continue
            supplier = suppliers[item["supplier"]]
            purchase = Purchase.objects.create(
            purchase_number=purchase_number,
            supplier=supplier,
            supplier_name=item["supplier"],
            supplier_email=item.get(
                "supplier_email",
                "",
            ),
            reference=reference,
            purchase_date=self.parse_date(
                item["purchase_date"]
            ),
            due_date=self.parse_date(
                item["due_date"]
            ),
            status="DRAFT",
        )

            for line in item.get("lines", []):
                PurchaseLineItem.objects.create(
                    purchase=purchase,
                    description=line["description"],
                    quantity=Decimal(
                        line["quantity"]
                    ),
                    unit_price=Decimal(
                        line["unit_price"]
                    ),
                    vat_rate=Decimal(
                        line.get("vat_rate", "0.00")
                    ),
                    vat_amount=Decimal("0.00"),
                )

            # Finalise using the real purchase service.
            post_purchase(purchase)

            purchase.refresh_from_db()

            for payment in item.get("payments", []):
                record_purchase_payment(
                    purchase=purchase,
                    amount=Decimal(payment["amount"]),
                    bank_account=bank,
                    accounts_payable_acc=accounts_payable,
                    purchases_acc=purchases_account,
                    payment_date=self.parse_date(
                        payment["payment_date"]
                    ),
                    reference=payment.get(
                        "reference",
                        "",
                    ),
                )

            count += 1

            self.stdout.write(
                f"    ✓ Purchase {reference}"
            )

        self.stdout.write(
            f"  ✓ Purchases ({count})"
        )

    # ------------------------------------------------------------------
    # Expenses
    # ------------------------------------------------------------------

    def load_expenses(self, data, accounts):
        expense_account = accounts["5300"]
        bank = accounts["1000"]

        count = 0

        for item in data:
            reference = item.get("reference", "")

            if reference and Expense.objects.filter(
                reference=reference
            ).exists():
                self.stdout.write(
                    f"    - {reference} already exists; skipping"
                )
                continue

            expense = Expense.objects.create(
                expense_date=self.parse_date(
                    item["expense_date"]
                ),
                description=item["description"],
                supplier_name=item.get(
                    "supplier_name",
                    "",
                ),
                reference=reference,
                status="DRAFT",
            )

            for line in item.get("lines", []):
                ExpenseLineItem.objects.create(
                    expense=expense,
                    description=line["description"],
                    quantity=Decimal(
                        line["quantity"]
                    ),
                    unit_price=Decimal(
                        line["unit_price"]
                    ),
                    vat_rate=Decimal(
                        line.get("vat_rate", "0.00")
                    ),
                    vat_amount=Decimal("0.00"),
                )

            # Expense is already paid, so this creates
            # the journal immediately.
            record_expense(
                expense=expense,
                expense_account=expense_account,
                payment_account=bank,
                reference=reference,
            )

            count += 1

            self.stdout.write(
                f"    ✓ Expense {reference}"
            )

        self.stdout.write(
            f"  ✓ Expenses ({count})"
        )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def parse_date(value):
        return date.fromisoformat(value)
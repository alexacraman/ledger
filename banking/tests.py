from datetime import date
from decimal import Decimal

from accounts.models import (
    Account,
    JournalEntry,
)

from accounts.services.journal import create_journal_entry


from .services.reconciliation import (
    get_reconciliation_candidates,
    reconcile_bank_transaction,
)
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import Account

from .models import (
    BankAccount,
    BankStatementImport,
    BankTransaction,
)
from .services.imports import import_bank_statement

class BankStatementImportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.bank = Account.objects.create(
            code="1000",
            name="Bank",
            type="ASSET",
        )

        cls.bank_account = BankAccount.objects.create(
            name="Business Bank",
            account=cls.bank,
        )

    def upload(self, content, name="statement.csv"):
        return SimpleUploadedFile(
            name,
            content.encode("utf-8"),
            content_type="text/csv",
        )

    def test_statement_can_be_imported(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Customer payment,BACS-001,450.00\n"
            "02/09/2026,Supplier payment,REF-001,-125.50\n"
        )

        result = import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=statement,
        )

        self.assertEqual(
            result.rows_imported,
            2,
        )

        self.assertEqual(
            result.rows_skipped,
            0,
        )

        self.assertEqual(
            BankTransaction.objects.count(),
            2,
        )

    def test_import_does_not_create_journal_entries(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Customer payment,BACS-001,450.00\n"
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=statement,
        )

        transaction = BankTransaction.objects.get()

        self.assertIsNone(
            transaction.journal_entry,
        )

        self.assertFalse(
            transaction.reconciled,
        )

    def test_duplicate_file_is_rejected(self):
        content = (
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Customer payment,BACS-001,450.00\n"
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.upload(content),
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=self.upload(content),
            )

        self.assertEqual(
            BankTransaction.objects.count(),
            1,
        )

        self.assertEqual(
            BankStatementImport.objects.count(),
            1,
        )

    def test_duplicate_reference_is_skipped(self):
        first = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Customer payment,BACS-001,450.00\n"
        )

        second = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Customer payment,BACS-001,450.00\n"
            "02/09/2026,Another payment,BACS-002,200.00\n",
            name="statement-2.csv",
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=first,
        )

        result = import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=second,
        )

        self.assertEqual(
            result.rows_imported,
            1,
        )

        self.assertEqual(
            result.rows_skipped,
            1,
        )

        self.assertEqual(
            BankTransaction.objects.count(),
            2,
        )

    def test_blank_rows_are_ignored(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "\n"
            "01/09/2026,Customer payment,BACS-001,450.00\n"
            "\n"
        )

        result = import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=statement,
        )

        self.assertEqual(
            result.rows_imported,
            1,
        )

    def test_missing_required_column_is_rejected(self):
        statement = self.upload(
            "Date,Description,Reference\n"
            "01/09/2026,Customer payment,BACS-001\n"
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=statement,
            )

        self.assertEqual(
            BankTransaction.objects.count(),
            0,
        )

    def test_invalid_date_is_rejected(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "not-a-date,Customer payment,BACS-001,450.00\n"
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=statement,
            )

        self.assertEqual(
            BankTransaction.objects.count(),
            0,
        )

    def test_invalid_amount_is_rejected(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Customer payment,BACS-001,not-money\n"
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=statement,
            )

        self.assertEqual(
            BankTransaction.objects.count(),
            0,
        )

    def test_zero_amount_is_rejected(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Zero transaction,BACS-001,0.00\n"
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=statement,
            )

    def test_import_rollback_leaves_no_partial_rows(self):
        statement = self.upload(
            "Date,Description,Reference,Amount\n"
            "01/09/2026,Valid payment,BACS-001,450.00\n"
            "bad-date,Invalid payment,BACS-002,100.00\n"
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=statement,
            )

        self.assertEqual(
            BankTransaction.objects.count(),
            0,
        )

        self.assertEqual(
            BankStatementImport.objects.count(),
            0,
        )


from datetime import date
from decimal import Decimal
from io import BytesIO

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from accounts.models import Account, JournalItem
from accounts.services.journal import create_journal_entry
from banking.models import (
    BankAccount,
    BankStatementImport,
    BankTransaction,
)
from banking.services.imports import import_bank_statement


class BankStatementImportTests(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.bank_ledger = Account.objects.create(
            code="1000",
            name="Bank",
            type="ASSET",
        )

        cls.bank_account = BankAccount.objects.create(
            name="Test Bank Account",
            account=cls.bank_ledger,
        )

    def make_csv(self, content):
        return SimpleUploadedFile(
            "statement.csv",
            content.encode("utf-8"),
            content_type="text/csv",
        )

    # ------------------------------------------------------------------
    # Basic import
    # ------------------------------------------------------------------

    def test_imports_bank_csv(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Opening payment","25.00","","975.00"\n'
            '"02 Apr 2026","BACS","Customer payment","","100.00","1075.00"\n'
        )

        result = import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.make_csv(csv_content),
        )

        self.assertEqual(
            BankTransaction.objects.count(),
            2,
        )

        transactions = BankTransaction.objects.order_by(
            "transaction_date",
            "id",
        )

        first = transactions[0]
        second = transactions[1]

        self.assertEqual(
            first.transaction_date,
            date(2026, 4, 1),
        )
        self.assertEqual(
            first.transaction_type,
            "BACS",
        )
        self.assertEqual(
            first.description,
            "Opening payment",
        )
        self.assertEqual(
            first.amount,
            Decimal("-25.00"),
        )
        self.assertEqual(
            first.balance,
            Decimal("975.00"),
        )

        self.assertEqual(
            second.transaction_date,
            date(2026, 4, 2),
        )
        self.assertEqual(
            second.transaction_type,
            "BACS",
        )
        self.assertEqual(
            second.description,
            "Customer payment",
        )
        self.assertEqual(
            second.amount,
            Decimal("100.00"),
        )
        self.assertEqual(
            second.balance,
            Decimal("1075.00"),
        )

        self.assertFalse(first.reconciled)
        self.assertIsNone(first.journal_entry_id)

        self.assertFalse(second.reconciled)
        self.assertIsNone(second.journal_entry_id)

    # ------------------------------------------------------------------
    # Date formats
    # ------------------------------------------------------------------

    def test_import_accepts_bank_date_format(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Payment","25.00","","975.00"\n'
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.make_csv(csv_content),
        )

        transaction = BankTransaction.objects.get()

        self.assertEqual(
            transaction.transaction_date,
            date(2026, 4, 1),
        )

    # ------------------------------------------------------------------
    # Paid out / paid in
    # ------------------------------------------------------------------

    def test_paid_out_becomes_negative_amount(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Supplier payment","125.50","","874.50"\n'
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.make_csv(csv_content),
        )

        transaction = BankTransaction.objects.get()

        self.assertEqual(
            transaction.amount,
            Decimal("-125.50"),
        )

    def test_paid_in_becomes_positive_amount(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Customer payment","","250.75","1250.75"\n'
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.make_csv(csv_content),
        )

        transaction = BankTransaction.objects.get()

        self.assertEqual(
            transaction.amount,
            Decimal("250.75"),
        )

    def test_row_cannot_have_both_paid_out_and_paid_in(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Invalid","100.00","50.00","950.00"\n'
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=self.make_csv(csv_content),
            )

    def test_row_cannot_have_neither_paid_out_nor_paid_in(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Invalid","","","1000.00"\n'
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=self.make_csv(csv_content),
            )

    # ------------------------------------------------------------------
    # Required columns
    # ------------------------------------------------------------------

    def test_import_rejects_old_csv_format(self):
        csv_content = (
            '"Date","Description","Reference","Amount"\n'
            '"01 Apr 2026","Old format","REF001","100.00"\n'
        )

        with self.assertRaises(ValidationError) as context:
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=self.make_csv(csv_content),
            )

        self.assertEqual(
            str(context.exception),
            "['The CSV file does not contain the expected transaction header.']",
        )

    # ------------------------------------------------------------------
    # Empty / invalid files
    # ------------------------------------------------------------------

    def test_empty_csv_is_rejected(self):
        uploaded_file = self.make_csv("")

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=uploaded_file,
            )

    def test_zero_amount_is_rejected(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Zero transaction","","0.00","1000.00"\n'
        )

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=self.make_csv(csv_content),
            )

    # ------------------------------------------------------------------
    # Audit batch
    # ------------------------------------------------------------------

    def test_import_creates_statement_import_batch(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Payment","25.00","","975.00"\n'
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.make_csv(csv_content),
        )

        statement_import = BankStatementImport.objects.get()

        self.assertEqual(
            statement_import.bank_account,
            self.bank_account,
        )

        self.assertEqual(
            statement_import.rows_imported,
            1,
        )

        self.assertEqual(
            statement_import.transactions.count(),
            1,
        )

    # ------------------------------------------------------------------
    # Duplicate file detection
    # ------------------------------------------------------------------

    def test_same_file_cannot_be_imported_twice(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Payment","25.00","","975.00"\n'
        )

        first_file = self.make_csv(csv_content)

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=first_file,
        )

        second_file = self.make_csv(csv_content)

        with self.assertRaises(ValidationError):
            import_bank_statement(
                bank_account=self.bank_account,
                uploaded_file=second_file,
            )

        self.assertEqual(
            BankStatementImport.objects.count(),
            1,
        )

        self.assertEqual(
            BankTransaction.objects.count(),
            1,
        )

    # ------------------------------------------------------------------
    # Import does not create accounting entries
    # ------------------------------------------------------------------

    def test_import_does_not_create_journal_entry(self):
        csv_content = (
            '"Date","Transaction type","Description","Paid out","Paid in","Balance"\n'
            '"01 Apr 2026","BACS","Customer payment","","100.00","1100.00"\n'
        )

        import_bank_statement(
            bank_account=self.bank_account,
            uploaded_file=self.make_csv(csv_content),
        )

        transaction = BankTransaction.objects.get()

        self.assertIsNone(
            transaction.journal_entry,
        )

        self.assertFalse(
            transaction.reconciled,
        )

        self.assertEqual(
            JournalItem.objects.count(),
            0,
        )
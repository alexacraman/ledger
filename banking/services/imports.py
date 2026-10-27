
import csv
import hashlib
import io

from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.core.exceptions import ValidationError
from django.db import transaction

from banking.models import (
    BankAccount,
    BankStatementImport,
    BankTransaction,
)


# ----------------------------------------------------------------------
# CSV structure supplied by the bank
# ----------------------------------------------------------------------

REQUIRED_COLUMNS = {
    "Date",
    "Transaction type",
    "Description",
    "Paid out",
    "Paid in",
    "Balance",
}


# ----------------------------------------------------------------------
# Parsing helpers
# ----------------------------------------------------------------------

def _parse_date(value, row_number):
    value = (value or "").strip()

    formats = (
        "%d %b %Y",   # 01 Apr 2026
        "%Y-%m-%d",   # 2026-04-01
        "%d/%m/%Y",   # 01/04/2026
        "%d-%m-%Y",   # 01-04-2026
    )

    for date_format in formats:
        try:
            return datetime.strptime(
                value,
                date_format,
            ).date()
        except ValueError:
            continue

    raise ValidationError(
        f"Row {row_number}: invalid date '{value}'."
    )




def _parse_optional_amount(
    value,
    row_number,
    field_name,
):
    """
    Parse a bank CSV money field.

    Blank values are allowed because the bank will normally
    populate either Paid out or Paid in, not both.
    """

    value = (value or "").strip()

    if not value:
        return None

    value = (
        value
        .replace("£", "")
        .replace(",", "")
        .strip()
    )

    # Support accounting-style negative amounts.
    if value.startswith("(") and value.endswith(")"):
        value = f"-{value[1:-1]}"

    try:
        return Decimal(value).quantize(
            Decimal("0.01")
        )
    except (InvalidOperation, ValueError):
        raise ValidationError(
            f"Row {row_number}: invalid {field_name} '{value}'."
        )



def _read_csv(uploaded_file):
    """
    Read and validate the uploaded bank CSV.

    The expected transaction header is:

        Date
        Transaction type
        Description
        Paid out
        Paid in
        Balance

    The bank may quote CSV fields, so header detection is performed
    using Python's CSV parser rather than simple string splitting.
    """

    raw = uploaded_file.read()

    try:
        decoded = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise ValidationError(
            "The CSV file must be encoded as UTF-8."
        )

    if not decoded.strip():
        raise ValidationError(
            "The CSV file is empty."
        )

    lines = decoded.splitlines()

    # --------------------------------------------------------------
    # Find the actual transaction header.
    # --------------------------------------------------------------

    header_index = None
    delimiter = None

    for index, line in enumerate(lines):

        if not line.strip():
            continue

        for candidate in (",", ";", "\t"):

            try:
                parsed_header = next(
                    csv.reader(
                        [line],
                        delimiter=candidate,
                    )
                )
            except (csv.Error, StopIteration):
                continue

            columns = {
                value.strip()
                for value in parsed_header
            }

            if REQUIRED_COLUMNS.issubset(columns):
                header_index = index
                delimiter = candidate
                break

        if header_index is not None:
            break

    if header_index is None:
        raise ValidationError(
            "The CSV file does not contain the expected transaction header."
        )

    # --------------------------------------------------------------
    # Start reading from the actual transaction header.
    # --------------------------------------------------------------

    csv_content = "\n".join(
        lines[header_index:]
    )

    reader = csv.DictReader(
        io.StringIO(csv_content),
        delimiter=delimiter,
    )

    if not reader.fieldnames:
        raise ValidationError(
            "The CSV file does not contain a header row."
        )

    # Clean whitespace/BOM from parsed headers.
    reader.fieldnames = [
        header.strip().lstrip("\ufeff")
        for header in reader.fieldnames
        if header
    ]

    headers = set(reader.fieldnames)

    missing = REQUIRED_COLUMNS - headers

    if missing:
        missing_text = ", ".join(
            sorted(missing)
        )

        found_text = ", ".join(
            reader.fieldnames
        )

        raise ValidationError(
            f"The CSV is missing required columns: "
            f"{missing_text}. "
            f"Columns found: {found_text}."
        )

    return raw, reader




# ----------------------------------------------------------------------
# Main importer
# ----------------------------------------------------------------------

@transaction.atomic
def import_bank_statement(
    *,
    bank_account,
    uploaded_file,
):
    """
    Import a bank statement CSV.

    Expected columns:

        Date
        Transaction type
        Description
        Paid out
        Paid in
        Balance

    Positive amounts represent money received.

    Negative amounts represent money paid out.

    Importing a bank statement does NOT create journal entries.
    Imported transactions remain unreconciled until they are
    matched to accounting records.

    The complete file is protected against re-import using a SHA-256
    hash.
    """

    if not isinstance(bank_account, BankAccount):
        raise ValidationError(
            "Invalid bank account."
        )

    if not bank_account.is_active:
        raise ValidationError(
            "This bank account is inactive."
        )

    raw, reader = _read_csv(
        uploaded_file
    )

    # ------------------------------------------------------------------
    # Protect against importing the exact same file twice.
    # ------------------------------------------------------------------

    file_hash = hashlib.sha256(
        raw
    ).hexdigest()

    if BankStatementImport.objects.filter(
        file_hash=file_hash
    ).exists():
        raise ValidationError(
            "This statement file has already been imported."
        )

    # ------------------------------------------------------------------
    # Create the import batch.
    # ------------------------------------------------------------------

    statement_import = BankStatementImport.objects.create(
        bank_account=bank_account,
        filename=uploaded_file.name[:255],
        file_hash=file_hash,
    )

    rows_imported = 0
    rows_skipped = 0

    # ------------------------------------------------------------------
    # Process each CSV row.
    # ------------------------------------------------------------------

    for row_number, row in enumerate(
        reader,
        start=2,
    ):
        cleaned_row = {
            key.strip(): (
                value.strip()
                if isinstance(value, str)
                else value
            )
            for key, value in row.items()
            if key
        }

        # Ignore completely blank rows.
        if not any(
            value
            for value in cleaned_row.values()
            if value is not None
        ):
            continue

        # --------------------------------------------------------------
        # Date
        # --------------------------------------------------------------

        transaction_date = _parse_date(
            cleaned_row.get("Date"),
            row_number,
        )

        # --------------------------------------------------------------
        # Transaction type
        # --------------------------------------------------------------

        transaction_type = (
            cleaned_row.get("Transaction type")
            or ""
        ).strip()

        # --------------------------------------------------------------
        # Description
        # --------------------------------------------------------------

        description = (
            cleaned_row.get("Description")
            or ""
        ).strip()

        if not description:
            raise ValidationError(
                f"Row {row_number}: description is required."
            )

        # --------------------------------------------------------------
        # Paid out / Paid in
        # --------------------------------------------------------------

        paid_out = _parse_optional_amount(
            cleaned_row.get("Paid out"),
            row_number,
            "Paid out",
        )

        paid_in = _parse_optional_amount(
            cleaned_row.get("Paid in"),
            row_number,
            "Paid in",
        )

        if paid_out is not None and paid_in is not None:
            raise ValidationError(
                f"Row {row_number}: both Paid out and Paid in contain values."
            )

        if paid_out is None and paid_in is None:
            raise ValidationError(
                f"Row {row_number}: either Paid out or Paid in must contain a value."
            )

        if paid_out is not None:
            amount = -abs(paid_out)
        else:
            amount = abs(paid_in)

        if amount == Decimal("0.00"):
            raise ValidationError(
                f"Row {row_number}: transaction amount cannot be zero."
            )

        # --------------------------------------------------------------
        # Running balance
        # --------------------------------------------------------------

        balance = _parse_optional_amount(
            cleaned_row.get("Balance"),
            row_number,
            "Balance",
        )

        # --------------------------------------------------------------
        # Create bank transaction.
        # --------------------------------------------------------------

        BankTransaction.objects.create(
            bank_account=bank_account,
            import_batch=statement_import,
            source_row=row_number,
            transaction_date=transaction_date,
            transaction_type=transaction_type,
            description=description,
            amount=amount,
            balance=balance,
            reference="",
            journal_entry=None,
            reconciled=False,
        )

        rows_imported += 1

    # ------------------------------------------------------------------
    # Do not retain an empty import batch.
    # ------------------------------------------------------------------

    if rows_imported == 0:
        statement_import.delete()

        raise ValidationError(
            "No bank transactions were imported."
        )

    # ------------------------------------------------------------------
    # Store import results.
    # ------------------------------------------------------------------

    statement_import.rows_imported = rows_imported
    statement_import.rows_skipped = rows_skipped

    statement_import.save(
        update_fields=[
            "rows_imported",
            "rows_skipped",
        ]
    )

    return statement_import


from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models

from accounts.models import Account, JournalEntry


class BankAccount(models.Model):
    """
    Represents a real-world bank account used by the business.
    The related Account is the corresponding ledger account.
    """
    name        = models.CharField( max_length=100, )
    account     = models.ForeignKey( Account, on_delete=models.PROTECT, related_name="bank_accounts", )
    is_active   = models.BooleanField( default=True, )

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                fields=["account"],
                name="unique_bank_account_ledger_account",
            ),
        ]

    def __str__(self):
        return self.name

    def clean(self):
        if self.account_id:
            if self.account.type != "ASSET":
                raise ValidationError( "A bank account must be linked to an asset account." )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)


class BankStatementImport(models.Model):
    """
    Represents one imported bank statement file.
    The file hash prevents the exact same file being imported twice.
    """
    bank_account  = models.ForeignKey( BankAccount, on_delete=models.PROTECT, related_name="statement_imports", )
    filename      = models.CharField( max_length=255, )
    file_hash     = models.CharField( max_length=64, unique=True, )
    imported_at   = models.DateTimeField( auto_now_add=True, )
    rows_imported = models.PositiveIntegerField( default=0, ) 
    rows_skipped  = models.PositiveIntegerField( default=0, )

    class Meta:
        ordering = ["-imported_at"]

    def __str__(self):
        return self.filename


class BankTransaction(models.Model):
    """
    A transaction imported or entered from a bank statement.
    Positive amounts represent money received.
    Negative amounts represent money paid out.
    Importing a bank transaction never creates an accounting entry.
    """
    bank_account     = models.ForeignKey( BankAccount, on_delete=models.PROTECT, related_name="transactions", )
    import_batch     = models.ForeignKey( BankStatementImport, on_delete=models.PROTECT, null=True, blank=True, related_name="transactions", )
    source_row       = models.PositiveIntegerField( null=True, blank=True, )
    transaction_date = models.DateField()
    transaction_type = models.CharField( max_length=100, blank=True, )
    description      = models.CharField( max_length=255, )
    amount           = models.DecimalField( max_digits=12, decimal_places=2, )
    balance          = models.DecimalField( max_digits=12, decimal_places=2, null=True, blank=True, )
    reference        = models.CharField( max_length=100, blank=True, )
    journal_entry    = models.ForeignKey( JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name="bank_transactions", )
    reconciled       = models.BooleanField( default=False, )
    created_at       = models.DateTimeField( auto_now_add=True, )

    @property
    def absolute_amount(self):
        return abs(self.amount)

    class Meta:
        ordering = [
            "-transaction_date",
            "-id",
        ]

    def __str__(self):
        return (
            f"{self.transaction_date} - "
            f"{self.description} - "
            f"{self.amount}"
        )

    def clean(self):
        if self.amount == Decimal("0.00"):
            raise ValidationError( "A bank transaction amount cannot be zero." )

        if self.reconciled and not self.journal_entry_id:
            raise ValidationError( "A reconciled bank transaction must have a journal entry." )

        if self.journal_entry_id and not self.reconciled:
            raise ValidationError( "A bank transaction linked to a journal entry must be reconciled." )

        if self.import_batch_id:
            if self.bank_account_id != self.import_batch.bank_account_id:
                raise ValidationError( "The bank transaction and import batch must belong " "to the same bank account." )
    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)
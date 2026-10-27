from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import models



class Account(models.Model):
    ACCOUNT_TYPES = [('ASSET', 'Asset'), ('LIABILITY', 'Liability'), ('EQUITY', 'Equity'), ('REVENUE', 'Revenue'), ('EXPENSE', 'Expense')]
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=100, unique=True)
    type = models.CharField(max_length=20, choices=ACCOUNT_TYPES)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return f'{self.code} - {self.name}'

class AccountingPeriod(models.Model):
    name        = models.CharField(max_length=20)
    start_date  = models.DateField()
    end_date    = models.DateField()
    is_closed   = models.BooleanField(default=False)

    class Meta:
        ordering = ['start_date']
        constraints = [models.UniqueConstraint(fields=['start_date', 'end_date'], name='unique_accounting_period_dates')]

    def __str__(self):
        return self.name

    def clean(self):
        if self.start_date and self.end_date:
            if self.start_date > self.end_date:
                raise ValidationError('The start date cannot be after the end date.')
            overlapping = AccountingPeriod.objects.filter(start_date__lte=self.end_date, end_date__gte=self.start_date).exclude(pk=self.pk)
            if overlapping.exists():
                raise ValidationError('This accounting period overlaps an existing period.')

class JournalEntry(models.Model):
    reference           = models.CharField(max_length=50, blank=True)
    description         = models.CharField(max_length=255)
    transaction_date    = models.DateField()
    period              = models.ForeignKey(AccountingPeriod, on_delete=models.PROTECT, related_name='journal_entries')
    created_at          = models.DateTimeField(auto_now_add=True)
    is_posted           = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.transaction_date} - {self.description}'

    @property
    def total_debits(self):
        return sum((item.debit for item in self.items.all()), Decimal('0.00'))

    @property
    def total_credits(self):
        return sum((item.credit for item in self.items.all()), Decimal('0.00'))

    def is_balanced(self):
        return self.total_debits == self.total_credits

    def post(self):
        if self.is_posted:
            raise ValidationError('This journal entry has already been posted.')
        if self.period.is_closed:
            raise ValidationError(f'Accounting period {self.period.name} is closed.')
        if not self.period.start_date <= self.transaction_date <= self.period.end_date:
            raise ValidationError(f'Transaction date {self.transaction_date} is outside accounting period {self.period.name}.')
        if not self.items.exists():
            raise ValidationError('A journal entry must contain at least one line.')
        if not self.is_balanced():
            raise ValidationError(f'Journal entry is not balanced. Debits: {self.total_debits}, Credits: {self.total_credits}')
        self.is_posted = True
        self.save(update_fields=['is_posted'])

    def delete(self, *args, **kwargs):
        if self.is_posted:
            raise ValidationError('Posted journal entries cannot be deleted.')
        return super().delete(*args, **kwargs)

class JournalItem(models.Model):
    entry    = models.ForeignKey(JournalEntry, on_delete=models.CASCADE, related_name='items')
    account  = models.ForeignKey(Account, on_delete=models.PROTECT, related_name='journal_items')
    debit    = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    credit   = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    def clean(self):
        if self.debit < 0 or self.credit < 0:
            raise ValidationError('Debit and credit amounts cannot be negative.')
        if self.debit > 0 and self.credit > 0:
            raise ValidationError('A line cannot contain both a debit and a credit.')
        if self.debit == 0 and self.credit == 0:
            raise ValidationError('A line must contain either a debit or a credit.')
        if self.entry_id and self.entry.is_posted:
            raise ValidationError('Posted journal entries cannot be changed.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.entry.is_posted:
            raise ValidationError('Posted journal entries cannot be changed.')
        return super().delete(*args, **kwargs)

    def __str__(self):
        return f'{self.account} - {self.entry}'

class Invoice(models.Model):
    INVOICE_STATUS = [('DRAFT', 'Draft'), ('POSTED', 'Posted'), ('SENT', 'Sent'), ('PARTIAL', 'Partially Paid'), ('PAID', 'Paid'), ('VOID', 'Void')]
    invoice_number = models.CharField(max_length=50, unique=True)
    customer       = models.ForeignKey('contacts.Customer', on_delete=models.PROTECT, related_name='invoices')
    client_name    = models.CharField(max_length=150)
    client_email   = models.EmailField()
    issue_date     = models.DateField()
    due_date       = models.DateField()
    status         = models.CharField(max_length=10, choices=INVOICE_STATUS, default='DRAFT')
    journal_entry  = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name='invoice')

    def __str__(self):
        return f'Invoice {self.invoice_number} - {self.client_name}'

    @property
    def total_net(self):
        return sum((line.net_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_vat(self):
        return sum((line.vat_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_gross(self):
        return self.total_net + self.total_vat

    @property
    def total_paid(self):
        return sum((payment.amount for payment in self.payments.all()), Decimal('0.00'))

    @property
    def amount_outstanding(self):
        return self.total_gross - self.total_paid

    def save(self, *args, **kwargs):
        if self.pk:
            original = Invoice.objects.get(pk=self.pk)
            if original.status in ['POSTED', 'SENT', 'PARTIAL', 'PAID', 'VOID']:
                financial_fields = ['client_name', 'client_email', 'issue_date', 'due_date']
                for field in financial_fields:
                    if getattr(original, field) != getattr(self, field):
                        raise ValidationError('Posted invoices cannot be financially edited.')
        super().save(*args, **kwargs)

class InvoiceLineItem(models.Model):
    invoice     = models.ForeignKey( Invoice, on_delete=models.CASCADE, related_name="lines", )
    description = models.CharField(max_length=255)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    vat_rate    = models.DecimalField( max_digits=5, decimal_places=2, default=0, )
    vat_amount  = models.DecimalField( max_digits=12, decimal_places=2, default=0, )

    @property
    def net_amount(self):
        return self.quantity * self.unit_price

    @property
    def gross_amount(self):
        return self.net_amount + self.vat_amount
    
class InvoiceNumberSequence(models.Model):
    name        = models.CharField(max_length=20, unique=True)
    next_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name

class InvoiceEmail(models.Model):
    STATUS_CHOICES = [
        ("SENT", "Sent"),
        ("FAILED", "Failed"),
    ]

    invoice    = models.ForeignKey( Invoice, on_delete=models.PROTECT, related_name="email_deliveries")
    recipient  = models.EmailField()
    subject    = models.CharField(max_length=255)
    status     = models.CharField( max_length=10, choices=STATUS_CHOICES, )
    sent_at    = models.DateTimeField( null=True, blank=True, )
    created_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.invoice.invoice_number} - {self.status}"

class Payment(models.Model):
    invoice       = models.ForeignKey(Invoice, on_delete=models.PROTECT, related_name='payments')
    payment_date  = models.DateField()
    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, related_name='payment')
    reference     = models.CharField(max_length=100, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.amount is None:
            return

        if self.amount <= 0:
            raise ValidationError(
                "Payment amount must be greater than zero."
            )

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.invoice.invoice_number} - {self.amount}'

class Purchase(models.Model):
    PURCHASE_STATUS = [
        ('DRAFT', 'Draft'), 
        ('POSTED', 'Posted'), 
        ('PARTIAL', 'Partially Paid'), 
        ('PAID', 'Paid'), 
        ('VOID', 'Void')
        ]
    supplier        = models.ForeignKey('contacts.Supplier', on_delete=models.PROTECT, related_name='purchases')
    supplier_name   = models.CharField(max_length=150)
    supplier_email  = models.EmailField(blank=True)
    purchase_number = models.CharField( max_length=20, unique=True)
    reference       = models.CharField(max_length=100, blank=True)
    purchase_date   = models.DateField()
    due_date        = models.DateField(blank=True, null=True)
    status          = models.CharField(max_length=10, choices=PURCHASE_STATUS, default='DRAFT')
    journal_entry   = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name='purchase')

    def __str__(self):
        return f'{self.supplier_name} - {self.reference}'

    @property
    def total_net(self):
        return sum((line.net_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_vat(self):
        return sum((line.vat_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_gross(self):
        return self.total_net + self.total_vat

    @property
    def total_paid(self):
        return sum((payment.amount for payment in self.payments.all()), Decimal('0.00'))

    @property
    def amount_outstanding(self):
        return self.total_gross - self.total_paid

class PurchaseLineItem(models.Model):
    purchase    = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=255)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    vat_rate    = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    vat_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    @property
    def net_amount(self):
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))

    @property
    def gross_amount(self):
        return self.net_amount + self.vat_amount

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')
        if self.unit_price < 0:
            raise ValidationError('Unit price cannot be negative.')
        if self.vat_rate < 0 or self.vat_rate > 100:
            raise ValidationError('VAT rate must be between 0 and 100.')
        if self.purchase.status in ['POSTED', 'PARTIAL', 'PAID', 'VOID']:
            raise ValidationError('Purchase lines cannot be changed after the purchase has been posted.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.purchase.status in ['POSTED', 'PARTIAL', 'PAID', 'VOID']:
            raise ValidationError('Purchase lines cannot be deleted after the purchase has been posted.')
        return super().delete(*args, **kwargs)

class PurchasePayment(models.Model):
    purchase      = models.ForeignKey(Purchase, on_delete=models.PROTECT, related_name='payments')
    payment_date  = models.DateField()
    amount        = models.DecimalField(max_digits=12, decimal_places=2)
    journal_entry = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, related_name='purchase_payment')
    reference     = models.CharField(max_length=100, blank=True)
    created_at    = models.DateTimeField(auto_now_add=True)

    def clean(self):
        if self.amount <= 0:
            raise ValidationError('Payment amount must be greater than zero.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.purchase.supplier_name} - {self.amount}'

class Expense(models.Model):
    EXPENSE_STATUS  = [('DRAFT', 'Draft'), ('POSTED', 'Posted'), ('VOID', 'Void')]
    expense_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="expenses",
        limit_choices_to={"type": "EXPENSE"},
    )

    payment_account = models.ForeignKey(
        Account,
        on_delete=models.PROTECT,
        related_name="expense_payments",
    )
    expense_date    = models.DateField()
    description     = models.CharField(max_length=255)
    supplier_name   = models.CharField(max_length=150, blank=True)
    reference       = models.CharField(max_length=100, blank=True)
    status          = models.CharField(max_length=10, choices=EXPENSE_STATUS, default='DRAFT')
    journal_entry   = models.OneToOneField(JournalEntry, on_delete=models.PROTECT, null=True, blank=True, related_name='expense')

    def __str__(self):
        return f'{self.expense_date} - {self.description}'

    @property
    def total_net(self):
        return sum((line.net_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_vat(self):
        return sum((line.vat_amount for line in self.lines.all()), Decimal('0.00'))

    @property
    def total_gross(self):
        return self.total_net + self.total_vat

class ExpenseLineItem(models.Model):
    expense     = models.ForeignKey(Expense, on_delete=models.CASCADE, related_name='lines')
    description = models.CharField(max_length=255)
    quantity    = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price  = models.DecimalField(max_digits=12, decimal_places=2)
    vat_rate    = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal('0.00'))
    vat_amount  = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))

    @property
    def net_amount(self):
        return (self.quantity * self.unit_price).quantize(Decimal('0.01'))

    @property
    def gross_amount(self):
        return self.net_amount + self.vat_amount

    def clean(self):
        if self.quantity <= 0:
            raise ValidationError('Quantity must be greater than zero.')
        if self.unit_price < 0:
            raise ValidationError('Unit price cannot be negative.')
        if self.vat_rate < 0 or self.vat_rate > 100:
            raise ValidationError('VAT rate must be between 0 and 100.')
        if self.expense_id and self.expense.status in ['POSTED', 'VOID']:
            raise ValidationError('Expense lines cannot be changed after the expense has been posted.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.expense.status in ['POSTED', 'VOID']:
            raise ValidationError('Expense lines cannot be deleted after the expense has been posted.')
        return super().delete(*args, **kwargs)
"\nWhy no ExpensePayment?\n\nBecause an expense is already paid.\n\nThat's the key difference from Purchase.\n"

class PurchaseNumberSequence(models.Model):
    name        = models.CharField(max_length=20, unique=True)
    next_number = models.PositiveIntegerField(default=1)

    def __str__(self):
        return self.name
from django.db import models
from django.core.exceptions import ValidationError

class BusinessSettings(models.Model):
    ACCOUNTING_BASIS_CHOICES = [
        ('CASH', 'Cash Basis'),
        ('ACCRUAL', 'Traditional Accounting'),
    ]
    VAT_SCHEME_CHOICES = [
        ('STANDARD', 'Standard VAT'),
        ('CASH', 'VAT Cash Accounting'),
        ('FLAT_RATE', 'Flat Rate VAT'),
    ]

    business_name    = models.CharField(max_length=200, blank=True) 
    accounting_basis = models.CharField(max_length=20, choices=ACCOUNTING_BASIS_CHOICES, default='CASH') 
    vat_registered   = models.BooleanField(default=False) 
    vat_scheme       = models.CharField(max_length=20, choices=VAT_SCHEME_CHOICES, blank=True) 
    created_at       = models.DateTimeField(auto_now_add=True) 
    updated_at       = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Business Settings"
        verbose_name_plural = "Business Settings"

    def clean(self):
        if self.vat_registered and not self.vat_scheme:
            raise ValidationError( "Please select a VAT scheme." )

        if not self.vat_registered:
            self.vat_scheme = ''

    def __str__(self):
        return self.business_name or "Business Settings"

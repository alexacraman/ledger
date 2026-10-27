from django.conf import settings
from django.db import models
from django.db.models import Q
from django.core.exceptions import ValidationError


class Business(models.Model):
    owner       = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='businesses', )
    name        = models.CharField(max_length=200)
    is_active   = models.BooleanField(default=True)
    created_at  = models.DateTimeField(auto_now_add=True)
    updated_at  = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['name']
        constraints = [
            models.UniqueConstraint(
                fields=['owner', 'name'],
                name='unique_business_name_per_owner',
            )
        ]

    def __str__(self):
        return self.name


class AccountingBasisPeriod(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='accounting_basis_periods',
        null=True,
        blank=True,
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    accounting_basis = models.CharField(max_length=20, choices=[
        ('CASH', 'Cash Basis'),
        ('ACCRUAL', 'Traditional Accounting'),
    ])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['effective_from']

    def clean(self):
        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError('The end date cannot be before the start date.')

        overlap_qs = AccountingBasisPeriod.objects.filter(
            effective_from__lte=self.effective_to or self.effective_from,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=self.effective_from)
        )

        if self.pk:
            overlap_qs = overlap_qs.exclude(pk=self.pk)

        if overlap_qs.exists():
            raise ValidationError('Accounting basis periods cannot overlap.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.accounting_basis} from {self.effective_from}'


class VATRegistrationPeriod(models.Model):
    business = models.ForeignKey(
        Business,
        on_delete=models.CASCADE,
        related_name='vat_registration_periods',
        null=True,
        blank=True,
    )
    effective_from = models.DateField()
    effective_to = models.DateField(null=True, blank=True)
    vat_registered = models.BooleanField(default=False)
    vat_scheme = models.CharField(max_length=20, choices=[
        ('STANDARD', 'Standard VAT'),
        ('CASH', 'VAT Cash Accounting'),
        ('FLAT_RATE', 'Flat Rate VAT'),
    ], blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['effective_from']

    def clean(self):
        if self.vat_registered and not self.vat_scheme:
            raise ValidationError('Please select a VAT scheme.')

        if not self.vat_registered:
            self.vat_scheme = ''

        if self.effective_to and self.effective_to < self.effective_from:
            raise ValidationError('The end date cannot be before the start date.')

        overlap_qs = VATRegistrationPeriod.objects.filter(
            effective_from__lte=self.effective_to or self.effective_from,
        ).filter(
            Q(effective_to__isnull=True) | Q(effective_to__gte=self.effective_from)
        )

        if self.pk:
            overlap_qs = overlap_qs.exclude(pk=self.pk)

        if overlap_qs.exists():
            raise ValidationError('VAT registration periods cannot overlap.')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        status = 'VAT registered' if self.vat_registered else 'Not VAT registered'
        return f'{status} from {self.effective_from}'


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

    business = models.OneToOneField(
        Business,
        on_delete=models.CASCADE,
        related_name='settings',
        null=True,
        blank=True,
    )
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

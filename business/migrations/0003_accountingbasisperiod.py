from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0002_vatregistrationperiod'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountingBasisPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('accounting_basis', models.CharField(choices=[('CASH', 'Cash Basis'), ('ACCRUAL', 'Traditional Accounting')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['effective_from'],
            },
        ),
    ]

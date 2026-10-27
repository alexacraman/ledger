from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='VATRegistrationPeriod',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('effective_from', models.DateField()),
                ('effective_to', models.DateField(blank=True, null=True)),
                ('vat_registered', models.BooleanField(default=False)),
                ('vat_scheme', models.CharField(blank=True, choices=[('STANDARD', 'Standard VAT'), ('CASH', 'VAT Cash Accounting'), ('FLAT_RATE', 'Flat Rate VAT')], max_length=20)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['effective_from'],
            },
        ),
    ]

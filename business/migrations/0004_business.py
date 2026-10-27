from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('business', '0003_accountingbasisperiod'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Business',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='businesses', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['name'],
            },
        ),
        migrations.AddConstraint(
            model_name='business',
            constraint=models.UniqueConstraint(fields=('owner', 'name'), name='unique_business_name_per_owner'),
        ),
        migrations.AddField(
            model_name='accountingbasisperiod',
            name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='accounting_basis_periods', to='business.business'),
        ),
        migrations.AddField(
            model_name='vatregistrationperiod',
            name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='vat_registration_periods', to='business.business'),
        ),
        migrations.AddField(
            model_name='businesssettings',
            name='business',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='settings', to='business.business'),
        ),
    ]

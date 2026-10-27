from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0001_initial'),
        ('business', '0004_business'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='accounts', to='business.business'),
        ),
        migrations.AlterField(
            model_name='account',
            name='code',
            field=models.CharField(max_length=20),
        ),
        migrations.AlterField(
            model_name='account',
            name='name',
            field=models.CharField(max_length=100),
        ),
        migrations.AddConstraint(
            model_name='account',
            constraint=models.UniqueConstraint(fields=('business', 'code'), name='unique_account_code_per_business'),
        ),
        migrations.AddConstraint(
            model_name='account',
            constraint=models.UniqueConstraint(fields=('business', 'name'), name='unique_account_name_per_business'),
        ),
        migrations.AddField(
            model_name='accountingperiod',
            name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='accounting_periods', to='business.business'),
        ),
        migrations.AddField(
            model_name='journalentry',
            name='business',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='journal_entries', to='business.business'),
        ),
    ]

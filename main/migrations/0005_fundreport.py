import django.core.validators
import django.utils.timezone
import main.models
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('main', '0004_donationproof'),
    ]

    operations = [
        migrations.CreateModel(
            name='FundReport',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('report_type', models.CharField(choices=[('monthly', 'Monthly Report'), ('quarterly', 'Quarterly Report'), ('annual', 'Annual Report'), ('audit', 'Audit / Accounts'), ('other', 'Other')], db_index=True, default='monthly', max_length=20)),
                ('period_label', models.CharField(blank=True, default='', max_length=100)),
                ('description', models.TextField(blank=True, default='')),
                ('pdf', models.FileField(upload_to=main.models.fund_report_path, validators=[django.core.validators.FileExtensionValidator(['pdf'])])),
                ('report_date', models.DateField(default=django.utils.timezone.localdate)),
                ('is_published', models.BooleanField(default=True)),
                ('uploaded_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'ordering': ['-report_date', '-id'],
            },
        ),
    ]
# Migration for separated risk assessment fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0006_add_profit_growth'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockanalysis',
            name='is_market_high_risk',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='stockanalysis',
            name='stock_risk_level',
            field=models.CharField(default='Medium', max_length=20),
        ),
    ]

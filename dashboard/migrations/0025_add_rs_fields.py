"""
Migration: Add rs_label and rs_bonus fields to StockAnalysis
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0024_alter_stockanalysis_is_inverted_risk'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockanalysis',
            name='rs_label',
            field=models.CharField(default='NEUTRAL', max_length=20),
        ),
        migrations.AddField(
            model_name='stockanalysis',
            name='rs_bonus',
            field=models.IntegerField(default=0),
        ),
    ]

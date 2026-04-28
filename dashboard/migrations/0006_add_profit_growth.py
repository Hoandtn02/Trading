# Generated migration for adding profit_growth field
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0005_add_timeframe_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockdata',
            name='profit_growth',
            field=models.FloatField(null=True, blank=True),
        ),
    ]

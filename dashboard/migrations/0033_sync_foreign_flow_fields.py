from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0032_foreign_flow_upgrade'),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.AddField(
                    model_name='stockanalysis',
                    name='foreign_buy_val',
                    field=models.FloatField(default=0.0),
                ),
                migrations.AddField(
                    model_name='stockanalysis',
                    name='foreign_sell_val',
                    field=models.FloatField(default=0.0),
                ),
                migrations.AddField(
                    model_name='stockanalysis',
                    name='foreign_trading_share',
                    field=models.FloatField(default=0.0),
                ),
                migrations.AddField(
                    model_name='stockanalysis',
                    name='foreign_accumulated_trend',
                    field=models.CharField(default='NEUTRAL', max_length=20),
                ),
                migrations.AddField(
                    model_name='stockanalysis',
                    name='foreign_accumulated_slope',
                    field=models.FloatField(default=0.0),
                ),
            ],
            database_operations=[],
        ),
    ]

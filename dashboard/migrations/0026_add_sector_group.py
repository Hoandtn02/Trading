from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('dashboard', '0025_add_rs_fields'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockdata',
            name='sector_group',
            field=models.CharField(
                max_length=50,
                blank=True,
                default='',
                help_text='Nhóm ngành rộng: cyclical / banking / growth_defensive / general',
            ),
        ),
    ]

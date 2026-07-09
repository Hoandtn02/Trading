from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("dashboard", "0026_add_sector_group"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockanalysis",
            name="scan_mode",
            field=models.CharField(
                max_length=20,
                default="EARLY_TREND",
                help_text="Chế độ quét: BOTTOM_FISHING | EARLY_TREND",
            ),
        ),
    ]

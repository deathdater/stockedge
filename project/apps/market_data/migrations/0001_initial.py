from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="DailyCandle",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("symbol", models.CharField(db_index=True, max_length=32)),
                ("date", models.DateField(db_index=True)),
                ("open", models.DecimalField(decimal_places=8, max_digits=20)),
                ("high", models.DecimalField(decimal_places=8, max_digits=20)),
                ("low", models.DecimalField(decimal_places=8, max_digits=20)),
                ("close", models.DecimalField(decimal_places=8, max_digits=20)),
                ("volume", models.BigIntegerField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"unique_together": {("symbol", "date")}},
        ),
    ]

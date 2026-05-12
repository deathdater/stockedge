from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='DailyRanking',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField(db_index=True)),
                ('symbol', models.CharField(db_index=True, max_length=32)),
                ('rank', models.PositiveIntegerField()),
                ('score', models.FloatField()),
                ('inputs', models.JSONField(default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'unique_together': {('date', 'symbol')}},
        ),
        migrations.AddIndex(model_name='dailyranking', index=models.Index(fields=['date', 'rank'], name='rankings_da_date_4135db_idx')),
    ]

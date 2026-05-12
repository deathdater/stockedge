from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='DailyFeature',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(db_index=True, max_length=32)),
                ('date', models.DateField(db_index=True)),
                ('feature_set', models.CharField(default='baseline_v1', max_length=64)),
                ('values', models.JSONField(default=dict)),
                ('source_candle_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'unique_together': {('symbol', 'date', 'feature_set')}},
        ),
        migrations.AddIndex(model_name='dailyfeature', index=models.Index(fields=['feature_set', 'date'], name='features_dai_feature_f0ff17_idx')),
    ]

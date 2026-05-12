from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='PredictionLabel',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('symbol', models.CharField(db_index=True, max_length=32)),
                ('date', models.DateField(db_index=True)),
                ('horizon_days', models.PositiveSmallIntegerField(default=5)),
                ('label_set', models.CharField(default='future_return_v1', max_length=64)),
                ('future_return', models.FloatField()),
                ('direction', models.SmallIntegerField(help_text='-1 bearish, 0 neutral, 1 bullish')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={'unique_together': {('symbol', 'date', 'horizon_days', 'label_set')}},
        ),
        migrations.AddIndex(model_name='predictionlabel', index=models.Index(fields=['label_set', 'horizon_days', 'date'], name='labels_pred_label_s_0e2dc0_idx')),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name='ModelRun',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('model_family', models.CharField(db_index=True, max_length=32)),
                ('model_version', models.CharField(default='baseline_v1', max_length=64)),
                ('train_start', models.DateField()),
                ('train_end', models.DateField()),
                ('val_start', models.DateField()),
                ('val_end', models.DateField()),
                ('metrics', models.JSONField(default=dict)),
                ('artifact_uri', models.CharField(blank=True, max_length=255)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.AddIndex(model_name='modelrun', index=models.Index(fields=['model_family', 'created_at'], name='ml_models_m_model_f_80ae5f_idx')),
    ]

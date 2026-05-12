from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="IngestionRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("source", models.CharField(default="bhavcopy", max_length=64)),
                ("source_date", models.DateField(db_index=True)),
                ("status", models.CharField(choices=[("started", "Started"), ("success", "Success"), ("failed", "Failed")], default="started", max_length=16)),
                ("source_file_name", models.CharField(blank=True, max_length=255)),
                ("source_file_hash", models.CharField(blank=True, max_length=64)),
                ("rows_seen", models.PositiveIntegerField(default=0)),
                ("rows_valid", models.PositiveIntegerField(default=0)),
                ("rows_inserted", models.PositiveIntegerField(default=0)),
                ("rows_updated", models.PositiveIntegerField(default=0)),
                ("rows_invalid", models.PositiveIntegerField(default=0)),
                ("started_at", models.DateTimeField(auto_now_add=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("elapsed_ms", models.PositiveBigIntegerField(blank=True, null=True)),
                ("error_message", models.TextField(blank=True)),
                ("error_payload", models.JSONField(blank=True, default=dict)),
            ],
            options={
                "indexes": [models.Index(fields=["source", "source_date"], name="ingestion_i_source__9dd2f8_idx")],
            },
        )
    ]

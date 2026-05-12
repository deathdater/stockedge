from django.db import models


class IngestionRun(models.Model):
    class Status(models.TextChoices):
        STARTED = "started", "Started"
        SUCCESS = "success", "Success"
        FAILED = "failed", "Failed"
        SKIPPED = "skipped", "Skipped"

    source = models.CharField(max_length=64, default="bhavcopy")
    source_date = models.DateField(db_index=True)
    status = models.CharField(max_length=16, choices=Status.choices, default=Status.STARTED)

    source_file_name = models.CharField(max_length=255, blank=True)
    source_file_hash = models.CharField(max_length=64, blank=True)

    rows_seen = models.PositiveIntegerField(default=0)
    rows_valid = models.PositiveIntegerField(default=0)
    rows_inserted = models.PositiveIntegerField(default=0)
    rows_updated = models.PositiveIntegerField(default=0)
    rows_invalid = models.PositiveIntegerField(default=0)

    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    elapsed_ms = models.PositiveBigIntegerField(null=True, blank=True)

    error_message = models.TextField(blank=True)
    error_payload = models.JSONField(default=dict, blank=True)

    class Meta:
        indexes = [models.Index(fields=["source", "source_date"])]

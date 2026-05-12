from django.db import models


class ModelRun(models.Model):
    model_family = models.CharField(max_length=32, db_index=True)
    model_version = models.CharField(max_length=64, default="baseline_v1")
    train_start = models.DateField()
    train_end = models.DateField()
    val_start = models.DateField()
    val_end = models.DateField()
    metrics = models.JSONField(default=dict)
    artifact_uri = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["model_family", "created_at"])]

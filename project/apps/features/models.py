from django.db import models


class DailyFeature(models.Model):
    symbol = models.CharField(max_length=32, db_index=True)
    date = models.DateField(db_index=True)
    feature_set = models.CharField(max_length=64, default="baseline_v1")
    values = models.JSONField(default=dict)
    source_candle_count = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("symbol", "date", "feature_set")
        indexes = [models.Index(fields=["feature_set", "date"])]

from django.db import models


class PredictionLabel(models.Model):
    symbol = models.CharField(max_length=32, db_index=True)
    date = models.DateField(db_index=True)
    horizon_days = models.PositiveSmallIntegerField(default=5)
    label_set = models.CharField(max_length=64, default="future_return_v1")
    future_return = models.FloatField()
    direction = models.SmallIntegerField(help_text="-1 bearish, 0 neutral, 1 bullish")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("symbol", "date", "horizon_days", "label_set")
        indexes = [models.Index(fields=["label_set", "horizon_days", "date"])]

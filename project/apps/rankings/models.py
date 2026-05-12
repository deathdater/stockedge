from django.db import models


class DailyRanking(models.Model):
    date = models.DateField(db_index=True)
    symbol = models.CharField(max_length=32, db_index=True)
    rank = models.PositiveIntegerField()
    score = models.FloatField()
    inputs = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("date", "symbol")
        indexes = [models.Index(fields=["date", "rank"])]

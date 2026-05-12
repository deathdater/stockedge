from django.core.exceptions import ValidationError
from django.db import models


class DailyCandle(models.Model):
    symbol = models.CharField(max_length=32, db_index=True)
    date = models.DateField(db_index=True)

    open = models.DecimalField(max_digits=20, decimal_places=8)
    high = models.DecimalField(max_digits=20, decimal_places=8)
    low = models.DecimalField(max_digits=20, decimal_places=8)
    close = models.DecimalField(max_digits=20, decimal_places=8)

    volume = models.BigIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("symbol", "date")

    def clean(self):
        super().clean()

        errors = {}

        if self.high is not None and self.low is not None and self.high < self.low:
            errors["high"] = "high must be greater than or equal to low."

        if self.open is not None and self.low is not None and self.open < self.low:
            errors["open"] = "open must be between low and high."
        if self.open is not None and self.high is not None and self.open > self.high:
            errors["open"] = "open must be between low and high."

        if self.close is not None and self.low is not None and self.close < self.low:
            errors["close"] = "close must be between low and high."
        if self.close is not None and self.high is not None and self.close > self.high:
            errors["close"] = "close must be between low and high."

        if self.volume is not None and self.volume < 0:
            errors["volume"] = "volume must be greater than or equal to 0."

        if errors:
            raise ValidationError(errors)

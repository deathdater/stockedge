from datetime import date
from decimal import Decimal, InvalidOperation


class DataValidator:
    REQUIRED = ["SYMBOL", "OPEN_PRICE", "HIGH_PRICE", "LOW_PRICE", "CLOSE_PRICE", "NET_TRDQTY"]

    @classmethod
    def parse_row(cls, row: dict, trade_date: date) -> dict:
        missing = [key for key in cls.REQUIRED if str(row.get(key, "")).strip() == ""]
        if missing:
            raise ValueError(f"missing columns: {missing}")

        symbol = str(row["SYMBOL"]).strip().upper()

        try:
            open_p = Decimal(str(row["OPEN_PRICE"]).strip() or "0")
            high_p = Decimal(str(row["HIGH_PRICE"]).strip() or "0")
            low_p = Decimal(str(row["LOW_PRICE"]).strip() or "0")
            close_p = Decimal(str(row["CLOSE_PRICE"]).strip() or "0")
            volume = int(Decimal(str(row["NET_TRDQTY"]).strip() or "0"))
        except (InvalidOperation, ValueError) as exc:
            raise ValueError(f"numeric parse failed: {exc}") from exc

        if high_p < low_p:
            raise ValueError("high < low")
        if not (low_p <= open_p <= high_p):
            raise ValueError("open outside [low, high]")
        if not (low_p <= close_p <= high_p):
            raise ValueError("close outside [low, high]")
        if volume < 0:
            raise ValueError("negative volume")

        return {
            "symbol": symbol,
            "date": trade_date,
            "open": open_p,
            "high": high_p,
            "low": low_p,
            "close": close_p,
            "volume": volume,
        }

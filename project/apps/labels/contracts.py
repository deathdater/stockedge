from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class LabelInputRow:
    symbol: str
    date: date
    close: float


@dataclass(slots=True)
class LabelOutputRow:
    symbol: str
    date: date
    horizon_days: int
    future_return: float
    direction: int

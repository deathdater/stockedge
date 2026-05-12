from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class FeatureInputRow:
    symbol: str
    date: date
    close: float
    volume: float


@dataclass(slots=True)
class FeatureOutputRow:
    symbol: str
    date: date
    feature_set: str
    values: dict[str, float]

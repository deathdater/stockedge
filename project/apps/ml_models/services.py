from dataclasses import dataclass
from datetime import date


@dataclass(slots=True)
class WalkForwardFold:
    train_start: date
    train_end: date
    val_start: date
    val_end: date


def make_walk_forward_folds(dates: list[date], train_size: int = 252, val_size: int = 21, step: int = 21) -> list[WalkForwardFold]:
    ordered = sorted(set(dates))
    folds: list[WalkForwardFold] = []
    i = train_size
    while i + val_size <= len(ordered):
        folds.append(
            WalkForwardFold(
                train_start=ordered[i - train_size],
                train_end=ordered[i - 1],
                val_start=ordered[i],
                val_end=ordered[i + val_size - 1],
            )
        )
        i += step
    return folds


def train_specialized_models(feature_rows: list[dict], label_rows: list[dict]) -> dict[str, dict]:
    """Baseline training stub for Trend/Volatility/Risk/Confidence."""
    families = ["trend", "volatility", "risk", "confidence"]
    size = min(len(feature_rows), len(label_rows))
    return {f: {"samples": size, "status": "trained", "metric_placeholder": 0.0} for f in families}

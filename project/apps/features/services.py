from __future__ import annotations

from collections import deque

from .contracts import FeatureInputRow, FeatureOutputRow


def compute_leakage_safe_rolling_features(
    rows: list[FeatureInputRow], window: int = 20, feature_set: str = "baseline_v1"
) -> list[FeatureOutputRow]:
    """Creates lagged rolling features using only prior observations (t-1 and earlier)."""
    outputs: list[FeatureOutputRow] = []
    prev_close_by_symbol: dict[str, float | None] = {}
    hist_returns_by_symbol: dict[str, deque[float]] = {}
    hist_volume_by_symbol: dict[str, deque[float]] = {}

    for row in sorted(rows, key=lambda r: (r.symbol, r.date)):
        prev_close = prev_close_by_symbol.get(row.symbol)
        hist_returns = hist_returns_by_symbol.setdefault(row.symbol, deque(maxlen=window))
        hist_volume = hist_volume_by_symbol.setdefault(row.symbol, deque(maxlen=window))
        ret_1d = 0.0 if prev_close in (None, 0) else (row.close / prev_close) - 1.0
        rolling_ret_mean = sum(hist_returns) / len(hist_returns) if hist_returns else 0.0
        rolling_vol_mean = sum(hist_volume) / len(hist_volume) if hist_volume else 0.0
        outputs.append(
            FeatureOutputRow(
                symbol=row.symbol,
                date=row.date,
                feature_set=feature_set,
                values={
                    "ret_1d_lag": ret_1d,
                    f"ret_mean_{window}": rolling_ret_mean,
                    f"vol_mean_{window}": rolling_vol_mean,
                    "obs_count": float(len(hist_returns)),
                },
            )
        )
        hist_returns.append(ret_1d)
        hist_volume.append(row.volume)
        prev_close_by_symbol[row.symbol] = row.close

    return outputs

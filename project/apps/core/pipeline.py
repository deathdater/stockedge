"""Daily ranking pipeline — uses ML models when available, falls back to heuristics."""

from __future__ import annotations

import logging
from datetime import date

import numpy as np

from project.apps.ensemble.services import score_with_models, weighted_ensemble_score
from project.apps.market_data.models import DailyCandle
from project.apps.rankings.services import persist_top_n_rankings

logger = logging.getLogger(__name__)


def run_daily_ranking_pipeline(run_date: date | None = None, top_n: int = 25) -> dict:
    run_date = run_date or date.today()

    # Try ML-powered scoring first
    ml_result = _try_ml_scoring(run_date, top_n)
    if ml_result is not None:
        return ml_result

    # Fallback to heuristic scoring
    return _heuristic_scoring(run_date, top_n)


def _try_ml_scoring(run_date: date, top_n: int) -> dict | None:
    """Attempt to score using trained ML models. Returns None if models aren't available."""
    from project.apps.features.models import DailyFeature
    from project.apps.ml_models.services import MODEL_FAMILIES, load_latest_model, predict_scores

    features_qs = DailyFeature.objects.filter(date=run_date, feature_set="baseline_v1")
    if not features_qs.exists():
        return None

    # Load models
    model_bundles = {}
    for family in MODEL_FAMILIES:
        bundle = load_latest_model(family)
        if bundle:
            model_bundles[family] = bundle

    if not model_bundles:
        return None

    # Build feature matrix
    symbols = []
    feature_rows = []
    feature_names = None
    for feat in features_qs.values("symbol", "values"):
        vals = feat["values"]
        if feature_names is None:
            feature_names = sorted(vals.keys())
        feature_rows.append([vals.get(fn, 0.0) for fn in feature_names])
        symbols.append(feat["symbol"])

    if not feature_rows:
        return None

    X = np.array(feature_rows, dtype=np.float64)
    scores = score_with_models(X, model_bundles)

    scored_rows = []
    for i, symbol in enumerate(symbols):
        inputs = {}
        for family, bundle in model_bundles.items():
            probs = predict_scores(X[i : i + 1], bundle)
            inputs[family] = round(float(probs[0]), 4)
        scored_rows.append({"symbol": symbol, "score": round(float(scores[i]), 6), "inputs": inputs})

    persisted = persist_top_n_rankings(scored_rows=scored_rows, date=run_date, top_n=top_n)
    logger.info("pipeline.ml_scoring: date=%s processed=%d ranked=%d", run_date, len(symbols), len(persisted))
    return {"date": run_date.isoformat(), "processed": len(symbols), "ranked": len(persisted), "mode": "ml"}


def _heuristic_scoring(run_date: date, top_n: int) -> dict:
    """Original heuristic scoring based on daily candle data."""
    candles = list(DailyCandle.objects.filter(date=run_date).only("symbol", "open", "close", "high", "low", "volume"))
    scored_rows: list[dict] = []

    for candle in candles:
        if candle.open == 0:
            continue
        trend = float((candle.close / candle.open) - 1)
        volatility = float((candle.high - candle.low) / candle.open)
        confidence = min(1.0, float(candle.volume) / 1_000_000)
        risk = abs(volatility) * 0.5
        score = weighted_ensemble_score(trend=trend, confidence=confidence, volatility=1 - volatility, risk=risk)
        scored_rows.append(
            {
                "symbol": candle.symbol,
                "score": score,
                "inputs": {
                    "trend": trend,
                    "volatility": volatility,
                    "confidence": confidence,
                    "risk": risk,
                },
            }
        )

    persisted = persist_top_n_rankings(scored_rows=scored_rows, date=run_date, top_n=top_n) if scored_rows else []
    logger.info("pipeline.heuristic_scoring: date=%s processed=%d ranked=%d", run_date, len(candles), len(persisted))
    return {"date": run_date.isoformat(), "processed": len(candles), "ranked": len(persisted), "mode": "heuristic"}

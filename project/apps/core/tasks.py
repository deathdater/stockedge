"""Core ML pipeline tasks — each is idempotent and additive (skips already-done work)."""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

import numpy as np
from celery import chain, shared_task
from django.utils import timezone

logger = logging.getLogger(__name__)

FEATURE_SET = "baseline_v1"
LABEL_SET = "future_return_v1"
MODEL_VERSION = "baseline_v1"
HORIZON_DAYS = 5
LOOKBACK_DAYS = 30


def _parse_run_date(payload: dict | str | None) -> date:
    """Extract run_date from a payload dict, ISO string, or default to today."""
    if payload is None:
        return timezone.now().date()
    if isinstance(payload, str):
        try:
            return datetime.strptime(payload, "%Y-%m-%d").date()
        except ValueError:
            return timezone.now().date()
    if isinstance(payload, dict):
        raw = payload.get("date") or payload.get("run_date")
        if raw:
            try:
                return datetime.strptime(str(raw), "%Y-%m-%d").date()
            except ValueError:
                pass
    return timezone.now().date()


@shared_task
def compute_features(payload: dict | None = None) -> dict:
    """Compute rolling features for a date range. Skips symbols+dates already computed."""
    from project.apps.features.contracts import FeatureInputRow
    from project.apps.features.models import DailyFeature
    from project.apps.features.services import compute_leakage_safe_rolling_features
    from project.apps.market_data.models import DailyCandle

    run_date = _parse_run_date(payload)
    window_start = run_date - timedelta(days=LOOKBACK_DAYS + 30)  # Extra days for rolling window warmup

    # Fetch candles for the window
    candles = list(
        DailyCandle.objects.filter(date__range=(window_start, run_date))
        .order_by("symbol", "date")
        .values("symbol", "date", "close", "volume")
    )
    if not candles:
        logger.info("compute_features: no candles for %s", run_date)
        return {"date": run_date.isoformat(), "symbols_processed": 0, "features_created": 0, "skipped": 0}

    # Find which (symbol, date) combos already have features
    existing = set(
        DailyFeature.objects.filter(
            date__range=(window_start, run_date),
            feature_set=FEATURE_SET,
        ).values_list("symbol", "date")
    )

    rows = [
        FeatureInputRow(
            symbol=c["symbol"],
            date=c["date"],
            close=float(c["close"]),
            volume=float(c["volume"]),
        )
        for c in candles
    ]

    outputs = compute_leakage_safe_rolling_features(rows, feature_set=FEATURE_SET)

    # Only insert features that don't already exist
    created = 0
    skipped = 0
    for out in outputs:
        if (out.symbol, out.date) in existing:
            skipped += 1
            continue

        DailyFeature.objects.update_or_create(
            symbol=out.symbol,
            date=out.date,
            feature_set=out.feature_set,
            defaults={
                "values": out.values,
                "source_candle_count": len([r for r in rows if r.symbol == out.symbol and r.date <= out.date]),
            },
        )
        created += 1

    symbols = len(set(c["symbol"] for c in candles))
    logger.info("compute_features: date=%s symbols=%d created=%d skipped=%d", run_date, symbols, created, skipped)
    return {"date": run_date.isoformat(), "symbols_processed": symbols, "features_created": created, "skipped": skipped}


@shared_task
def generate_labels(payload: dict | None = None) -> dict:
    """Generate future-return labels. Skips (symbol, date, horizon) already labeled."""
    from project.apps.labels.contracts import LabelInputRow
    from project.apps.labels.models import PredictionLabel
    from project.apps.labels.services import build_future_return_labels
    from project.apps.market_data.models import DailyCandle

    run_date = _parse_run_date(payload)
    window_start = run_date - timedelta(days=LOOKBACK_DAYS + 30)
    window_end = run_date + timedelta(days=HORIZON_DAYS + 5)  # Need future data for labels

    candles = list(
        DailyCandle.objects.filter(date__range=(window_start, window_end))
        .order_by("symbol", "date")
        .values("symbol", "date", "close")
    )
    if not candles:
        logger.info("generate_labels: no candles for %s", run_date)
        return {"date": run_date.isoformat(), "labels_created": 0, "skipped": 0}

    existing = set(
        PredictionLabel.objects.filter(
            date__range=(window_start, run_date),
            horizon_days=HORIZON_DAYS,
            label_set=LABEL_SET,
        ).values_list("symbol", "date")
    )

    rows = [LabelInputRow(symbol=c["symbol"], date=c["date"], close=float(c["close"])) for c in candles]
    outputs = build_future_return_labels(rows, horizon_days=HORIZON_DAYS)

    created = 0
    skipped = 0
    for out in outputs:
        if out.date > run_date:
            continue  # Don't create labels for future dates beyond run_date
        if (out.symbol, out.date) in existing:
            skipped += 1
            continue

        PredictionLabel.objects.update_or_create(
            symbol=out.symbol,
            date=out.date,
            horizon_days=out.horizon_days,
            label_set=LABEL_SET,
            defaults={
                "future_return": out.future_return,
                "direction": out.direction,
            },
        )
        created += 1

    logger.info("generate_labels: date=%s created=%d skipped=%d", run_date, created, skipped)
    return {"date": run_date.isoformat(), "labels_created": created, "skipped": skipped}


@shared_task
def train_models(payload: dict | None = None) -> dict:
    """Train specialized models using walk-forward folds. Skips if models already exist for run_date."""
    from project.apps.features.models import DailyFeature
    from project.apps.labels.models import PredictionLabel
    from project.apps.ml_models.models import ModelRun
    from project.apps.ml_models.services import (
        MODEL_FAMILIES,
        make_walk_forward_folds,
        train_specialized_models,
    )

    run_date = _parse_run_date(payload)

    # Check if models already exist for this date
    existing_runs = ModelRun.objects.filter(
        model_version=MODEL_VERSION,
        val_end=run_date,
    ).count()
    if existing_runs >= len(MODEL_FAMILIES):
        logger.info("train_models: models already exist for %s, skipping", run_date)
        return {"date": run_date.isoformat(), "status": "skipped", "reason": "already_trained"}

    # Load features and labels, join on (symbol, date)
    features_qs = DailyFeature.objects.filter(feature_set=FEATURE_SET).order_by("date")
    labels_qs = PredictionLabel.objects.filter(
        label_set=LABEL_SET,
        horizon_days=HORIZON_DAYS,
        date__lte=run_date,
    )

    # Build lookup of labels
    label_lookup: dict[tuple[str, date], float] = {}
    for lab in labels_qs.values("symbol", "date", "future_return"):
        label_lookup[(lab["symbol"], lab["date"])] = lab["future_return"]

    # Build aligned feature matrix and label vector
    feature_names: list[str] | None = None
    feature_rows = []
    label_values = []
    all_dates: list[date] = []

    for feat in features_qs.values("symbol", "date", "values"):
        key = (feat["symbol"], feat["date"])
        if key not in label_lookup:
            continue
        vals = feat["values"]
        if feature_names is None:
            feature_names = sorted(vals.keys())
        feature_rows.append([vals.get(fn, 0.0) for fn in feature_names])
        label_values.append(label_lookup[key])
        all_dates.append(feat["date"])

    if not feature_rows or not feature_names:
        logger.warning("train_models: insufficient data for %s", run_date)
        return {"date": run_date.isoformat(), "status": "insufficient_data", "samples": len(feature_rows)}

    X = np.array(feature_rows, dtype=np.float64)
    y = np.array(label_values, dtype=np.float64)

    # Use walk-forward folds to identify train/val split
    folds = make_walk_forward_folds(all_dates, train_size=min(252, len(all_dates) // 2))
    if not folds:
        # Not enough data for walk-forward — train on all available data
        logger.info("train_models: not enough data for walk-forward, training on all %d rows", len(X))
        fold_train_end = run_date
        fold_val_start = run_date
        fold_val_end = run_date
        fold_train_start = all_dates[0] if all_dates else run_date
    else:
        latest_fold = folds[-1]
        fold_train_start = latest_fold.train_start
        fold_train_end = latest_fold.train_end
        fold_val_start = latest_fold.val_start
        fold_val_end = latest_fold.val_end

    # Train models
    results = train_specialized_models(
        feature_matrix=X,
        label_vector=y,
        feature_names=feature_names,
        version=MODEL_VERSION,
        run_date=run_date,
    )

    # Persist ModelRun records
    for family, metrics in results.items():
        if metrics.get("status") == "skipped":
            continue
        ModelRun.objects.update_or_create(
            model_family=family,
            model_version=MODEL_VERSION,
            train_start=fold_train_start,
            train_end=fold_train_end,
            val_start=fold_val_start,
            val_end=fold_val_end,
            defaults={
                "metrics": metrics,
                "artifact_uri": metrics.get("artifact_uri", ""),
            },
        )

    logger.info("train_models: date=%s families=%s samples=%d", run_date, list(results.keys()), len(X))
    return {"date": run_date.isoformat(), "models_trained": len(results), "samples": len(X), "metrics": results}


@shared_task
def generate_rankings(payload: dict | None = None) -> dict:
    """Score symbols using trained models and persist top rankings. Skips if rankings exist for date."""
    from project.apps.features.models import DailyFeature
    from project.apps.ml_models.services import MODEL_FAMILIES, load_latest_model
    from project.apps.rankings.models import DailyRanking
    from project.apps.rankings.services import persist_top_n_rankings

    run_date = _parse_run_date(payload)

    # Check if rankings already exist
    existing = DailyRanking.objects.filter(date=run_date).count()
    if existing > 0:
        logger.info("generate_rankings: rankings already exist for %s (%d), skipping", run_date, existing)
        return {"date": run_date.isoformat(), "status": "skipped", "existing_count": existing}

    # Load today's features
    features_qs = DailyFeature.objects.filter(date=run_date, feature_set=FEATURE_SET)
    if not features_qs.exists():
        logger.info("generate_rankings: no features for %s", run_date)
        return {"date": run_date.isoformat(), "ranked_count": 0, "reason": "no_features"}

    # Load all model bundles
    model_bundles = {}
    for family in MODEL_FAMILIES:
        bundle = load_latest_model(family, MODEL_VERSION)
        if bundle:
            model_bundles[family] = bundle

    if not model_bundles:
        # Fallback: use heuristic scoring from pipeline.py
        logger.info("generate_rankings: no trained models, falling back to heuristic")
        from project.apps.core.pipeline import run_daily_ranking_pipeline

        result = run_daily_ranking_pipeline(run_date=run_date)
        return {**result, "mode": "heuristic_fallback"}

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
        return {"date": run_date.isoformat(), "ranked_count": 0}

    X = np.array(feature_rows, dtype=np.float64)

    # Score using ensemble
    from project.apps.ensemble.services import score_with_models

    scores = score_with_models(X, model_bundles)

    # Build scored rows
    scored_rows = []
    for i, symbol in enumerate(symbols):
        # Get individual family scores for the inputs field
        inputs = {}
        for family, bundle in model_bundles.items():
            from project.apps.ml_models.services import predict_scores

            probs = predict_scores(X[i : i + 1], bundle)
            inputs[family] = round(float(probs[0]), 4)

        scored_rows.append({"symbol": symbol, "score": round(float(scores[i]), 6), "inputs": inputs})

    persisted = persist_top_n_rankings(scored_rows=scored_rows, date=run_date, top_n=25)
    logger.info("generate_rankings: date=%s ranked=%d mode=ml", run_date, len(persisted))
    return {"date": run_date.isoformat(), "ranked_count": len(persisted), "mode": "ml"}


@shared_task
def run_backtests(payload: dict | None = None) -> dict:
    """Run backtest on recent rankings. Gracefully skips if vectorbt not installed."""
    run_date = _parse_run_date(payload)

    try:
        from project.apps.backtesting.services import BacktestConfig, run_vectorbt_backtest
    except ImportError:
        logger.info("run_backtests: vectorbt not installed, skipping")
        return {"date": run_date.isoformat(), "status": "skipped", "reason": "vectorbt_not_installed"}

    try:
        import pandas as pd

        from project.apps.market_data.models import DailyCandle
        from project.apps.rankings.models import DailyRanking

        # Get top-ranked symbols
        top_symbols = list(
            DailyRanking.objects.filter(date=run_date, rank__lte=10).values_list("symbol", flat=True)
        )
        if not top_symbols:
            return {"date": run_date.isoformat(), "status": "no_rankings"}

        # Fetch price history for these symbols (last 252 trading days)
        lookback = run_date - timedelta(days=365)
        candles = (
            DailyCandle.objects.filter(symbol__in=top_symbols, date__range=(lookback, run_date))
            .order_by("date")
            .values("symbol", "date", "close")
        )

        # Pivot to price series
        df = pd.DataFrame(list(candles))
        if df.empty:
            return {"date": run_date.isoformat(), "status": "insufficient_price_data"}

        pivot = df.pivot(index="date", columns="symbol", values="close").ffill()
        entry_signals = pd.DataFrame(True, index=pivot.index[-1:], columns=pivot.columns)
        exit_signals = pd.DataFrame(False, index=pivot.index, columns=pivot.columns)

        config = BacktestConfig()
        portfolio = run_vectorbt_backtest(pivot, entry_signals, exit_signals, config)

        stats = {
            "sharpe": round(float(portfolio.sharpe_ratio()), 4),
            "total_return": round(float(portfolio.total_return()), 4),
            "max_drawdown": round(float(portfolio.max_drawdown()), 4),
        }
        logger.info("run_backtests: date=%s stats=%s", run_date, stats)
        return {"date": run_date.isoformat(), "status": "completed", "stats": stats}

    except Exception as exc:
        logger.warning("run_backtests: failed — %s", exc)
        return {"date": run_date.isoformat(), "status": "failed", "error": str(exc)}


@shared_task
def monitor_drift(payload: dict | None = None) -> dict:
    """Check feature drift between training data and recent live data."""
    from project.apps.features.models import DailyFeature
    from project.apps.monitoring.services import compute_feature_drift, emit_monitoring_report

    run_date = _parse_run_date(payload)

    # Get training-period features (older data)
    train_end = run_date - timedelta(days=30)
    train_start = train_end - timedelta(days=252)
    train_features = list(
        DailyFeature.objects.filter(
            date__range=(train_start, train_end),
            feature_set=FEATURE_SET,
        ).values("values")
    )

    # Get recent live features
    live_start = run_date - timedelta(days=5)
    live_features = list(
        DailyFeature.objects.filter(
            date__range=(live_start, run_date),
            feature_set=FEATURE_SET,
        ).values("values")
    )

    if not train_features or not live_features:
        logger.info("monitor_drift: insufficient data for drift check on %s", run_date)
        return {"date": run_date.isoformat(), "status": "insufficient_data"}

    # Build numpy arrays
    feature_names = sorted(train_features[0]["values"].keys())
    train_matrix = np.array([[f["values"].get(fn, 0.0) for fn in feature_names] for f in train_features])
    live_matrix = np.array([[f["values"].get(fn, 0.0) for fn in feature_names] for f in live_features])

    result = compute_feature_drift(train_matrix, live_matrix, feature_names)
    emit_monitoring_report(result)

    logger.info(
        "monitor_drift: date=%s drift=%s features_drifted=%s",
        run_date,
        result["drift_detected"],
        result.get("features_drifted", []),
    )
    return {"date": run_date.isoformat(), **result}


def build_daily_ml_chain(run_date: str):
    """Build the full daily ML pipeline chain for a given date.

    Each task receives and passes a payload dict with run_date,
    allowing the chain to be invoked for any date.
    """
    payload = {"date": run_date}
    return chain(
        compute_features.si(payload),
        generate_labels.si(payload),
        train_models.si(payload),
        generate_rankings.si(payload),
        run_backtests.si(payload),
        monitor_drift.si(payload),
    )

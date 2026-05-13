"""Monitoring — feature drift detection and reporting hooks."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)


def detect_simple_drift(reference_mean: float, live_mean: float, threshold: float = 0.15) -> dict:
    if reference_mean == 0:
        delta = 0.0
    else:
        delta = abs(live_mean - reference_mean) / abs(reference_mean)
    return {"delta": delta, "drift": delta > threshold}


def compute_feature_drift(
    train_features: np.ndarray,
    live_features: np.ndarray,
    feature_names: list[str],
    threshold: float = 0.15,
) -> dict:
    """Compare feature distributions between training and live data.

    Returns a summary of which features drifted beyond the threshold.
    """
    drifted: list[str] = []
    details: dict[str, dict] = {}

    for i, name in enumerate(feature_names):
        ref_mean = float(np.mean(train_features[:, i])) if train_features.shape[0] > 0 else 0.0
        live_mean = float(np.mean(live_features[:, i])) if live_features.shape[0] > 0 else 0.0
        result = detect_simple_drift(ref_mean, live_mean, threshold)
        details[name] = {
            "ref_mean": round(ref_mean, 6),
            "live_mean": round(live_mean, 6),
            **result,
        }
        if result["drift"]:
            drifted.append(name)

    return {
        "drift_detected": len(drifted) > 0,
        "features_drifted": drifted,
        "total_features": len(feature_names),
        "details": details,
    }


def emit_monitoring_report(payload: dict) -> None:
    """Hook for external observability integration (Sentry/DataDog/Prometheus)."""
    if payload.get("drift_detected"):
        logger.warning("monitoring.drift_detected", extra={"event": "monitoring.drift_detected", **payload})
    else:
        logger.info("monitoring.no_drift", extra={"event": "monitoring.no_drift"})

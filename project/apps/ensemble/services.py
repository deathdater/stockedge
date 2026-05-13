"""Ensemble scoring — combines model family predictions into a single score."""

from __future__ import annotations

import logging

import numpy as np

logger = logging.getLogger(__name__)

# Default weights for each model family in the ensemble
DEFAULT_WEIGHTS = {
    "trend": 0.40,
    "confidence": 0.25,
    "volatility": 0.20,
    "risk": 0.15,
}


def weighted_ensemble_score(trend: float, confidence: float, volatility: float, risk: float) -> float:
    return (trend * confidence * volatility) - risk


def score_with_models(
    features: np.ndarray,
    model_bundles: dict[str, dict],
    weights: dict[str, float] | None = None,
) -> np.ndarray:
    """Run inference on all available model families and produce a weighted ensemble score per row.

    Returns an array of composite scores, one per feature row.
    """
    weights = weights or DEFAULT_WEIGHTS
    n_rows = features.shape[0]
    composite = np.zeros(n_rows)
    total_weight = 0.0

    for family, bundle in model_bundles.items():
        if bundle is None:
            continue
        w = weights.get(family, 0.0)
        if w == 0:
            continue

        from project.apps.ml_models.services import predict_scores

        probs = predict_scores(features, bundle)

        if family == "risk":
            # Higher risk probability → lower score (invert)
            composite -= w * probs
        else:
            # Higher probability → higher score
            composite += w * probs
        total_weight += w

    if total_weight > 0:
        composite /= total_weight

    return composite

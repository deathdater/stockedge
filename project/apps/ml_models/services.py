"""ML model training, persistence, and walk-forward fold utilities."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import date
from pathlib import Path

import joblib
import numpy as np
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import accuracy_score, f1_score
from sklearn.preprocessing import StandardScaler

logger = logging.getLogger(__name__)

MODELS_DIR = Path("/app/models_store")

MODEL_FAMILIES = ("trend", "volatility", "risk", "confidence")


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


def _derive_target(labels: np.ndarray, family: str) -> np.ndarray:
    """Derive binary classification target from continuous future returns per model family."""
    if family == "trend":
        # 1 = bullish (positive return), 0 = bearish
        return (labels > 0).astype(int)
    elif family == "volatility":
        # 1 = high volatility (abs return > median), 0 = low
        median = np.median(np.abs(labels))
        return (np.abs(labels) > median).astype(int)
    elif family == "risk":
        # 1 = risky (negative return below -2%), 0 = ok
        return (labels < -0.02).astype(int)
    elif family == "confidence":
        # 1 = high confidence (abs return > 1%), 0 = ambiguous
        return (np.abs(labels) > 0.01).astype(int)
    else:
        return (labels > 0).astype(int)


def train_specialized_models(
    feature_matrix: np.ndarray,
    label_vector: np.ndarray,
    feature_names: list[str],
    version: str = "baseline_v1",
    run_date: date | None = None,
) -> dict[str, dict]:
    """Train a GradientBoostingClassifier for each model family and save artifacts."""
    run_date = run_date or date.today()
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    results: dict[str, dict] = {}

    for family in MODEL_FAMILIES:
        y = _derive_target(label_vector, family)

        # Need at least 2 classes to train
        if len(np.unique(y)) < 2:
            logger.warning("Skipping %s — only one class in target", family)
            results[family] = {"status": "skipped", "reason": "single_class"}
            continue

        scaler = StandardScaler()
        X_scaled = scaler.fit_transform(feature_matrix)

        clf = GradientBoostingClassifier(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            subsample=0.8,
            random_state=42,
        )
        clf.fit(X_scaled, y)
        y_pred = clf.predict(X_scaled)

        metrics = {
            "accuracy": round(accuracy_score(y, y_pred), 4),
            "f1": round(f1_score(y, y_pred, zero_division=0), 4),
            "samples": int(len(y)),
            "pos_ratio": round(float(y.mean()), 4),
        }

        # Save model + scaler as a bundle
        artifact_path = MODELS_DIR / f"{family}_{version}_{run_date.isoformat()}.joblib"
        bundle = {
            "model": clf,
            "scaler": scaler,
            "feature_names": feature_names,
            "family": family,
            "version": version,
            "train_date": run_date.isoformat(),
            "metrics": metrics,
        }
        joblib.dump(bundle, artifact_path)
        logger.info("Saved model %s to %s", family, artifact_path)

        results[family] = {
            "status": "trained",
            "artifact_uri": str(artifact_path),
            **metrics,
        }

    return results


def load_latest_model(family: str, version: str = "baseline_v1") -> dict | None:
    """Load the most recently trained model bundle for a given family."""
    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    pattern = f"{family}_{version}_*.joblib"
    candidates = sorted(MODELS_DIR.glob(pattern), reverse=True)
    if not candidates:
        return None
    return joblib.load(candidates[0])


def predict_scores(features: np.ndarray, model_bundle: dict) -> np.ndarray:
    """Run inference using a loaded model bundle. Returns predicted probabilities."""
    scaler = model_bundle["scaler"]
    clf = model_bundle["model"]
    X_scaled = scaler.transform(features)
    # Return probability of positive class
    return clf.predict_proba(X_scaled)[:, 1]

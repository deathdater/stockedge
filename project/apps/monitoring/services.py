def detect_simple_drift(reference_mean: float, live_mean: float, threshold: float = 0.15) -> dict:
    if reference_mean == 0:
        delta = 0.0
    else:
        delta = abs(live_mean - reference_mean) / abs(reference_mean)
    return {"delta": delta, "drift": delta > threshold}


def emit_monitoring_report(payload: dict) -> None:
    """Hook for external observability integration (Sentry/DataDog/Prometheus)."""
    _ = payload

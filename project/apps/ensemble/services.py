def weighted_ensemble_score(trend: float, confidence: float, volatility: float, risk: float) -> float:
    return (trend * confidence * volatility) - risk

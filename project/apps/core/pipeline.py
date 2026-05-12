from datetime import date

from project.apps.ensemble.services import weighted_ensemble_score
from project.apps.market_data.models import DailyCandle
from project.apps.rankings.services import persist_top_n_rankings


def run_daily_ranking_pipeline(run_date: date | None = None, top_n: int = 25) -> dict:
    run_date = run_date or date.today()
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
    return {"date": run_date.isoformat(), "processed": len(candles), "ranked": len(persisted)}

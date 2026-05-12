from datetime import date

from fastapi import FastAPI, HTTPException

from project.apps.core.pipeline import run_daily_ranking_pipeline
from project.apps.rankings.models import DailyRanking
from .schemas import BacktestSummary, ExplanationPayload, RankingItem, SymbolSnapshot

app = FastAPI(title="StockEdge API")


@app.get("/rankings/today", response_model=list[RankingItem])
def rankings_today():
    today = date.today()
    rows = DailyRanking.objects.filter(date=today).order_by("rank")
    return [RankingItem(symbol=r.symbol, rank=r.rank, score=r.score) for r in rows]


@app.get("/symbol/{symbol}", response_model=SymbolSnapshot)
def symbol_snapshot(symbol: str):
    row = DailyRanking.objects.filter(symbol=symbol).order_by("-date").first()
    if not row:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return SymbolSnapshot(symbol=row.symbol, score=row.score, rank=row.rank, components=row.inputs)


@app.get("/explain/{symbol}", response_model=ExplanationPayload)
def explain(symbol: str):
    row = DailyRanking.objects.filter(symbol=symbol).order_by("-date").first()
    if not row:
        raise HTTPException(status_code=404, detail="Symbol not found")
    return ExplanationPayload(symbol=symbol, explanation=row.inputs)


@app.get("/backtests/latest", response_model=BacktestSummary)
def backtests_latest():
    return BacktestSummary(run_id="baseline", stats={"sharpe": 0.0, "cagr": 0.0})


@app.post("/process/run")
def run_process():
    return run_daily_ranking_pipeline()


@app.get("/prediction/{symbol}", response_model=SymbolSnapshot)
def prediction_by_symbol(symbol: str):
    return symbol_snapshot(symbol)

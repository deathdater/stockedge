from pydantic import BaseModel


class RankingItem(BaseModel):
    symbol: str
    rank: int
    score: float


class SymbolSnapshot(BaseModel):
    symbol: str
    score: float
    rank: int
    components: dict[str, float]


class ExplanationPayload(BaseModel):
    symbol: str
    explanation: dict[str, float]


class BacktestSummary(BaseModel):
    run_id: str
    stats: dict[str, float]

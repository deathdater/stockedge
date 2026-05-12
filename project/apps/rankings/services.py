from .models import DailyRanking


def persist_top_n_rankings(scored_rows: list[dict], date, top_n: int = 25) -> list[DailyRanking]:
    ordered = sorted(scored_rows, key=lambda r: r["score"], reverse=True)[:top_n]
    saved = []
    for i, row in enumerate(ordered, start=1):
        obj, _ = DailyRanking.objects.update_or_create(
            date=date,
            symbol=row["symbol"],
            defaults={"rank": i, "score": row["score"], "inputs": row.get("inputs", {})},
        )
        saved.append(obj)
    return saved

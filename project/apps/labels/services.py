from .contracts import LabelInputRow, LabelOutputRow


def build_future_return_labels(rows: list[LabelInputRow], horizon_days: int = 5) -> list[LabelOutputRow]:
    by_symbol: dict[str, list[LabelInputRow]] = {}
    for row in rows:
        by_symbol.setdefault(row.symbol, []).append(row)

    outputs: list[LabelOutputRow] = []
    for symbol_rows in by_symbol.values():
        ordered = sorted(symbol_rows, key=lambda r: r.date)
        for i, row in enumerate(ordered):
            j = i + horizon_days
            if j >= len(ordered) or row.close == 0:
                continue
            ret = (ordered[j].close / row.close) - 1.0
            direction = 1 if ret > 0 else -1 if ret < 0 else 0
            outputs.append(
                LabelOutputRow(
                    symbol=row.symbol,
                    date=row.date,
                    horizon_days=horizon_days,
                    future_return=ret,
                    direction=direction,
                )
            )
    return outputs

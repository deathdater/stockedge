from dataclasses import dataclass


@dataclass(slots=True)
class BacktestConfig:
    slippage_bps: float = 5.0
    commission_bps: float = 2.0
    fill_delay_days: int = 1
    position_size: float = 0.05
    max_exposure: float = 1.0


def run_vectorbt_backtest(price_series, entry_signals, exit_signals, config: BacktestConfig):
    try:
        import vectorbt as vbt
    except ImportError as exc:
        raise RuntimeError("vectorbt is required for backtesting workflow") from exc

    fees = config.commission_bps / 10_000
    slippage = config.slippage_bps / 10_000
    delayed_entries = entry_signals.shift(config.fill_delay_days).fillna(False)
    delayed_exits = exit_signals.shift(config.fill_delay_days).fillna(False)

    portfolio = vbt.Portfolio.from_signals(
        close=price_series,
        entries=delayed_entries,
        exits=delayed_exits,
        fees=fees,
        slippage=slippage,
        size=config.position_size,
        size_type="valuepercent",
        max_size=config.max_exposure,
    )
    return portfolio

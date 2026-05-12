import sys
import types
from unittest.mock import patch

from project.apps.backtesting.services import BacktestConfig, run_vectorbt_backtest


def test_backtest_applies_slippage_commission_and_exposure_constraints():
    class SeriesLike(list):
        def shift(self, days):
            return SeriesLike(([False] * days) + list(self[:-days or None]))

        def fillna(self, value):
            return self

        @property
        def iloc(self):
            return self

    price = SeriesLike([100, 101, 102])
    entries = SeriesLike([True, False, False])
    exits = SeriesLike([False, True, False])
    cfg = BacktestConfig(slippage_bps=10, commission_bps=3, fill_delay_days=1, position_size=0.25, max_exposure=0.75)

    fake_vbt = types.ModuleType("vectorbt")

    class Portfolio:
        @staticmethod
        def from_signals(**kwargs):
            return "portfolio"

    fake_vbt.Portfolio = Portfolio
    sys.modules["vectorbt"] = fake_vbt

    with patch("vectorbt.Portfolio.from_signals", return_value="portfolio") as mock_from_signals:
        result = run_vectorbt_backtest(price, entries, exits, cfg)

    assert result == "portfolio"
    kwargs = mock_from_signals.call_args.kwargs
    assert kwargs["fees"] == 0.0003
    assert kwargs["slippage"] == 0.001
    assert kwargs["size"] == 0.25
    assert kwargs["max_size"] == 0.75
    assert bool(kwargs["entries"].iloc[0]) is False

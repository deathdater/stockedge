from datetime import date

import pytest

from project.apps.ingestion.validators import DataValidator


def test_parse_row_rejects_missing_required_columns():
    with pytest.raises(ValueError, match="missing columns"):
        DataValidator.parse_row({"SYMBOL": "ABC"}, trade_date=date(2026, 1, 1))


def test_parse_row_rejects_invalid_price_ranges_and_negative_volume():
    with pytest.raises(ValueError, match="high < low"):
        DataValidator.parse_row(
            {
                "SYMBOL": "ABC",
                "OPEN_PRICE": "100",
                "HIGH_PRICE": "90",
                "LOW_PRICE": "95",
                "CLOSE_PRICE": "96",
                "NET_TRDQTY": "1000",
            },
            trade_date=date(2026, 1, 1),
        )

    with pytest.raises(ValueError, match="negative volume"):
        DataValidator.parse_row(
            {
                "SYMBOL": "ABC",
                "OPEN_PRICE": "100",
                "HIGH_PRICE": "110",
                "LOW_PRICE": "95",
                "CLOSE_PRICE": "96",
                "NET_TRDQTY": "-1",
            },
            trade_date=date(2026, 1, 1),
        )


def test_parse_row_normalizes_symbol_and_types():
    row = DataValidator.parse_row(
        {
            "SYMBOL": " abc ",
            "OPEN_PRICE": "100",
            "HIGH_PRICE": "110",
            "LOW_PRICE": "95",
            "CLOSE_PRICE": "108",
            "NET_TRDQTY": "1000",
        },
        trade_date=date(2026, 1, 1),
    )
    assert row["symbol"] == "ABC"
    assert row["volume"] == 1000

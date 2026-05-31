import pandas as pd

from stock_bullish.config import FilterConfig
from stock_bullish.data_cleaner import filter_tradeable_universe


def test_filter_tradeable_universe_removes_untradeable_rows():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-02"] * 4),
            "symbol": ["A", "B", "C", "D"],
            "open": [10, 10, 10, 10],
            "high": [11, 11, 11, 11],
            "low": [9, 9, 9, 9],
            "close": [10, 10, 10, 10],
            "volume": [1, 1, 1, 1],
            "amount": [100_000_000, 100_000_000, 100_000_000, 1_000_000],
            "is_st": [False, True, False, False],
            "is_suspended": [False, False, True, False],
            "is_delisted": [False, False, False, False],
            "listing_days": [200, 200, 200, 200],
        }
    )

    result = filter_tradeable_universe(
        df,
        FilterConfig(liquidity_lookback=1, min_avg_amount=30_000_000),
    )

    assert list(result["symbol"]) == ["A"]


def test_filter_tradeable_universe_keeps_st_rows_when_not_excluded():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-02", "2026-01-02"]),
            "symbol": ["A", "B"],
            "amount": [100_000_000, 100_000_000],
            "is_st": [False, True],
            "listing_days": [200, 200],
        }
    )

    result = filter_tradeable_universe(
        df,
        FilterConfig(exclude_st=False, liquidity_lookback=1, min_avg_amount=30_000_000),
    )

    assert list(result["symbol"]) == ["A", "B"]

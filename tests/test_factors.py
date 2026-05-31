import pandas as pd

from stock_bullish.factors import add_core_factors


def test_add_core_factors_marks_moving_average_breakout():
    df = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=25, freq="D"),
            "symbol": ["A"] * 25,
            "open": list(range(10, 35)),
            "high": list(range(11, 36)),
            "low": list(range(9, 34)),
            "close": list(range(10, 35)),
            "volume": [100] * 20 + [300] * 5,
            "amount": [10_000_000] * 20 + [50_000_000] * 5,
        }
    )
    original = df.copy(deep=True)

    result = add_core_factors(df)

    pd.testing.assert_frame_equal(df, original)
    core_columns = {
        "ma5",
        "ma20",
        "ma60",
        "macd",
        "macd_signal",
        "macd_hist",
        "rsi14",
        "return_5d",
        "return_20d",
        "volatility_20d",
        "avg_volume_20d",
        "avg_amount_20d",
        "ma_bullish",
        "ma_breakout",
        "volume_expansion",
        "amount_expansion",
        "turnover_spike",
        "price_volume_divergence",
        "consecutive_amount_inflow",
        "momentum_strong",
        "volatility_contraction",
    }
    assert core_columns.issubset(result.columns)
    assert pd.isna(result["avg_volume_20d"].iloc[18])
    assert pd.isna(result["avg_volume_20d"].iloc[19]) is False
    assert pd.isna(result["avg_amount_20d"].iloc[18])
    assert pd.isna(result["avg_amount_20d"].iloc[19]) is False
    assert pd.isna(result["volatility_20d"].iloc[19])
    assert pd.isna(result["volatility_20d"].iloc[20]) is False
    assert pd.notna(result["avg_volume_20d"].iloc[-1])
    assert pd.notna(result["avg_amount_20d"].iloc[-1])
    assert pd.notna(result["volatility_20d"].iloc[-1])
    assert pd.notna(result["rsi14"].iloc[-1])
    assert result["rsi14"].iloc[-1] > 50
    assert bool(result["ma_bullish"].iloc[-1])
    assert bool(result["volume_expansion"].iloc[-1])
    assert bool(result["turnover_spike"].iloc[-1])


def test_add_core_factors_keeps_rolling_windows_per_symbol():
    dates = pd.date_range("2026-01-01", periods=21, freq="D")
    df = pd.concat(
        [
            pd.DataFrame(
                {
                    "trade_date": dates,
                    "symbol": ["B"] * 21,
                    "open": range(100, 121),
                    "high": range(101, 122),
                    "low": range(99, 120),
                    "close": range(100, 121),
                    "volume": [1_000] * 21,
                    "amount": [100_000_000] * 21,
                }
            ),
            pd.DataFrame(
                {
                    "trade_date": dates,
                    "symbol": ["A"] * 21,
                    "open": range(10, 31),
                    "high": range(11, 32),
                    "low": range(9, 30),
                    "close": range(10, 31),
                    "volume": [100] * 21,
                    "amount": [10_000_000] * 21,
                }
            ),
        ],
        ignore_index=True,
    ).sample(frac=1, random_state=42).reset_index(drop=True)
    original = df.copy(deep=True)

    result = add_core_factors(df).sort_values(["symbol", "trade_date"]).reset_index(drop=True)

    pd.testing.assert_frame_equal(df, original)
    a_rows = result[result["symbol"] == "A"].reset_index(drop=True)
    b_rows = result[result["symbol"] == "B"].reset_index(drop=True)

    assert pd.isna(a_rows["avg_volume_20d"].iloc[18])
    assert pd.isna(a_rows["avg_volume_20d"].iloc[19]) is False
    assert a_rows["avg_volume_20d"].iloc[19] == 100
    assert a_rows["avg_volume_20d"].iloc[20] == 100

    assert pd.isna(b_rows["avg_volume_20d"].iloc[18])
    assert pd.isna(b_rows["avg_volume_20d"].iloc[19]) is False
    assert b_rows["avg_volume_20d"].iloc[19] == 1_000
    assert b_rows["avg_volume_20d"].iloc[20] == 1_000


def test_add_core_factors_marks_turnover_spike_from_turnover_column():
    df = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=21, freq="D"),
            "symbol": ["A"] * 21,
            "open": range(10, 31),
            "high": range(11, 32),
            "low": range(9, 30),
            "close": range(10, 31),
            "volume": [100] * 21,
            "amount": [10_000_000] * 21,
            "turnover": [1.0] * 20 + [3.0],
        }
    )

    result = add_core_factors(df)

    assert bool(result["turnover_spike"].iloc[-1])


def test_add_core_factors_marks_price_volume_divergence_on_falling_price_with_volume_expansion():
    df = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=25, freq="D"),
            "symbol": ["A"] * 25,
            "open": [100] * 20 + [99, 98, 97, 96, 95],
            "high": [101] * 20 + [100, 99, 98, 97, 96],
            "low": [99] * 20 + [98, 97, 96, 95, 94],
            "close": [100] * 20 + [99, 98, 97, 96, 95],
            "volume": [100] * 24 + [300],
            "amount": [10_000_000] * 24 + [50_000_000],
        }
    )

    result = add_core_factors(df)

    assert bool(result["price_volume_divergence"].iloc[-1])


def test_add_core_factors_marks_consecutive_amount_inflow_after_three_increases():
    df = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=10, freq="D"),
            "symbol": ["A"] * 10,
            "open": range(10, 20),
            "high": range(11, 21),
            "low": range(9, 19),
            "close": range(10, 20),
            "volume": [100] * 10,
            "amount": [10_000_000] * 6 + [20_000_000, 30_000_000, 40_000_000, 50_000_000],
        }
    )

    result = add_core_factors(df)

    assert bool(result["consecutive_amount_inflow"].iloc[-1])

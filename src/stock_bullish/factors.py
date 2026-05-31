import pandas as pd


def add_core_factors(df: pd.DataFrame) -> pd.DataFrame:
    result = df.sort_values(["symbol", "trade_date"]).copy()
    grouped = result.groupby("symbol", group_keys=False)

    result["ma5"] = grouped["close"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    result["ma20"] = grouped["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    result["ma60"] = grouped["close"].transform(lambda s: s.rolling(60, min_periods=60).mean())
    result["macd"] = grouped["close"].transform(
        lambda s: s.ewm(span=12, adjust=False).mean() - s.ewm(span=26, adjust=False).mean()
    )
    result["macd_signal"] = grouped["macd"].transform(
        lambda s: s.ewm(span=9, adjust=False).mean()
    )
    result["macd_hist"] = result["macd"] - result["macd_signal"]
    close_diff = grouped["close"].diff()
    average_gain = close_diff.clip(lower=0).groupby(result["symbol"]).transform(
        lambda s: s.rolling(14, min_periods=14).mean()
    )
    average_loss = (-close_diff.clip(upper=0)).groupby(result["symbol"]).transform(
        lambda s: s.rolling(14, min_periods=14).mean()
    )
    rs = average_gain / average_loss
    result["rsi14"] = 100 - (100 / (1 + rs))
    result["return_5d"] = grouped["close"].pct_change(5)
    result["return_20d"] = grouped["close"].pct_change(20)
    result["volatility_20d"] = grouped["close"].transform(
        lambda s: s.pct_change().rolling(20, min_periods=20).std()
    )
    result["avg_volume_20d"] = grouped["volume"].transform(
        lambda s: s.rolling(20, min_periods=20).mean()
    )
    result["avg_amount_20d"] = grouped["amount"].transform(
        lambda s: s.rolling(20, min_periods=20).mean()
    )

    grouped = result.groupby("symbol", group_keys=False)
    result["ma_bullish"] = (result["ma5"] > result["ma20"]) & (
        result["ma60"].isna() | (result["ma20"] > result["ma60"])
    )
    previous_close = grouped["close"].shift(1)
    previous_ma20 = grouped["ma20"].shift(1)
    result["ma_breakout"] = (result["close"] > result["ma20"]) & (previous_close <= previous_ma20)
    result["volume_expansion"] = result["volume"] >= result["avg_volume_20d"] * 1.5
    result["amount_expansion"] = result["amount"] >= result["avg_amount_20d"] * 1.5
    if "turnover" in result.columns:
        average_turnover_20d = grouped["turnover"].transform(
            lambda s: s.rolling(20, min_periods=20).mean()
        )
        result["turnover_spike"] = result["turnover"] >= average_turnover_20d * 1.5
    else:
        result["turnover_spike"] = result["volume_expansion"]

    price_new_high_20d = result["close"] >= grouped["close"].transform(
        lambda s: s.rolling(20, min_periods=20).max()
    )
    activity_expansion = result["volume_expansion"] | result["amount_expansion"]
    result["price_volume_divergence"] = (
        (result["return_5d"] < 0) & activity_expansion
    ) | (price_new_high_20d & ~activity_expansion)
    result["consecutive_amount_inflow"] = grouped["amount"].transform(
        lambda s: s.diff().gt(0).rolling(3, min_periods=3).sum().eq(3)
    )
    result["momentum_strong"] = result["return_20d"] > 0.08
    result["volatility_contraction"] = result["volatility_20d"] < grouped[
        "volatility_20d"
    ].transform(lambda s: s.rolling(60, min_periods=20).median())

    return result

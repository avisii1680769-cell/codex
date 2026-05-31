import pandas as pd

from stock_bullish.config import FilterConfig


def filter_tradeable_universe(df: pd.DataFrame, config: FilterConfig) -> pd.DataFrame:
    result = df.copy()

    if config.exclude_st and "is_st" in result.columns:
        result = result[~result["is_st"].fillna(False)]
    if config.exclude_suspended and "is_suspended" in result.columns:
        result = result[~result["is_suspended"].fillna(False)]
    if config.exclude_delisted and "is_delisted" in result.columns:
        result = result[~result["is_delisted"].fillna(False)]
    if "listing_days" in result.columns:
        result = result[result["listing_days"] >= config.min_listing_days]

    result = result.sort_values(["symbol", "trade_date"]).copy()
    result["avg_amount"] = (
        result.groupby("symbol")["amount"]
        .transform(lambda s: s.rolling(config.liquidity_lookback, min_periods=1).mean())
    )
    result = result[result["avg_amount"] >= config.min_avg_amount]
    return result.drop(columns=["avg_amount"]).reset_index(drop=True)

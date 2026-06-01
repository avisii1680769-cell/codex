import pandas as pd


SUMMARY_COLUMNS = [
    "strategy",
    "window",
    "sample_count",
    "fixed_target_success_rate",
    "path_success_rate",
    "average_return",
    "median_return",
    "worst_return",
    "best_return",
    "profit_loss_ratio",
    "max_drawdown",
    "unstable_sample",
]
STABILITY_COLUMNS = ["group_type", "group_value", *SUMMARY_COLUMNS]


def summarize_backtest(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(columns=SUMMARY_COLUMNS)

    grouped = results.groupby(["strategy", "window"], dropna=False)
    summary = grouped.agg(
        sample_count=("window_return", "size"),
        fixed_target_success_rate=("fixed_target_success", "mean"),
        path_success_rate=("path_success", "mean"),
        average_return=("window_return", "mean"),
        median_return=("window_return", "median"),
        worst_return=("window_return", "min"),
        best_return=("window_return", "max"),
        max_drawdown=("max_drawdown", "min"),
    ).reset_index()
    summary["profit_loss_ratio"] = grouped["window_return"].apply(_profit_loss_ratio).to_numpy()
    summary["unstable_sample"] = summary["sample_count"] < 30
    return summary[SUMMARY_COLUMNS]


def summarize_group_stability(results: pd.DataFrame) -> pd.DataFrame:
    if results.empty:
        return pd.DataFrame(columns=STABILITY_COLUMNS)

    frames = []
    if "signal_date" in results.columns:
        year_results = results.copy()
        year_results["group_type"] = "year"
        year_results["group_value"] = pd.to_datetime(year_results["signal_date"]).dt.year.astype(str)
        frames.append(_summarize_with_group(year_results))

    if "industry" in results.columns:
        industry_results = results[results["industry"].notna()].copy()
        if not industry_results.empty:
            industry_results["group_type"] = "industry"
            industry_results["group_value"] = industry_results["industry"].astype(str)
            frames.append(_summarize_with_group(industry_results))

    if "market_cap" in results.columns:
        market_cap_results = results[results["market_cap"].notna()].copy()
        if not market_cap_results.empty:
            market_cap_results["group_type"] = "market_cap_bucket"
            market_cap_results["group_value"] = _market_cap_bucket(market_cap_results["market_cap"])
            frames.append(_summarize_with_group(market_cap_results))

    if not frames:
        return pd.DataFrame(columns=STABILITY_COLUMNS)
    return pd.concat(frames, ignore_index=True)[STABILITY_COLUMNS]


def _summarize_with_group(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(["group_type", "group_value", "strategy", "window"], dropna=False)
    summary = grouped.agg(
        sample_count=("window_return", "size"),
        fixed_target_success_rate=("fixed_target_success", "mean"),
        path_success_rate=("path_success", "mean"),
        average_return=("window_return", "mean"),
        median_return=("window_return", "median"),
        worst_return=("window_return", "min"),
        best_return=("window_return", "max"),
        max_drawdown=("max_drawdown", "min"),
    ).reset_index()
    summary["profit_loss_ratio"] = grouped["window_return"].apply(_profit_loss_ratio).to_numpy()
    summary["unstable_sample"] = summary["sample_count"] < 30
    return summary


def _market_cap_bucket(market_cap: pd.Series) -> pd.Series:
    return pd.cut(
        market_cap.astype(float),
        bins=[float("-inf"), 10_000_000_000, 100_000_000_000, float("inf")],
        labels=["small", "mid", "large"],
        right=False,
    ).astype(str)


def _profit_loss_ratio(returns: pd.Series) -> float:
    winners = returns[returns > 0]
    losers = returns[returns < 0]
    if winners.empty or losers.empty:
        return float("nan")
    return winners.mean() / abs(losers.mean())

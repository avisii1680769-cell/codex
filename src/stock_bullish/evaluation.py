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
    "unstable_sample",
]


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
    ).reset_index()
    summary["unstable_sample"] = summary["sample_count"] < 30
    return summary[SUMMARY_COLUMNS]

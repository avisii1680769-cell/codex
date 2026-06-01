import pandas as pd
import pytest

from stock_bullish.evaluation import summarize_backtest, summarize_group_stability


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


def test_summarize_backtest_groups_by_strategy_and_window():
    results = pd.DataFrame(
        {
            "strategy": ["demo", "demo", "demo", "control", "control"],
            "window": [5, 5, 5, 20, 20],
            "fixed_target_success": [True, False, True, True, False],
            "path_success": [True, None, float("nan"), None, float("nan")],
            "window_return": [0.05, -0.02, 0.12, 0.03, -0.01],
        }
    )

    summary = summarize_backtest(results)

    row = summary[(summary["strategy"] == "demo") & (summary["window"] == 5)].iloc[0]
    assert row["sample_count"] == 3
    assert row["fixed_target_success_rate"] == pytest.approx(2 / 3)
    assert row["path_success_rate"] == 1.0
    assert row["average_return"] == pytest.approx(0.05)
    assert row["median_return"] == pytest.approx(0.05)
    assert row["worst_return"] == pytest.approx(-0.02)
    assert row["best_return"] == pytest.approx(0.12)

    long_window_row = summary[
        (summary["strategy"] == "control") & (summary["window"] == 20)
    ].iloc[0]
    assert pd.isna(long_window_row["path_success_rate"])


def test_summarize_backtest_returns_empty_frame_with_columns():
    results = pd.DataFrame(
        columns=["strategy", "window", "fixed_target_success", "path_success", "window_return"]
    )

    summary = summarize_backtest(results)

    assert summary.empty
    assert list(summary.columns) == SUMMARY_COLUMNS


def test_summarize_backtest_marks_unstable_sample_threshold():
    results = pd.DataFrame(
        {
            "strategy": ["demo"] * 29 + ["control"] * 30,
            "window": [5] * 59,
            "fixed_target_success": [True] * 59,
            "path_success": [True] * 59,
            "window_return": [0.01] * 59,
        }
    )

    summary = summarize_backtest(results)

    demo_row = summary[(summary["strategy"] == "demo") & (summary["window"] == 5)].iloc[0]
    control_row = summary[
        (summary["strategy"] == "control") & (summary["window"] == 5)
    ].iloc[0]
    assert demo_row["sample_count"] == 29
    assert demo_row["unstable_sample"]
    assert control_row["sample_count"] == 30
    assert not control_row["unstable_sample"]


def test_summarize_backtest_preserves_raw_mean_precision():
    results = pd.DataFrame(
        {
            "strategy": ["demo"],
            "window": [5],
            "fixed_target_success": [True],
            "path_success": [True],
            "window_return": [0.123456789123456],
        }
    )

    summary = summarize_backtest(results)

    row = summary.iloc[0]
    assert row["average_return"] == pytest.approx(0.123456789123456, rel=0, abs=1e-16)


def test_summarize_group_stability_groups_by_year_industry_and_market_cap_bucket():
    results = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2024-01-02", "2024-02-02", "2025-01-02"]),
            "strategy": ["demo", "demo", "demo"],
            "window": [5, 5, 5],
            "industry": ["bank", "tech", "bank"],
            "market_cap": [8_000_000_000, 30_000_000_000, 150_000_000_000],
            "fixed_target_success": [True, False, True],
            "path_success": [True, False, None],
            "window_return": [0.05, -0.02, 0.12],
        }
    )

    stability = summarize_group_stability(results)

    assert set(stability["group_type"]) == {"year", "industry", "market_cap_bucket"}
    year_2024 = stability[
        (stability["group_type"] == "year") & (stability["group_value"] == "2024")
    ].iloc[0]
    assert year_2024["sample_count"] == 2
    assert year_2024["fixed_target_success_rate"] == pytest.approx(0.5)

    market_cap_groups = stability[stability["group_type"] == "market_cap_bucket"]
    assert set(market_cap_groups["group_value"]) == {"small", "mid", "large"}


def test_summarize_group_stability_returns_empty_frame_with_columns():
    stability = summarize_group_stability(pd.DataFrame())

    assert stability.empty
    assert stability.columns.tolist() == [
        "group_type",
        "group_value",
        *SUMMARY_COLUMNS,
    ]

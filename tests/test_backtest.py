import pandas as pd
import pytest

from stock_bullish.backtest import run_backtest
from stock_bullish.config import BacktestConfig, CostConfig


def test_run_backtest_detects_fixed_target_and_path_success():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=7, freq="D"),
            "symbol": ["A"] * 7,
            "open": [10, 10, 10.2, 10.5, 10.8, 11.0, 11.2],
            "high": [10.1, 10.4, 10.8, 11.0, 11.4, 11.6, 11.8],
            "low": [9.9, 10.0, 10.1, 10.3, 10.5, 10.8, 11.0],
            "close": [10, 10.2, 10.6, 10.9, 11.2, 11.4, 11.7],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(windows=(5,), fixed_return_targets={5: 0.03}, stop_loss=0.04),
    )

    assert results["fixed_target_success"].iloc[0]
    assert results["path_success"].iloc[0]
    assert results["window"].iloc[0] == 5


def test_run_backtest_prioritizes_stop_loss_when_same_day_hits_both_thresholds():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=2, freq="D"),
            "symbol": ["A", "A"],
            "open": [10.0, 10.0],
            "high": [10.0, 10.9],
            "low": [10.0, 9.5],
            "close": [10.0, 10.2],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(windows=(1,), fixed_return_targets={1: 0.03}, stop_loss=0.04),
    )

    assert results["path_success"].iloc[0] is False
    assert results["exit_reason"].iloc[0] == "stop_loss"


def test_run_backtest_returns_empty_frame_with_columns_when_no_future_prices():
    prices = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "open": [10.0],
            "high": [10.0],
            "low": [10.0],
            "close": [10.0],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(windows=(5,), fixed_return_targets={5: 0.03}, stop_loss=0.04),
    )

    assert results.empty
    assert list(results.columns) == [
        "signal_date",
        "symbol",
        "entry_close",
        "strategy",
        "window",
        "fixed_target_success",
        "path_success",
            "window_return",
            "max_return",
            "max_drawdown",
            "exit_reason",
        ]


def test_run_backtest_skips_window_when_future_prices_are_shorter_than_window():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=3, freq="D"),
            "symbol": ["A"] * 3,
            "open": [10.0, 10.1, 10.2],
            "high": [10.0, 10.4, 10.6],
            "low": [10.0, 10.0, 10.1],
            "close": [10.0, 10.2, 10.5],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(windows=(5,), fixed_return_targets={5: 0.03}, stop_loss=0.04),
    )

    assert results.empty
    assert list(results.columns) == [
        "signal_date",
        "symbol",
        "entry_close",
        "strategy",
        "window",
        "fixed_target_success",
        "path_success",
            "window_return",
            "max_return",
            "max_drawdown",
            "exit_reason",
        ]


def test_run_backtest_applies_round_trip_costs_to_returns_and_fixed_target():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=2, freq="D"),
            "symbol": ["A", "A"],
            "open": [10.0, 10.0],
            "high": [10.0, 10.31],
            "low": [10.0, 10.0],
            "close": [10.0, 10.25],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(
            windows=(1,),
            fixed_return_targets={1: 0.03},
            stop_loss=0.04,
            costs=CostConfig(commission_rate=0.0003, slippage_rate=0.0005),
        ),
    )

    assert results["window_return"].iloc[0] == pytest.approx(0.025 - 0.0016)
    assert results["max_return"].iloc[0] == pytest.approx(0.031 - 0.0016)
    assert results["fixed_target_success"].iloc[0] is False


def test_run_backtest_applies_round_trip_costs_to_path_success():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=2, freq="D"),
            "symbol": ["A", "A"],
            "open": [10.0, 10.0],
            "high": [10.0, 10.805],
            "low": [10.0, 10.0],
            "close": [10.0, 10.7],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(
            windows=(1,),
            fixed_return_targets={1: 0.03},
            stop_loss=0.04,
            costs=CostConfig(commission_rate=0.0003, slippage_rate=0.0005),
        ),
    )

    assert results["path_success"].iloc[0] is None
    assert results["exit_reason"].iloc[0] == "window_end"


def test_run_backtest_records_max_drawdown_after_costs():
    prices = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=4, freq="D"),
            "symbol": ["A"] * 4,
            "open": [10.0, 10.0, 10.0, 10.0],
            "high": [10.0, 10.2, 10.1, 10.3],
            "low": [10.0, 9.7, 9.6, 9.8],
            "close": [10.0, 10.1, 9.9, 10.2],
        }
    )
    signals = pd.DataFrame(
        {
            "signal_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "entry_close": [10.0],
            "strategy": ["demo"],
        }
    )

    results = run_backtest(
        prices,
        signals,
        BacktestConfig(
            windows=(3,),
            fixed_return_targets={3: 0.03},
            stop_loss=0.05,
            costs=CostConfig(commission_rate=0.0003, slippage_rate=0.0005),
        ),
    )

    assert results["max_drawdown"].iloc[0] == pytest.approx(-0.04 - 0.0016)

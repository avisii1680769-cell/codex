import pandas as pd
import pytest

from stock_bullish.strategy import PRESET_STRATEGIES, StrategyRule, generate_signals, get_strategy_rules


def test_generate_signals_requires_all_selected_conditions():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-01", "2026-01-02"]),
            "symbol": ["A", "A"],
            "ma_bullish": [True, True],
            "volume_expansion": [False, True],
            "close": [10, 11],
        }
    )

    signals = generate_signals(
        df,
        StrategyRule(name="breakout", conditions=("ma_bullish", "volume_expansion")),
    )

    assert signals.shape[0] == 1
    assert signals["signal_date"].dt.strftime("%Y-%m-%d").iloc[0] == "2026-01-02"
    assert signals["strategy"].iloc[0] == "breakout"


def test_generate_signals_uses_min_score_when_provided():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-01", "2026-01-02", "2026-01-03"]),
            "symbol": ["A", "A", "A"],
            "ma_bullish": [True, False, False],
            "volume_expansion": [False, True, False],
            "close": [10, 11, 12],
        }
    )

    signals = generate_signals(
        df,
        StrategyRule(
            name="score",
            conditions=("ma_bullish", "volume_expansion"),
            min_score=1,
        ),
    )

    assert signals["signal_date"].dt.strftime("%Y-%m-%d").tolist() == [
        "2026-01-01",
        "2026-01-02",
    ]
    assert signals["entry_close"].tolist() == [10, 11]
    assert signals["matched_conditions"].tolist() == ["ma_bullish", "volume_expansion"]
    assert {"ma_bullish", "volume_expansion"}.issubset(signals.columns)


def test_generate_signals_does_not_match_missing_conditions():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "ma_bullish": [True],
            "volume_expansion": [pd.NA],
            "close": [10],
        }
    )

    signals = generate_signals(
        df,
        StrategyRule(
            name="score",
            conditions=("ma_bullish", "volume_expansion"),
            min_score=1,
        ),
    )

    assert signals.shape[0] == 1
    assert signals["matched_conditions"].iloc[0] == "ma_bullish"
    assert signals["volume_expansion"].tolist() == [False]


def test_generate_signals_rejects_missing_condition_columns():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-01"]),
            "symbol": ["A"],
            "ma_bullish": [True],
            "close": [10],
        }
    )

    with pytest.raises(
        ValueError,
        match=r"Missing strategy condition columns: \['volume_expansion'\]",
    ):
        generate_signals(
            df,
            StrategyRule(name="breakout", conditions=("ma_bullish", "volume_expansion")),
        )


def test_get_strategy_rules_returns_all_presets_by_default():
    rules = get_strategy_rules("all")

    assert [rule.name for rule in rules] == list(PRESET_STRATEGIES)
    assert len(rules) >= 3


def test_get_strategy_rules_returns_single_named_preset():
    rules = get_strategy_rules("trend_volume")

    assert rules == (PRESET_STRATEGIES["trend_volume"],)


def test_get_strategy_rules_rejects_unknown_name():
    with pytest.raises(ValueError, match="Unknown strategy preset: missing"):
        get_strategy_rules("missing")

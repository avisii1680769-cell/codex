from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyRule:
    name: str
    conditions: tuple[str, ...]
    min_score: int | None = None


PRESET_STRATEGIES = {
    "trend_volume": StrategyRule("trend_volume", ("ma_bullish", "volume_expansion"), min_score=2),
    "breakout_momentum": StrategyRule(
        "breakout_momentum",
        ("ma_breakout", "volume_expansion", "momentum_strong"),
        min_score=2,
    ),
    "capital_inflow": StrategyRule(
        "capital_inflow",
        ("amount_expansion", "turnover_spike", "consecutive_amount_inflow"),
        min_score=2,
    ),
    "balanced": StrategyRule(
        "balanced",
        (
            "ma_bullish",
            "ma_breakout",
            "volume_expansion",
            "amount_expansion",
            "volatility_contraction",
        ),
        min_score=3,
    ),
}


def get_strategy_rules(strategy_name: str = "all") -> tuple[StrategyRule, ...]:
    if strategy_name == "all":
        return tuple(PRESET_STRATEGIES.values())
    if strategy_name not in PRESET_STRATEGIES:
        valid_names = ", ".join(["all", *PRESET_STRATEGIES])
        raise ValueError(f"Unknown strategy preset: {strategy_name}. Valid presets: {valid_names}")
    return (PRESET_STRATEGIES[strategy_name],)


def generate_signals(df: pd.DataFrame, rule: StrategyRule) -> pd.DataFrame:
    missing = [condition for condition in rule.conditions if condition not in df.columns]
    if missing:
        raise ValueError(f"Missing strategy condition columns: {missing}")

    result = df.copy()
    condition_frame = result[list(rule.conditions)].fillna(False).astype(bool)

    if rule.min_score is None:
        mask = condition_frame.all(axis=1)
    else:
        mask = condition_frame.sum(axis=1) >= rule.min_score

    normalized_conditions = condition_frame.loc[mask].reset_index(drop=True)
    signals = result.loc[mask, ["trade_date", "symbol", "close"]].copy().reset_index(drop=True)
    signals = signals.rename(columns={"trade_date": "signal_date", "close": "entry_close"})
    signals[list(rule.conditions)] = normalized_conditions
    signals["strategy"] = rule.name
    signals["matched_conditions"] = normalized_conditions.apply(
        lambda row: ",".join([column for column, matched in row.items() if bool(matched)]),
        axis=1,
    )
    return signals

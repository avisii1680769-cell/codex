from dataclasses import dataclass

import pandas as pd


@dataclass(frozen=True)
class StrategyRule:
    name: str
    conditions: tuple[str, ...]
    min_score: int | None = None


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

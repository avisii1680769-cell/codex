import pandas as pd

from stock_bullish.config import BacktestConfig


RESULT_COLUMNS = [
    "window",
    "fixed_target_success",
    "path_success",
    "window_return",
    "max_return",
    "exit_reason",
]


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    config: BacktestConfig,
) -> pd.DataFrame:
    signal_columns = list(signals.columns)
    output_columns = signal_columns + RESULT_COLUMNS

    if prices.empty or signals.empty:
        return pd.DataFrame(columns=output_columns)
    if not {"trade_date", "symbol", "high", "low", "close"}.issubset(prices.columns):
        return pd.DataFrame(columns=output_columns)
    if not {"signal_date", "symbol", "entry_close"}.issubset(signals.columns):
        return pd.DataFrame(columns=output_columns)

    price_groups = {
        symbol: group.sort_values("trade_date").reset_index(drop=True)
        for symbol, group in prices.groupby("symbol", sort=False)
    }

    rows = []
    total_cost_rate = config.costs.commission_rate + config.costs.slippage_rate
    round_trip_cost = total_cost_rate * 2
    for _, signal in signals.iterrows():
        symbol = signal["symbol"]
        signal_date = signal["signal_date"]
        group = price_groups.get(symbol)
        if group is None:
            continue

        signal_matches = group.index[group["trade_date"] == signal_date].tolist()
        if not signal_matches:
            continue

        entry_index = signal_matches[0]
        entry_close = signal["entry_close"]
        take_profit = config.stop_loss * config.take_profit_loss_ratio

        for window in config.windows:
            future = group.iloc[entry_index + 1 : entry_index + 1 + window]
            if len(future) < window:
                continue

            max_return = future["high"].max() / entry_close - 1 - round_trip_cost
            window_return = future["close"].iloc[-1] / entry_close - 1 - round_trip_cost
            fixed_target = config.fixed_return_targets[window]
            path_success, exit_reason = _evaluate_path(
                future=future,
                entry_close=entry_close,
                stop_loss=config.stop_loss,
                take_profit=take_profit,
                round_trip_cost=round_trip_cost,
            )

            row = signal.to_dict()
            row.update(
                {
                    "window": window,
                    "fixed_target_success": bool(max_return >= fixed_target),
                    "path_success": path_success,
                    "window_return": window_return,
                    "max_return": max_return,
                    "exit_reason": exit_reason,
                }
            )
            rows.append(row)

    result = pd.DataFrame(rows, columns=output_columns)
    for column in ["fixed_target_success", "path_success"]:
        if column in result.columns:
            result[column] = result[column].astype(object)
    return result


def _evaluate_path(
    future: pd.DataFrame,
    entry_close: float,
    stop_loss: float,
    take_profit: float,
    round_trip_cost: float,
) -> tuple[bool | None, str]:
    for _, price in future.iterrows():
        low_return = price["low"] / entry_close - 1 - round_trip_cost
        high_return = price["high"] / entry_close - 1 - round_trip_cost
        if low_return <= -stop_loss:
            return False, "stop_loss"
        if high_return >= take_profit:
            return True, "take_profit"

    return None, "window_end"

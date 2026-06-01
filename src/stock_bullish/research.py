from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from stock_bullish.backtest import run_backtest
from stock_bullish.config import BacktestConfig
from stock_bullish.data_cleaner import filter_tradeable_universe
from stock_bullish.data_loader import load_market_data
from stock_bullish.evaluation import (
    SUMMARY_COLUMNS,
    STABILITY_COLUMNS,
    summarize_backtest,
    summarize_group_stability,
)
from stock_bullish.factors import add_core_factors
from stock_bullish.reporting import write_research_reports
from stock_bullish.strategy import generate_signals, get_strategy_rules


@dataclass(frozen=True)
class ResearchOutput:
    summary: pd.DataFrame
    signals: pd.DataFrame
    backtest_results: pd.DataFrame
    stability: pd.DataFrame
    paths: dict[str, Path]


def run_research(
    input_path: str | Path,
    output_dir: str | Path,
    strategy_name: str = "all",
    config: BacktestConfig | None = None,
) -> ResearchOutput:
    config = config or BacktestConfig()
    rules = get_strategy_rules(strategy_name)

    prices = load_market_data(input_path)
    prices = filter_tradeable_universe(prices, config.filters)
    if prices.empty:
        summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
        signals = pd.DataFrame()
        results = pd.DataFrame()
        stability = pd.DataFrame(columns=STABILITY_COLUMNS)
    else:
        prices = add_core_factors(prices)
        signals = pd.concat(
            [generate_signals(prices, rule) for rule in rules],
            ignore_index=True,
        )
        if signals.empty:
            summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
            results = pd.DataFrame()
            stability = pd.DataFrame(columns=STABILITY_COLUMNS)
        else:
            results = run_backtest(prices, signals, config)
            summary = summarize_backtest(results)
            if summary.empty:
                summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
            stability = summarize_group_stability(results)

    paths = write_research_reports(
        summary=summary,
        output_dir=output_dir,
        signals=signals,
        backtest_results=results,
        stability=stability,
    )
    return ResearchOutput(
        summary=summary,
        signals=signals,
        backtest_results=results,
        stability=stability,
        paths=paths,
    )

from pathlib import Path

import pandas as pd
import typer
from rich.console import Console

from stock_bullish import __version__
from stock_bullish.backtest import run_backtest
from stock_bullish.config import BacktestConfig
from stock_bullish.data_cleaner import filter_tradeable_universe
from stock_bullish.data_loader import load_market_data
from stock_bullish.evaluation import SUMMARY_COLUMNS, summarize_backtest
from stock_bullish.factors import add_core_factors
from stock_bullish.reporting import write_reports
from stock_bullish.strategy import StrategyRule, generate_signals

app = typer.Typer()
console = Console()


@app.command()
def version() -> None:
    console.print(__version__)


@app.command()
def research(
    input_path: Path,
    output_dir: Path = Path("outputs/research"),
    strategy_name: str = "trend_volume",
) -> None:
    config = BacktestConfig()
    prices = load_market_data(input_path)
    prices = filter_tradeable_universe(prices, config.filters)
    if prices.empty:
        summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
    else:
        prices = add_core_factors(prices)
        signals = generate_signals(
            prices,
            StrategyRule(strategy_name, ("ma_bullish", "volume_expansion"), min_score=2),
        )
        if signals.empty:
            summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
        else:
            results = run_backtest(prices, signals, config)
            summary = summarize_backtest(results)
            if summary.empty:
                summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
    paths = write_reports(summary, output_dir)
    console.print(f"Wrote reports: {paths}")

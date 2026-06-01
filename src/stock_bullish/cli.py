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
from stock_bullish.strategy import generate_signals, get_strategy_rules

app = typer.Typer()
console = Console()


@app.command()
def version() -> None:
    console.print(__version__)


@app.command()
def research(
    input_path: Path,
    output_dir: Path = Path("outputs/research"),
    strategy_name: str = "all",
) -> None:
    config = BacktestConfig()
    try:
        rules = get_strategy_rules(strategy_name)
    except ValueError as exc:
        raise typer.BadParameter(str(exc), param_hint="--strategy-name") from exc
    prices = load_market_data(input_path)
    prices = filter_tradeable_universe(prices, config.filters)
    if prices.empty:
        summary = pd.DataFrame(columns=SUMMARY_COLUMNS)
    else:
        prices = add_core_factors(prices)
        signals = pd.concat(
            [generate_signals(prices, rule) for rule in rules],
            ignore_index=True,
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

# stock-bullish

[![CI](https://github.com/avisii1680769-cell/codex/actions/workflows/ci.yml/badge.svg)](https://github.com/avisii1680769-cell/codex/actions/workflows/ci.yml)

Python research tool for screening A-share bullish signals and evaluating them with historical backtests.

## Installation

```powershell
python -m pip install -e ".[dev]"
```

## Usage

Run the end-to-end research command against the bundled sample data:

```powershell
stock-bullish research examples/sample_prices.csv --output-dir outputs/research
```

By default, `research` evaluates all built-in strategy presets. To run one preset:

```powershell
stock-bullish research examples/sample_prices.csv --output-dir outputs/research --strategy-name trend_volume
```

The command writes:

- `outputs/research/summary.csv`
- `outputs/research/summary.md`
- `outputs/research/signals.csv`
- `outputs/research/backtest_results.csv`
- `outputs/research/stability.csv`

Empty reports are valid when the input data does not produce matching strategy signals. The CSV still keeps the standard summary header.

Use `examples/market_data_template.csv` as a template for real daily market data. See `docs/data-input-template.md` for field definitions and examples.

## Strategy Presets

- `trend_volume`: moving averages are aligned upward and volume is expanding.
- `breakout_momentum`: moving-average breakout, volume expansion, and recent momentum.
- `capital_inflow`: amount expansion, turnover spike, and consecutive amount inflow.
- `balanced`: a broader score across trend, breakout, volume, amount, and volatility contraction.

Use `--strategy-name all` to compare every preset in one report. This is the default.

## Input Data

Market data can be provided as CSV or Parquet. The standard fields are:

- `trade_date`: trading date.
- `symbol`: stock symbol, such as `000001.SZ`.
- `open`, `high`, `low`, `close`: daily price fields.
- `volume`: daily trading volume.
- `amount`: daily traded amount.
- `is_st`: whether the stock is ST or special-treatment.
- `is_suspended`: whether the stock is suspended.
- `is_delisted`: whether the stock is delisted.
- `listing_days`: number of days since listing.
- `industry`: industry label used for grouping or later analysis.
- `market_cap`: market capitalization.

The required loading fields are `trade_date`, `symbol`, `open`, `high`, `low`, `close`, `volume`, and `amount`. The optional metadata fields are used by cleaning filters and reporting context when present.

## Success Rate Definitions

Research output is grouped by `strategy` and holding `window`.

- `sample_count`: number of evaluated signal samples in the group.
- `fixed_target_success_rate`: share of samples whose maximum future high within the window reached the configured fixed return target.
- `path_success_rate`: share of samples whose path hit the configured take-profit threshold before the stop-loss threshold. Samples that hit neither threshold end at the window close and are not counted as path successes.
- `average_return`, `median_return`, `worst_return`, `best_return`: return statistics measured from signal close to the window-end close.
- `unstable_sample`: `true` when `sample_count` is below 30, meaning the sample size is too small for stable interpretation.

The detail files are:

- `signals.csv`: every historical signal date, symbol, entry close, strategy, matched conditions, and optional context such as industry and market cap.
- `backtest_results.csv`: one row per signal and holding window, including fixed-target success, path success, returns, and exit reason.
- `stability.csv`: grouped checks by year, industry, and market-cap bucket when those fields are available.

## Tests

Run the full test suite:

```powershell
python -m pytest
```

Run lint checks:

```powershell
python -m ruff check src tests
```

## Risk Notice

This tool is only for historical backtesting research and does not constitute investment advice. Historical results do not represent future returns.

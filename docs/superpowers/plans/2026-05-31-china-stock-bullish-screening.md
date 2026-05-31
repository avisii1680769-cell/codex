# 中国股票看涨成功率筛选工具 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 构建一个 Python 第一版 A 股看涨信号回测研究工具，支持标准行情数据导入、因子计算、信号组合、5/20/60 日回测、成功率评估和命令行报告。

**架构：** 采用小型 Python 包结构，核心逻辑与 CLI 分离。数据模型、清洗、因子、策略、回测和评估各自独立，所有计算通过 pandas DataFrame 传递。第一版以 CLI 输出 CSV/Markdown 报告为主，保留后续看板扩展点。

**技术栈：** Python 3.11+、pandas、numpy、pyarrow、pytest、ruff、typer、rich。

---

## 文件结构

创建以下文件：

- `pyproject.toml`：项目元数据、依赖、测试和 lint 配置。
- `README.md`：本地安装、数据格式、运行示例和风险提示。
- `src/stock_bullish/__init__.py`：包版本和公共导出。
- `src/stock_bullish/schema.py`：标准行情字段、信号字段、回测结果字段常量。
- `src/stock_bullish/config.py`：默认股票池、窗口、成功阈值、交易成本配置。
- `src/stock_bullish/data_loader.py`：CSV/Parquet 本地数据读取和字段标准化。
- `src/stock_bullish/data_cleaner.py`：ST、停牌、退市、低流动性、上市天数过滤。
- `src/stock_bullish/factors.py`：技术面和交易面因子计算。
- `src/stock_bullish/strategy.py`：因子条件组合与看涨信号生成。
- `src/stock_bullish/backtest.py`：固定目标和止盈止损路径回测。
- `src/stock_bullish/evaluation.py`：胜率、收益、回撤、分组稳定性指标。
- `src/stock_bullish/reporting.py`：Markdown 和 CSV 报告输出。
- `src/stock_bullish/cli.py`：命令行入口。
- `tests/conftest.py`：测试样例数据构造器。
- `tests/test_data_loader.py`：数据读取测试。
- `tests/test_data_cleaner.py`：清洗过滤测试。
- `tests/test_factors.py`：因子计算测试。
- `tests/test_strategy.py`：信号组合测试。
- `tests/test_backtest.py`：回测成功定义测试。
- `tests/test_evaluation.py`：评估指标测试。
- `tests/test_cli.py`：CLI 冒烟测试。
- `examples/sample_prices.csv`：最小示例行情数据。

## 数据契约

标准行情输入字段：

- `trade_date`：交易日期，格式 `YYYY-MM-DD`
- `symbol`：股票代码，例如 `000001.SZ`
- `open`：开盘价
- `high`：最高价
- `low`：最低价
- `close`：收盘价
- `volume`：成交量
- `amount`：成交额
- `is_st`：是否 ST
- `is_suspended`：是否停牌
- `is_delisted`：是否退市或退市整理
- `listing_days`：上市以来交易天数
- `industry`：行业
- `market_cap`：市值

所有模块都使用标准字段名。第三方接口适配器在第一版之后添加，但必须转换为该格式。

## 任务 1：项目脚手架和基础配置

**文件：**
- 创建：`pyproject.toml`
- 创建：`README.md`
- 创建：`src/stock_bullish/__init__.py`
- 创建：`src/stock_bullish/schema.py`
- 创建：`src/stock_bullish/config.py`

- [ ] **步骤 1：编写失败的导入测试**

创建 `tests/test_imports.py`：

```python
from stock_bullish.config import BacktestConfig
from stock_bullish.schema import PRICE_COLUMNS


def test_package_imports_config_and_schema():
    config = BacktestConfig()
    assert config.windows == (5, 20, 60)
    assert "close" in PRICE_COLUMNS
```

- [ ] **步骤 2：运行测试确认失败**

运行：

```powershell
python -m pytest tests/test_imports.py -v
```

预期：失败，原因是 `stock_bullish` 包和配置文件尚未创建。

- [ ] **步骤 3：实现项目配置和基础模块**

`pyproject.toml`：

```toml
[project]
name = "stock-bullish"
version = "0.1.0"
description = "A-share bullish signal backtesting research tool"
requires-python = ">=3.11"
dependencies = [
  "numpy>=1.26",
  "pandas>=2.2",
  "pyarrow>=15.0",
  "typer>=0.12",
  "rich>=13.7"
]

[project.optional-dependencies]
dev = [
  "pytest>=8.0",
  "ruff>=0.5"
]

[project.scripts]
stock-bullish = "stock_bullish.cli:app"

[tool.pytest.ini_options]
pythonpath = ["src"]
testpaths = ["tests"]

[tool.ruff]
line-length = 100
target-version = "py311"
```

`src/stock_bullish/__init__.py`：

```python
__version__ = "0.1.0"
```

`src/stock_bullish/schema.py`：

```python
PRICE_COLUMNS = ("open", "high", "low", "close")
MARKET_COLUMNS = ("volume", "amount")
META_COLUMNS = (
    "trade_date",
    "symbol",
    "is_st",
    "is_suspended",
    "is_delisted",
    "listing_days",
    "industry",
    "market_cap",
)
REQUIRED_COLUMNS = ("trade_date", "symbol", *PRICE_COLUMNS, *MARKET_COLUMNS)

SIGNAL_DATE = "signal_date"
WINDOW = "window"
FIXED_TARGET_SUCCESS = "fixed_target_success"
PATH_SUCCESS = "path_success"
WINDOW_RETURN = "window_return"
```

`src/stock_bullish/config.py`：

```python
from dataclasses import dataclass, field


@dataclass(frozen=True)
class CostConfig:
    commission_rate: float = 0.0003
    slippage_rate: float = 0.0005


@dataclass(frozen=True)
class FilterConfig:
    exclude_st: bool = True
    exclude_suspended: bool = True
    exclude_delisted: bool = True
    min_listing_days: int = 120
    liquidity_lookback: int = 20
    min_avg_amount: float = 30_000_000


@dataclass(frozen=True)
class BacktestConfig:
    windows: tuple[int, ...] = (5, 20, 60)
    fixed_return_targets: dict[int, float] = field(
        default_factory=lambda: {5: 0.03, 20: 0.08, 60: 0.15}
    )
    stop_loss: float = 0.04
    take_profit_loss_ratio: float = 2.0
    costs: CostConfig = field(default_factory=CostConfig)
    filters: FilterConfig = field(default_factory=FilterConfig)
```

`README.md` 写明：该工具只做历史回测研究，不构成投资建议；历史结果不代表未来收益。

- [ ] **步骤 4：运行测试确认通过**

运行：

```powershell
python -m pytest tests/test_imports.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add pyproject.toml README.md src/stock_bullish tests/test_imports.py
git commit -m "chore: scaffold stock bullish research package"
```

## 任务 2：本地数据读取和标准化

**文件：**
- 创建：`src/stock_bullish/data_loader.py`
- 创建：`tests/test_data_loader.py`
- 创建：`examples/sample_prices.csv`

- [ ] **步骤 1：编写 CSV 和 Parquet 读取测试**

```python
from pathlib import Path

import pandas as pd

from stock_bullish.data_loader import load_market_data


def test_load_csv_market_data_normalizes_dates(tmp_path: Path):
    path = tmp_path / "prices.csv"
    path.write_text(
        "trade_date,symbol,open,high,low,close,volume,amount\n"
        "2026-01-02,000001.SZ,10,11,9.8,10.5,100000,120000000\n",
        encoding="utf-8",
    )

    df = load_market_data(path)

    assert list(df["symbol"]) == ["000001.SZ"]
    assert str(df["trade_date"].dt.date.iloc[0]) == "2026-01-02"
    assert df["close"].iloc[0] == 10.5


def test_load_parquet_market_data(tmp_path: Path):
    path = tmp_path / "prices.parquet"
    pd.DataFrame(
        {
            "trade_date": ["2026-01-02"],
            "symbol": ["000001.SZ"],
            "open": [10.0],
            "high": [11.0],
            "low": [9.8],
            "close": [10.5],
            "volume": [100000],
            "amount": [120000000],
        }
    ).to_parquet(path)

    df = load_market_data(path)

    assert df.shape[0] == 1
    assert df["trade_date"].dt.year.iloc[0] == 2026
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_data_loader.py -v
```

预期：失败，原因是 `load_market_data` 尚未实现。

- [ ] **步骤 3：实现数据读取**

```python
from pathlib import Path

import pandas as pd

from stock_bullish.schema import REQUIRED_COLUMNS


def load_market_data(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        df = pd.read_csv(source)
    elif source.suffix.lower() in {".parquet", ".pq"}:
        df = pd.read_parquet(source)
    else:
        raise ValueError(f"Unsupported market data file type: {source.suffix}")

    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    df = df.sort_values(["symbol", "trade_date"]).reset_index(drop=True)
    return df
```

创建 `examples/sample_prices.csv`，至少包含 2 只股票、10 个交易日数据，字段使用数据契约。

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_data_loader.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add src/stock_bullish/data_loader.py tests/test_data_loader.py examples/sample_prices.csv
git commit -m "feat: load local market data files"
```

## 任务 3：数据清洗和可交易样本过滤

**文件：**
- 创建：`src/stock_bullish/data_cleaner.py`
- 创建：`tests/test_data_cleaner.py`

- [ ] **步骤 1：编写过滤测试**

```python
import pandas as pd

from stock_bullish.config import FilterConfig
from stock_bullish.data_cleaner import filter_tradeable_universe


def test_filter_tradeable_universe_removes_untradeable_rows():
    df = pd.DataFrame(
        {
            "trade_date": pd.to_datetime(["2026-01-02"] * 4),
            "symbol": ["A", "B", "C", "D"],
            "open": [10, 10, 10, 10],
            "high": [11, 11, 11, 11],
            "low": [9, 9, 9, 9],
            "close": [10, 10, 10, 10],
            "volume": [1, 1, 1, 1],
            "amount": [100_000_000, 100_000_000, 100_000_000, 1_000_000],
            "is_st": [False, True, False, False],
            "is_suspended": [False, False, True, False],
            "is_delisted": [False, False, False, False],
            "listing_days": [200, 200, 200, 200],
        }
    )

    result = filter_tradeable_universe(
        df,
        FilterConfig(liquidity_lookback=1, min_avg_amount=30_000_000),
    )

    assert list(result["symbol"]) == ["A"]
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_data_cleaner.py -v
```

预期：失败，原因是清洗函数尚未实现。

- [ ] **步骤 3：实现过滤逻辑**

```python
import pandas as pd

from stock_bullish.config import FilterConfig


def filter_tradeable_universe(df: pd.DataFrame, config: FilterConfig) -> pd.DataFrame:
    result = df.copy()

    if config.exclude_st and "is_st" in result.columns:
        result = result[~result["is_st"].fillna(False)]
    if config.exclude_suspended and "is_suspended" in result.columns:
        result = result[~result["is_suspended"].fillna(False)]
    if config.exclude_delisted and "is_delisted" in result.columns:
        result = result[~result["is_delisted"].fillna(False)]
    if "listing_days" in result.columns:
        result = result[result["listing_days"] >= config.min_listing_days]

    result = result.sort_values(["symbol", "trade_date"]).copy()
    result["avg_amount"] = (
        result.groupby("symbol")["amount"]
        .transform(lambda s: s.rolling(config.liquidity_lookback, min_periods=1).mean())
    )
    result = result[result["avg_amount"] >= config.min_avg_amount]
    return result.drop(columns=["avg_amount"]).reset_index(drop=True)
```

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_data_cleaner.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add src/stock_bullish/data_cleaner.py tests/test_data_cleaner.py
git commit -m "feat: filter tradeable stock universe"
```

## 任务 4：技术面和交易面因子

**文件：**
- 创建：`src/stock_bullish/factors.py`
- 创建：`tests/test_factors.py`

- [ ] **步骤 1：编写因子测试**

```python
import pandas as pd

from stock_bullish.factors import add_core_factors


def test_add_core_factors_marks_moving_average_breakout():
    df = pd.DataFrame(
        {
            "trade_date": pd.date_range("2026-01-01", periods=25, freq="D"),
            "symbol": ["A"] * 25,
            "open": list(range(10, 35)),
            "high": list(range(11, 36)),
            "low": list(range(9, 34)),
            "close": list(range(10, 35)),
            "volume": [100] * 20 + [300] * 5,
            "amount": [10_000_000] * 20 + [50_000_000] * 5,
        }
    )

    result = add_core_factors(df)

    assert "ma5" in result.columns
    assert "ma20" in result.columns
    assert "ma_bullish" in result.columns
    assert "volume_expansion" in result.columns
    assert result["ma_bullish"].iloc[-1]
    assert result["volume_expansion"].iloc[-1]
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_factors.py -v
```

预期：失败，原因是 `add_core_factors` 尚未实现。

- [ ] **步骤 3：实现核心因子**

```python
import pandas as pd


def add_core_factors(df: pd.DataFrame) -> pd.DataFrame:
    result = df.sort_values(["symbol", "trade_date"]).copy()
    grouped = result.groupby("symbol", group_keys=False)

    result["ma5"] = grouped["close"].transform(lambda s: s.rolling(5, min_periods=5).mean())
    result["ma20"] = grouped["close"].transform(lambda s: s.rolling(20, min_periods=20).mean())
    result["ma60"] = grouped["close"].transform(lambda s: s.rolling(60, min_periods=60).mean())
    result["return_5d"] = grouped["close"].pct_change(5)
    result["return_20d"] = grouped["close"].pct_change(20)
    result["volatility_20d"] = grouped["close"].transform(
        lambda s: s.pct_change().rolling(20, min_periods=10).std()
    )
    result["avg_volume_20d"] = grouped["volume"].transform(
        lambda s: s.rolling(20, min_periods=5).mean()
    )
    result["avg_amount_20d"] = grouped["amount"].transform(
        lambda s: s.rolling(20, min_periods=5).mean()
    )

    result["ma_bullish"] = (result["ma5"] > result["ma20"]) & (
        result["ma60"].isna() | (result["ma20"] > result["ma60"])
    )
    result["ma_breakout"] = (result["close"] > result["ma20"]) & (
        grouped["close"].shift(1) <= grouped["ma20"].shift(1)
    )
    result["volume_expansion"] = result["volume"] >= result["avg_volume_20d"] * 1.5
    result["amount_expansion"] = result["amount"] >= result["avg_amount_20d"] * 1.5
    result["momentum_strong"] = result["return_20d"] > 0.08
    result["volatility_contraction"] = result["volatility_20d"] < grouped[
        "volatility_20d"
    ].transform(lambda s: s.rolling(60, min_periods=20).median())

    return result
```

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_factors.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add src/stock_bullish/factors.py tests/test_factors.py
git commit -m "feat: compute core bullish factors"
```

## 任务 5：策略组合和信号生成

**文件：**
- 创建：`src/stock_bullish/strategy.py`
- 创建：`tests/test_strategy.py`

- [ ] **步骤 1：编写策略测试**

```python
import pandas as pd

from stock_bullish.strategy import StrategyRule, generate_signals


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

    signals = generate_signals(df, StrategyRule(name="breakout", conditions=("ma_bullish", "volume_expansion")))

    assert signals.shape[0] == 1
    assert signals["signal_date"].dt.strftime("%Y-%m-%d").iloc[0] == "2026-01-02"
    assert signals["strategy"].iloc[0] == "breakout"
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_strategy.py -v
```

预期：失败，原因是策略模块尚未实现。

- [ ] **步骤 3：实现策略组合**

```python
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

    signals = result.loc[mask, ["trade_date", "symbol", "close", *rule.conditions]].copy()
    signals = signals.rename(columns={"trade_date": "signal_date", "close": "entry_close"})
    signals["strategy"] = rule.name
    signals["matched_conditions"] = signals[list(rule.conditions)].apply(
        lambda row: ",".join([column for column, matched in row.items() if bool(matched)]),
        axis=1,
    )
    return signals.reset_index(drop=True)
```

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_strategy.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add src/stock_bullish/strategy.py tests/test_strategy.py
git commit -m "feat: generate bullish strategy signals"
```

## 任务 6：固定目标和路径回测

**文件：**
- 创建：`src/stock_bullish/backtest.py`
- 创建：`tests/test_backtest.py`

- [ ] **步骤 1：编写回测测试**

```python
import pandas as pd

from stock_bullish.backtest import run_backtest
from stock_bullish.config import BacktestConfig


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
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_backtest.py -v
```

预期：失败，原因是回测模块尚未实现。

- [ ] **步骤 3：实现回测函数**

```python
import pandas as pd

from stock_bullish.config import BacktestConfig


def run_backtest(
    prices: pd.DataFrame,
    signals: pd.DataFrame,
    config: BacktestConfig,
) -> pd.DataFrame:
    prices_by_symbol = {
        symbol: group.sort_values("trade_date").reset_index(drop=True)
        for symbol, group in prices.groupby("symbol")
    }
    rows: list[dict] = []

    for signal in signals.to_dict("records"):
        symbol_prices = prices_by_symbol.get(signal["symbol"])
        if symbol_prices is None:
            continue

        signal_date = pd.Timestamp(signal["signal_date"])
        position = symbol_prices.index[symbol_prices["trade_date"] == signal_date]
        if len(position) == 0:
            continue

        entry_index = int(position[0])
        entry_close = float(signal["entry_close"])
        take_profit = entry_close * (1 + config.stop_loss * config.take_profit_loss_ratio)
        stop_loss = entry_close * (1 - config.stop_loss)

        for window in config.windows:
            future = symbol_prices.iloc[entry_index + 1 : entry_index + 1 + window]
            if future.empty:
                continue

            fixed_target = config.fixed_return_targets[window]
            max_return = future["high"].max() / entry_close - 1
            end_return = future["close"].iloc[-1] / entry_close - 1
            path_success = None
            exit_reason = "window_end"

            for row in future.to_dict("records"):
                if row["low"] <= stop_loss:
                    path_success = False
                    exit_reason = "stop_loss"
                    break
                if row["high"] >= take_profit:
                    path_success = True
                    exit_reason = "take_profit"
                    break

            rows.append(
                {
                    **signal,
                    "window": window,
                    "fixed_target_success": bool(max_return >= fixed_target),
                    "path_success": path_success,
                    "window_return": end_return,
                    "max_return": max_return,
                    "exit_reason": exit_reason,
                }
            )

    return pd.DataFrame(rows)
```

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_backtest.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add src/stock_bullish/backtest.py tests/test_backtest.py
git commit -m "feat: backtest bullish signal outcomes"
```

## 任务 7：评估指标和稳定性分析

**文件：**
- 创建：`src/stock_bullish/evaluation.py`
- 创建：`tests/test_evaluation.py`

- [ ] **步骤 1：编写评估测试**

```python
import pandas as pd

from stock_bullish.evaluation import summarize_backtest


def test_summarize_backtest_groups_by_strategy_and_window():
    results = pd.DataFrame(
        {
            "strategy": ["demo", "demo", "demo"],
            "window": [5, 5, 20],
            "fixed_target_success": [True, False, True],
            "path_success": [True, False, None],
            "window_return": [0.05, -0.02, 0.12],
        }
    )

    summary = summarize_backtest(results)

    row = summary[(summary["strategy"] == "demo") & (summary["window"] == 5)].iloc[0]
    assert row["sample_count"] == 2
    assert row["fixed_target_success_rate"] == 0.5
    assert row["average_return"] == 0.015
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_evaluation.py -v
```

预期：失败，原因是评估模块尚未实现。

- [ ] **步骤 3：实现汇总评估**

```python
import pandas as pd


def summarize_backtest(results: pd.DataFrame) -> pd.DataFrame:
    grouped = results.groupby(["strategy", "window"], dropna=False)
    summary = grouped.agg(
        sample_count=("window_return", "size"),
        fixed_target_success_rate=("fixed_target_success", "mean"),
        path_success_rate=("path_success", "mean"),
        average_return=("window_return", "mean"),
        median_return=("window_return", "median"),
        worst_return=("window_return", "min"),
        best_return=("window_return", "max"),
    ).reset_index()
    summary["unstable_sample"] = summary["sample_count"] < 30
    return summary
```

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_evaluation.py -v
```

预期：通过。

- [ ] **步骤 5：Commit**

```powershell
git add src/stock_bullish/evaluation.py tests/test_evaluation.py
git commit -m "feat: summarize backtest performance"
```

## 任务 8：报告输出和 CLI

**文件：**
- 创建：`src/stock_bullish/reporting.py`
- 创建：`src/stock_bullish/cli.py`
- 创建：`tests/test_cli.py`

- [ ] **步骤 1：编写 CLI 冒烟测试**

```python
from typer.testing import CliRunner

from stock_bullish.cli import app


def test_cli_version_runs():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output
```

- [ ] **步骤 2：运行测试确认失败**

```powershell
python -m pytest tests/test_cli.py -v
```

预期：失败，原因是 CLI 尚未实现。

- [ ] **步骤 3：实现报告和 CLI**

`reporting.py`：

```python
from pathlib import Path

import pandas as pd


def write_reports(summary: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    csv_path = target / "summary.csv"
    md_path = target / "summary.md"

    summary.to_csv(csv_path, index=False, encoding="utf-8-sig")
    md_path.write_text(summary.to_markdown(index=False), encoding="utf-8")
    return {"csv": csv_path, "markdown": md_path}
```

`cli.py`：

```python
from pathlib import Path

import typer
from rich.console import Console

from stock_bullish import __version__
from stock_bullish.backtest import run_backtest
from stock_bullish.config import BacktestConfig
from stock_bullish.data_cleaner import filter_tradeable_universe
from stock_bullish.data_loader import load_market_data
from stock_bullish.evaluation import summarize_backtest
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
    prices = add_core_factors(prices)
    signals = generate_signals(
        prices,
        StrategyRule(strategy_name, ("ma_bullish", "volume_expansion"), min_score=2),
    )
    results = run_backtest(prices, signals, config)
    summary = summarize_backtest(results)
    paths = write_reports(summary, output_dir)
    console.print(f"Wrote reports: {paths}")
```

- [ ] **步骤 4：运行测试确认通过**

```powershell
python -m pytest tests/test_cli.py -v
```

预期：通过。

- [ ] **步骤 5：运行示例命令**

```powershell
python -m stock_bullish.cli research examples/sample_prices.csv --output-dir outputs/research
```

预期：生成 `outputs/research/summary.csv` 和 `outputs/research/summary.md`。

- [ ] **步骤 6：Commit**

```powershell
git add src/stock_bullish/reporting.py src/stock_bullish/cli.py tests/test_cli.py
git commit -m "feat: add research CLI reports"
```

## 任务 9：端到端验证和文档补齐

**文件：**
- 修改：`README.md`
- 修改：`examples/sample_prices.csv`

- [ ] **步骤 1：补齐 README 使用说明**

README 必须包含：

- 安装命令：`python -m pip install -e ".[dev]"`
- 测试命令：`python -m pytest`
- 示例命令：`stock-bullish research examples/sample_prices.csv --output-dir outputs/research`
- 标准数据字段说明
- 成功率口径说明
- 风险提示：本工具不构成投资建议，历史回测不代表未来收益

- [ ] **步骤 2：运行完整测试**

```powershell
python -m pytest
```

预期：全部通过。

- [ ] **步骤 3：运行 lint**

```powershell
python -m ruff check src tests
```

预期：无 lint 错误。

- [ ] **步骤 4：运行端到端示例**

```powershell
stock-bullish research examples/sample_prices.csv --output-dir outputs/research
```

预期：CLI 正常结束，输出 `summary.csv` 和 `summary.md`，其中每条结果包含 `strategy`、`window`、`sample_count`、`fixed_target_success_rate`、`path_success_rate` 和 `unstable_sample`。

- [ ] **步骤 5：Commit**

```powershell
git add README.md examples/sample_prices.csv outputs/research
git commit -m "docs: document stock bullish research workflow"
```

## 自检结果

规格覆盖：

- 股票池和过滤：任务 3 覆盖。
- 本地数据优先：任务 2 覆盖。
- 第三方接口适配：第一版保留接口边界，不实现，符合规格。
- 技术面和交易面因子：任务 4 覆盖第一批核心因子。
- 策略组合：任务 5 覆盖。
- 5/20/60 日回测：任务 6 覆盖。
- 固定收益目标和路径成功：任务 6 覆盖。
- 评估指标和样本不足标记：任务 7 覆盖。
- CLI 报告：任务 8 覆盖。
- 文档和风险提示：任务 9 覆盖。

范围控制：

- 不实现自动交易。
- 不实现实盘荐股看板。
- 不实现机器学习。
- 不实现完整基本面因子库。
- 不实现第三方接口同步。

执行注意：

- 当前 Windows 环境可能没有 `git` 命令；若没有 Git，跳过 commit 步骤，但保留每个任务的提交边界。
- 若 `python` 不可用，先使用本机实际 Python 解释器路径替代命令。
- 示例数据必须足够触发至少一个策略信号，否则端到端报告可能为空。

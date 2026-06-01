import pandas as pd
from typer.testing import CliRunner

from stock_bullish.cli import app
from stock_bullish.evaluation import SUMMARY_COLUMNS
from stock_bullish.reporting import write_research_reports


def test_cli_version_runs():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_write_research_reports_creates_csv_and_markdown(tmp_path):
    summary = pd.DataFrame(
        {
            "strategy": ["trend_volume"],
            "window": [5],
            "sample_count": [1],
        }
    )

    paths = write_research_reports(summary=summary, output_dir=tmp_path)

    assert paths == {
        "summary_csv": tmp_path / "summary.csv",
        "summary_markdown": tmp_path / "summary.md",
    }
    assert paths["summary_csv"].exists()
    assert paths["summary_markdown"].exists()
    assert pd.read_csv(paths["summary_csv"]).to_dict("records") == summary.to_dict("records")
    assert paths["summary_markdown"].read_text(encoding="utf-8") == summary.to_markdown(index=False)


def test_write_research_reports_writes_optional_detail_frames(tmp_path):
    signals = pd.DataFrame({"strategy": ["trend_volume"], "symbol": ["000001.SZ"]})
    backtest_results = pd.DataFrame(
        {"strategy": ["trend_volume"], "window": [5], "window_return": [0.01]}
    )
    stability = pd.DataFrame(
        {"group_type": ["year"], "group_value": ["2026"], "strategy": ["trend_volume"]}
    )

    paths = write_research_reports(
        summary=pd.DataFrame(),
        output_dir=tmp_path,
        signals=signals,
        backtest_results=backtest_results,
        stability=stability,
    )

    assert paths["signals_csv"] == tmp_path / "signals.csv"
    assert paths["backtest_results_csv"] == tmp_path / "backtest_results.csv"
    assert paths["stability_csv"] == tmp_path / "stability.csv"
    assert pd.read_csv(paths["signals_csv"]).to_dict("records") == signals.to_dict("records")


def test_cli_research_writes_reports(tmp_path):
    runner = CliRunner()
    output_dir = tmp_path / "research"

    result = runner.invoke(
        app,
        [
            "research",
            "examples/sample_prices.csv",
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "summary.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert (output_dir / "signals.csv").exists()
    assert (output_dir / "backtest_results.csv").exists()
    assert (output_dir / "stability.csv").exists()
    assert "summary.csv" in result.output
    assert "summary.md" in result.output


def test_cli_research_accepts_single_strategy_preset(tmp_path):
    runner = CliRunner()
    output_dir = tmp_path / "research"

    result = runner.invoke(
        app,
        [
            "research",
            "examples/sample_prices.csv",
            "--output-dir",
            str(output_dir),
            "--strategy-name",
            "trend_volume",
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "summary.csv").exists()


def test_cli_research_rejects_unknown_strategy_preset(tmp_path):
    runner = CliRunner()
    output_dir = tmp_path / "research"

    result = runner.invoke(
        app,
        [
            "research",
            "examples/sample_prices.csv",
            "--output-dir",
            str(output_dir),
            "--strategy-name",
            "missing",
        ],
    )

    assert result.exit_code != 0
    assert "Unknown strategy preset: missing" in result.output


def test_cli_research_writes_empty_summary_for_header_only_csv(tmp_path):
    runner = CliRunner()
    input_path = tmp_path / "empty_prices.csv"
    output_dir = tmp_path / "research"
    input_path.write_text(
        "trade_date,symbol,open,high,low,close,volume,amount\n",
        encoding="utf-8",
    )

    result = runner.invoke(
        app,
        [
            "research",
            str(input_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    assert result.exit_code == 0
    assert (output_dir / "summary.csv").exists()
    assert (output_dir / "summary.md").exists()
    assert pd.read_csv(output_dir / "summary.csv").columns.tolist() == SUMMARY_COLUMNS

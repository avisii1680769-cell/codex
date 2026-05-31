import pandas as pd
from typer.testing import CliRunner

from stock_bullish.cli import app
from stock_bullish.evaluation import SUMMARY_COLUMNS
from stock_bullish.reporting import write_reports


def test_cli_version_runs():
    runner = CliRunner()
    result = runner.invoke(app, ["version"])

    assert result.exit_code == 0
    assert "0.1.0" in result.output


def test_write_reports_creates_csv_and_markdown(tmp_path):
    summary = pd.DataFrame(
        {
            "strategy": ["trend_volume"],
            "window": [5],
            "sample_count": [1],
        }
    )

    paths = write_reports(summary, tmp_path)

    assert paths == {
        "csv": tmp_path / "summary.csv",
        "markdown": tmp_path / "summary.md",
    }
    assert paths["csv"].exists()
    assert paths["markdown"].exists()
    assert pd.read_csv(paths["csv"]).to_dict("records") == summary.to_dict("records")
    assert paths["markdown"].read_text(encoding="utf-8") == summary.to_markdown(index=False)


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
    assert "summary.csv" in result.output
    assert "summary.md" in result.output


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

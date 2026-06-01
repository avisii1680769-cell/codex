from pathlib import Path

from stock_bullish.research import run_research


def test_run_research_returns_all_report_frames(tmp_path: Path):
    output = run_research(
        input_path=Path("examples/market_data_template.csv"),
        output_dir=tmp_path,
        strategy_name="all",
    )

    assert output.summary is not None
    assert output.signals is not None
    assert output.backtest_results is not None
    assert output.stability is not None
    assert output.paths["summary_csv"] == tmp_path / "summary.csv"
    assert output.paths["signals_csv"] == tmp_path / "signals.csv"


def test_run_research_rejects_unknown_strategy(tmp_path: Path):
    try:
        run_research(
            input_path=Path("examples/market_data_template.csv"),
            output_dir=tmp_path,
            strategy_name="missing",
        )
    except ValueError as exc:
        assert "Unknown strategy preset: missing" in str(exc)
    else:
        raise AssertionError("expected unknown strategy to raise ValueError")

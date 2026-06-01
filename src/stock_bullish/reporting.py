from pathlib import Path

import pandas as pd


def write_reports(summary: pd.DataFrame, output_dir: str | Path) -> dict[str, Path]:
    paths = write_research_reports(summary=summary, output_dir=output_dir)
    return {"csv": paths["summary_csv"], "markdown": paths["summary_markdown"]}


def write_research_reports(
    summary: pd.DataFrame,
    output_dir: str | Path,
    signals: pd.DataFrame | None = None,
    backtest_results: pd.DataFrame | None = None,
    stability: pd.DataFrame | None = None,
) -> dict[str, Path]:
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)

    csv_path = target / "summary.csv"
    md_path = target / "summary.md"

    summary.to_csv(csv_path, index=False, encoding="utf-8-sig")
    md_path.write_text(summary.to_markdown(index=False), encoding="utf-8")
    paths = {"summary_csv": csv_path, "summary_markdown": md_path}

    optional_reports = {
        "signals": signals,
        "backtest_results": backtest_results,
        "stability": stability,
    }
    for name, frame in optional_reports.items():
        if frame is None:
            continue
        path = target / f"{name}.csv"
        frame.to_csv(path, index=False, encoding="utf-8-sig")
        paths[f"{name}_csv"] = path

    return paths

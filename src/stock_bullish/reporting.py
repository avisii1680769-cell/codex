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

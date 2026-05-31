from pathlib import Path

import pandas as pd

from stock_bullish import schema


def load_market_data(path: str | Path) -> pd.DataFrame:
    source = Path(path)
    suffix = source.suffix.lower()

    if suffix == ".csv":
        df = pd.read_csv(source)
    elif suffix in {".parquet", ".pq"}:
        df = pd.read_parquet(source)
    else:
        raise ValueError(f"Unsupported market data file type: {source.suffix}")

    missing = [column for column in schema.REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"Missing required columns: {missing}")

    df = df.copy()
    df["trade_date"] = pd.to_datetime(df["trade_date"])
    return df.sort_values(["symbol", "trade_date"]).reset_index(drop=True)

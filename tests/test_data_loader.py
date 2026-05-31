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

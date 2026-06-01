# Market Data Input Template

Use `examples/market_data_template.csv` as the starting point for real A-share daily market data. CSV and Parquet inputs are supported.

## Required Fields

| Field | Type | Example | Notes |
|---|---:|---|---|
| `trade_date` | date | `2026-01-02` | Trading date in `YYYY-MM-DD` format. |
| `symbol` | string | `000001.SZ` | A-share symbol with exchange suffix. |
| `open` | number | `10.00` | Adjusted daily open price. |
| `high` | number | `10.30` | Adjusted daily high price. |
| `low` | number | `9.90` | Adjusted daily low price. |
| `close` | number | `10.10` | Adjusted daily close price. |
| `volume` | number | `100000` | Daily trading volume. |
| `amount` | number | `1010000` | Daily traded amount. |

## Recommended Optional Fields

| Field | Type | Example | Notes |
|---|---:|---|---|
| `is_st` | boolean | `false` | Used by the tradeable-universe filter. |
| `is_suspended` | boolean | `false` | Used by the tradeable-universe filter. |
| `is_delisted` | boolean | `false` | Used by the tradeable-universe filter. |
| `listing_days` | integer | `5200` | Used to exclude newly listed stocks. |
| `industry` | string | `bank` | Reserved for grouping and reporting context. |
| `market_cap` | number | `12000000000` | Reserved for grouping and reporting context. |
| `turnover` | number | `1.20` | Enables turnover-spike factor calculation. |

## Running Research

```powershell
stock-bullish research path\to\market_data.csv --output-dir outputs/research
```

The tool expects one row per `symbol` and `trade_date`. Sort order is not required; the loader sorts by `symbol` and `trade_date`.

The default command evaluates all built-in strategy presets. Use `--strategy-name trend_volume`, `--strategy-name breakout_momentum`, `--strategy-name capital_inflow`, or `--strategy-name balanced` to run one preset.

import pandas as pd

from stock_bullish.live import rank_live_candidates


def test_rank_live_candidates_scores_short_mid_long_candidates():
    spot = pd.DataFrame(
        {
            "代码": ["000001", "000002", "600000"],
            "名称": ["强势股", "平稳股", "弱势股"],
            "最新价": [10.0, 20.0, 8.0],
            "涨跌幅": [4.2, 1.8, -2.0],
            "成交额": [2_000_000_000, 900_000_000, 200_000_000],
            "换手率": [7.5, 2.0, 0.5],
            "量比": [2.2, 1.1, 0.6],
            "振幅": [5.0, 2.0, 8.0],
            "市盈率-动态": [22.0, 18.0, -1.0],
            "市净率": [2.1, 1.3, 6.0],
            "总市值": [80_000_000_000, 160_000_000_000, 20_000_000_000],
        }
    )

    candidates = rank_live_candidates(spot, limit=2)

    assert set(candidates) == {"短期", "中期", "长期"}
    assert candidates["短期"].iloc[0]["代码"] == "000001"
    assert "看涨概率" in candidates["短期"].columns
    assert candidates["短期"].iloc[0]["看涨概率"] > candidates["短期"].iloc[1]["看涨概率"]
    assert candidates["长期"].iloc[0]["代码"] == "000002"


def test_rank_live_candidates_returns_stable_columns_for_empty_input():
    candidates = rank_live_candidates(pd.DataFrame(), limit=5)

    assert candidates["短期"].empty
    assert candidates["短期"].columns.tolist() == [
        "周期",
        "排名",
        "代码",
        "名称",
        "最新价",
        "涨跌幅",
        "成交额",
        "换手率",
        "量比",
        "振幅",
        "看涨概率",
        "评分",
        "入选理由",
    ]

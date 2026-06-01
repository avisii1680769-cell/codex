import pandas as pd

from stock_bullish import live
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
    assert "看涨评分" in candidates["短期"].columns
    assert candidates["短期"].iloc[0]["看涨评分"] > candidates["短期"].iloc[1]["看涨评分"]
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
        "看涨评分",
        "技术面评分",
        "基本面评分",
        "财报质量评分",
        "评分",
        "技术面分析",
        "基本面分析",
        "利润分析",
        "负债分析",
        "现金流分析",
        "行业景气分析",
        "公告新闻风险",
        "入选理由",
    ]


def test_rank_live_candidates_uses_technical_and_fundamental_scores():
    spot = pd.DataFrame(
        {
            "代码": ["000001", "000002"],
            "名称": ["技术基本面共振", "只有技术强"],
            "最新价": [10.0, 20.0],
            "涨跌幅": [3.2, 5.8],
            "成交额": [1_500_000_000, 1_800_000_000],
            "换手率": [4.5, 7.0],
            "量比": [1.8, 2.3],
            "振幅": [4.0, 7.0],
            "市盈率-动态": [18.0, 120.0],
            "市净率": [1.4, 12.0],
            "总市值": [120_000_000_000, 5_000_000_000],
            "净利润": [5_000_000_000, -300_000_000],
            "营收": [30_000_000_000, 2_000_000_000],
            "净利润同比": [12.0, -40.0],
            "资产负债率": [45.0, 92.0],
            "经营现金流": [4_000_000_000, -2_000_000_000],
            "行业": ["银行", "高风险行业"],
        }
    )

    candidates = rank_live_candidates(spot, limit=2)
    first_mid = candidates["中期"].iloc[0]

    assert first_mid["代码"] == "000001"
    assert first_mid["技术面评分"] > 0
    assert first_mid["基本面评分"] > 0
    assert "技术面：" in first_mid["技术面分析"]
    assert "基本面：" in first_mid["基本面分析"]
    assert "利润：" in first_mid["利润分析"]
    assert "负债：" in first_mid["负债分析"]
    assert "现金流：" in first_mid["现金流分析"]
    assert "行业景气：" in first_mid["行业景气分析"]


def test_enrich_selected_risks_adds_announcement_risk(monkeypatch):
    candidates = {
        "短期": pd.DataFrame(
            {
                "代码": ["000001"],
                "名称": ["风险股"],
                "周期": ["短期"],
                "排名": [1],
            }
        )
    }

    monkeypatch.setattr(live, "_fetch_recent_announcement_titles", lambda code: ["公司收到监管问询函"])

    enriched = live._enrich_selected_risks(candidates)

    assert "公告新闻风险" in enriched["短期"].columns
    assert "风险词" in enriched["短期"].iloc[0]["公告新闻风险"]


def test_fetch_live_spot_tries_next_eastmoney_host_before_cache(monkeypatch):
    sample = pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})
    attempts = []
    writes = []

    def fake_fetch(host: str) -> pd.DataFrame:
        attempts.append(host)
        if len(attempts) == 1:
            raise RuntimeError("first host failed")
        return sample

    monkeypatch.setattr(live, "_fetch_eastmoney_spot", fake_fetch)
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda spot: spot)
    monkeypatch.setattr(live, "_read_cached_spot", lambda: None)
    monkeypatch.setattr(live, "_write_cached_spot", writes.append)

    result = live.fetch_live_spot()

    assert result.equals(sample)
    assert attempts == list(live.EASTMONEY_HOSTS[:2])
    assert writes[0].equals(sample)


def test_fetch_live_spot_uses_cache_after_all_hosts_fail(monkeypatch):
    cached = pd.DataFrame({"代码": ["600000"], "名称": ["浦发银行"]})
    attempts = []

    def fake_fetch(host: str) -> pd.DataFrame:
        attempts.append(host)
        raise RuntimeError("host failed")

    monkeypatch.setattr(live, "_fetch_eastmoney_spot", fake_fetch)
    monkeypatch.setattr(
        live,
        "_fetch_tencent_spot",
        lambda: (_ for _ in ()).throw(RuntimeError("fallback failed")),
    )
    monkeypatch.setattr(live, "_read_cached_spot", lambda: cached)
    monkeypatch.setattr(live, "_write_cached_spot", lambda spot: None)

    result = live.fetch_live_spot()

    assert result.equals(cached)
    assert attempts == list(live.EASTMONEY_HOSTS)


def test_fetch_live_spot_uses_tencent_source_before_cache(monkeypatch):
    sample = pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})
    attempts = []

    def fake_fetch(host: str) -> pd.DataFrame:
        attempts.append(host)
        raise RuntimeError("host failed")

    def fail_if_cache_is_used() -> pd.DataFrame | None:
        raise AssertionError("cache should not be used when tencent source works")

    monkeypatch.setattr(live, "_fetch_eastmoney_spot", fake_fetch)
    monkeypatch.setattr(live, "_fetch_tencent_spot", lambda: sample)
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda spot: spot)
    monkeypatch.setattr(live, "_read_cached_spot", fail_if_cache_is_used)
    monkeypatch.setattr(live, "_write_cached_spot", lambda spot: None)

    result = live.fetch_live_spot()

    assert result.equals(sample)
    assert attempts == list(live.EASTMONEY_HOSTS)

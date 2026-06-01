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
        "应收账款风险",
        "存货风险",
        "商誉风险",
        "非经常性损益分析",
        "ROE趋势分析",
        "多年增长分析",
        "行业估值分位",
        "政策周期分析",
        "全网新闻舆情",
        "历史回测胜率校准",
        "机构持仓分析",
        "北向资金分析",
        "融资融券分析",
        "主力资金流向",
        "风险等级",
        "支持证据",
        "反对证据",
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
            "应收账款": [1_000_000_000, 900_000_000],
            "存货": [500_000_000, 1_200_000_000],
            "商誉": [200_000_000, 900_000_000],
            "扣非净利润": [4_800_000_000, -500_000_000],
            "ROE": [12.0, -3.0],
            "多年营收连续增长": [True, False],
            "多年利润连续增长": [True, False],
            "行业": ["银行", "高风险行业"],
            "公告新闻风险": ["公告/新闻风险：近期公告标题未见明显风险词。", "公告/新闻风险：近期公告含风险词。"],
            "风险等级": ["低", "高"],
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
    assert "同业样本" in first_mid["行业景气分析"]
    assert "应收账款：" in first_mid["应收账款风险"]
    assert "存货：" in first_mid["存货风险"]
    assert "商誉：" in first_mid["商誉风险"]
    assert "扣非净利润" in first_mid["非经常性损益分析"]
    assert "ROE" in first_mid["ROE趋势分析"]
    assert "多年增长：" in first_mid["多年增长分析"]
    assert "行业估值分位：" in first_mid["行业估值分位"]
    assert "政策周期：" in first_mid["政策周期分析"]
    assert "全网新闻舆情：" in first_mid["全网新闻舆情"]
    assert "历史回测：" in first_mid["历史回测胜率校准"]
    assert "机构持仓：" in first_mid["机构持仓分析"]
    assert "北向资金：" in first_mid["北向资金分析"]
    assert "融资融券：" in first_mid["融资融券分析"]
    assert "主力资金：" in first_mid["主力资金流向"]
    assert "支持证据" in first_mid
    assert "反对证据" in first_mid
    assert first_mid["支持证据"]
    assert first_mid["反对证据"]


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

    monkeypatch.setattr(live, "_fetch_market_evidence", lambda codes: pd.DataFrame(columns=["代码"]))
    monkeypatch.setattr(live, "_fetch_recent_announcement_titles", lambda code: ["公司收到监管问询函"])

    enriched = live._enrich_selected_risks(candidates)

    assert "公告新闻风险" in enriched["短期"].columns
    assert "风险等级" in enriched["短期"].columns
    assert "风险词" in enriched["短期"].iloc[0]["公告新闻风险"]
    assert enriched["短期"].iloc[0]["风险等级"] == "中"


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


def test_parse_margin_financing_rows_keeps_latest_row_per_stock():
    rows = [
        {
            "DATE": "2026-05-28 00:00:00",
            "SCODE": "000001",
            "RZYE": 100,
            "RQYE": 20,
            "RZJME": 5,
            "RZJME5D": 8,
            "RZJME10D": 13,
        },
        {
            "DATE": "2026-05-29 00:00:00",
            "SCODE": "000001",
            "RZYE": 200,
            "RQYE": 30,
            "RZJME": -6,
            "RZJME5D": -9,
            "RZJME10D": 15,
        },
    ]

    parsed = live._parse_margin_financing_rows(rows)

    assert parsed.iloc[0]["代码"] == "000001"
    assert parsed.iloc[0]["融资余额"] == 200
    assert parsed.iloc[0]["融资净买额"] == -6
    assert parsed.iloc[0]["5日融资净买额"] == -9


def test_parse_northbound_holding_rows_keeps_latest_quarterly_holding():
    rows = [
        {
            "HOLD_DATE": "2025-12-31 00:00:00",
            "SECURITY_CODE": "000001",
            "HOLD_SHARES": 100,
            "ADD_SHARES_REPAIR": 5,
            "HOLD_MARKET_CAP": 1000,
            "FREE_SHARES_RATIO": 1.2,
            "ORG_QUANTITY": 20,
            "ORG_QUANTITY_RATIO": 2.0,
        },
        {
            "HOLD_DATE": "2026-03-31 00:00:00",
            "SECURITY_CODE": "000001",
            "HOLD_SHARES": 120,
            "ADD_SHARES_REPAIR": -3,
            "HOLD_MARKET_CAP": 1300,
            "FREE_SHARES_RATIO": 1.5,
            "ORG_QUANTITY": 22,
            "ORG_QUANTITY_RATIO": 10.0,
        },
    ]

    parsed = live._parse_northbound_holding_rows(rows)

    assert parsed.iloc[0]["代码"] == "000001"
    assert parsed.iloc[0]["互联互通持股数"] == 120
    assert parsed.iloc[0]["互联互通增持股数"] == -3
    assert parsed.iloc[0]["互联互通机构数量"] == 22


def test_parse_main_fund_flow_rows_maps_push2_fields():
    rows = [
        {
            "f12": "000001",
            "f62": 112414454.0,
            "f184": 10.79,
            "f66": 59083668.0,
            "f72": 53330786.0,
            "f78": -36658864.0,
            "f84": -75755584.0,
        }
    ]

    parsed = live._parse_main_fund_flow_rows(rows)

    assert parsed.iloc[0]["代码"] == "000001"
    assert parsed.iloc[0]["主力净流入"] == 112414454.0
    assert parsed.iloc[0]["主力净占比"] == 10.79
    assert parsed.iloc[0]["大单净流入"] == 53330786.0

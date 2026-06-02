import pandas as pd

from stock_bullish import live
from stock_bullish.live import analyze_stock_code, rank_live_candidates


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
        "追高风险",
        "综合结论",
        "操作节奏",
        "核心看多理由",
        "核心反对理由",
        "失效条件",
        "支持证据",
        "反对证据",
        "建议持仓周期",
        "入选理由",
    ]


def test_analyze_stock_code_returns_three_period_report_and_best_period(monkeypatch):
    spot = pd.DataFrame(
        {
            "代码": ["000001"],
            "名称": ["平安银行"],
            "最新价": [10.0],
            "涨跌幅": [3.0],
            "成交额": [1_000_000_000],
            "换手率": [3.0],
            "量比": [1.6],
            "振幅": [4.0],
            "市盈率-动态": [7.0],
            "市净率": [0.8],
            "总市值": [200_000_000_000],
        }
    )

    monkeypatch.setattr(live, "_fetch_tencent_spot_for_codes", lambda codes: spot)
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda frame: frame)
    monkeypatch.setattr(live, "_enrich_selected_risks", lambda candidates: candidates)

    report, updated_at, metadata = analyze_stock_code("1")

    assert updated_at
    assert report["代码"].tolist() == ["000001", "000001", "000001"]
    assert set(report["周期"]) == {"短期", "中期", "长期"}
    assert metadata["query_code"] == "000001"
    assert metadata["recommended_period"] == report.sort_values("评分", ascending=False).iloc[0]["周期"]
    assert "建议持仓周期" in report.columns


def test_analyze_stock_code_falls_back_to_full_market_source(monkeypatch):
    market = pd.DataFrame(
        {
            "代码": ["000066", "000001"],
            "名称": ["中国长城", "平安银行"],
            "最新价": [12.0, 10.0],
            "涨跌幅": [2.5, 1.0],
            "成交额": [800_000_000, 300_000_000],
            "换手率": [4.0, 1.0],
            "量比": [1.5, 1.0],
            "振幅": [4.0, 2.0],
            "市盈率-动态": [32.0, 7.0],
            "市净率": [2.5, 0.8],
            "总市值": [80_000_000_000, 200_000_000_000],
        }
    )

    monkeypatch.setattr(live, "_fetch_tencent_spot_for_codes", lambda codes: pd.DataFrame())
    monkeypatch.setattr(live, "fetch_live_spot", lambda: market)
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda frame: frame)
    monkeypatch.setattr(live, "_enrich_selected_risks", lambda candidates: candidates)

    report, _, metadata = analyze_stock_code("000066")

    assert set(report["代码"]) == {"000066"}
    assert report.iloc[0]["名称"] == "中国长城"
    assert metadata["query_code"] == "000066"


def test_analyze_stock_code_accepts_single_quote_with_missing_amount(monkeypatch):
    quote = pd.DataFrame(
        {
            "代码": ["000066"],
            "名称": ["中国长城"],
            "最新价": [18.18],
            "涨跌幅": [-1.62],
            "成交额": [0.0],
            "换手率": [0.0],
            "量比": [0.0],
            "振幅": [0.0],
            "市盈率-动态": [2906.98],
            "市净率": [5.36],
            "总市值": [58_645_000_000],
        }
    )

    monkeypatch.setattr(live, "_fetch_tencent_spot_for_codes", lambda codes: quote)
    monkeypatch.setattr(live, "fetch_live_spot", lambda: pd.DataFrame())
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda frame: frame)
    monkeypatch.setattr(live, "_enrich_selected_risks", lambda candidates: candidates)

    report, _, metadata = analyze_stock_code("000066")

    assert set(report["代码"]) == {"000066"}
    assert report.iloc[0]["名称"] == "中国长城"
    assert metadata["query_code"] == "000066"


def test_analyze_stock_code_rejects_invalid_code():
    try:
        analyze_stock_code("abc")
    except ValueError as exc:
        assert "请输入 6 位 A 股股票代码" in str(exc)
    else:
        raise AssertionError("invalid code should fail")


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
    assert "综合结论" in first_mid
    assert "操作节奏" in first_mid
    assert "核心看多理由" in first_mid
    assert "核心反对理由" in first_mid
    assert "失效条件" in first_mid
    assert "建议持仓周期：" in first_mid["建议持仓周期"]
    assert first_mid["综合结论"]
    assert first_mid["操作节奏"]
    assert first_mid["失效条件"]
    assert first_mid["支持证据"]
    assert first_mid["反对证据"]


def test_holding_period_advice_varies_by_period_and_risk():
    hot_risky = pd.Series(
        {
            "换手率": 30.0,
            "量比": 6.0,
            "涨跌幅": 10.0,
            "风险等级": "低",
            "全网新闻舆情": "全网新闻舆情：新闻搜索结果含风险词，需核查。",
            "反对证据": "反对：融资资金净偿还。",
            "融资净买额": -1_000_000,
            "互联互通增持股数": -100_000,
        }
    )
    stable = pd.Series(
        {
            "换手率": 2.0,
            "量比": 1.2,
            "涨跌幅": 1.0,
            "风险等级": "低",
            "全网新闻舆情": "全网新闻舆情：新闻搜索结果未见明显风险词。",
            "反对证据": "反对：暂未发现规则内的明显反对证据。",
            "融资净买额": 1_000_000,
            "互联互通增持股数": 100_000,
        }
    )

    assert "1-2 个交易日" in live._holding_period_advice(hot_risky, "短期")
    assert "4-6 周" in live._holding_period_advice(stable, "中期")
    assert "6-12 个月" in live._holding_period_advice(stable, "长期")


def test_chase_risk_downgrades_hot_expensive_candidates():
    hot_expensive = pd.Series(
        {
            "涨跌幅": 8.5,
            "换手率": 18.0,
            "量比": 3.8,
            "市盈率-动态": 180.0,
            "市净率": 12.0,
            "风险等级": "中",
            "反对证据": "反对：融资资金净偿还；互联互通持仓减持。",
            "融资净买额": -1_000_000,
            "互联互通增持股数": -100_000,
        }
    )

    assert "高" in live._chase_risk_analysis(hot_expensive)
    assert "只适合观察" in live._operation_tempo(hot_expensive, "短期")
    assert "追高风险" in live._trading_conclusion(hot_expensive, "短期")


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
        "_fetch_akshare_spot",
        lambda: (_ for _ in ()).throw(RuntimeError("akshare failed")),
    )
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
    monkeypatch.setattr(
        live,
        "_fetch_akshare_spot",
        lambda: (_ for _ in ()).throw(RuntimeError("akshare failed")),
    )
    monkeypatch.setattr(live, "_fetch_tencent_spot", lambda: sample)
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda spot: spot)
    monkeypatch.setattr(live, "_read_cached_spot", fail_if_cache_is_used)
    monkeypatch.setattr(live, "_write_cached_spot", lambda spot: None)

    result = live.fetch_live_spot()

    assert result.equals(sample)
    assert attempts == list(live.EASTMONEY_HOSTS)


def test_fetch_live_spot_uses_akshare_full_market_before_tencent(monkeypatch):
    attempts = []
    akshare_spot = pd.DataFrame(
        {
            "代码": ["000001", "600000"],
            "名称": ["平安银行", "浦发银行"],
            "最新价": [10.0, 9.0],
            "涨跌幅": [1.2, -0.5],
            "成交额": [100_000_000, 90_000_000],
            "换手率": [1.5, 0.5],
            "量比": [1.1, 0.8],
            "振幅": [2.0, 1.5],
            "总市值": [100_000_000_000, 200_000_000_000],
            "市净率": [0.8, 0.5],
            "市盈率-动态": [6.0, 7.0],
        }
    )
    akshare_spot.attrs["raw_count"] = 5524
    akshare_spot.attrs["filtered_count"] = 2
    akshare_spot.attrs["scan_scope"] = "全A股实时行情"
    akshare_spot.attrs["data_source"] = "AkShare 新浪全市场行情"

    def fake_fetch(host: str) -> pd.DataFrame:
        attempts.append(host)
        raise RuntimeError("host failed")

    def fail_if_tencent_is_used() -> pd.DataFrame:
        raise AssertionError("tencent should not be used when akshare full market works")

    monkeypatch.setattr(live, "_fetch_eastmoney_spot", fake_fetch)
    monkeypatch.setattr(live, "_fetch_akshare_spot", lambda: akshare_spot)
    monkeypatch.setattr(live, "_fetch_tencent_spot", fail_if_tencent_is_used)
    monkeypatch.setattr(live, "_enrich_financial_evidence", lambda spot: spot)
    monkeypatch.setattr(live, "_read_cached_spot", lambda: None)
    monkeypatch.setattr(live, "_write_cached_spot", lambda spot: None)

    result = live.fetch_live_spot()

    assert result.equals(akshare_spot)
    assert result.attrs["raw_count"] == 5524
    assert result.attrs["scan_scope"] == "全A股实时行情"
    assert attempts == list(live.EASTMONEY_HOSTS)


def test_fetch_eastmoney_spot_uses_system_proxy_and_records_full_market_metadata(monkeypatch):
    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {
                "data": {
                    "total": 5857,
                    "diff": [
                        {
                            "f2": 10.0,
                            "f3": 1.2,
                            "f6": 100_000_000,
                            "f7": 2.0,
                            "f8": 1.5,
                            "f10": 1.1,
                            "f12": "000001",
                            "f14": "平安银行",
                            "f20": 100_000_000_000,
                            "f23": 0.8,
                            "f115": 6.2,
                        }
                    ],
                }
            }

    sessions = []

    class FakeSession:
        trust_env = False

        def __init__(self):
            self.headers = {}
            self.params = []
            sessions.append(self)

        def get(self, url, params, timeout):
            self.params.append(params)
            if params["pn"] == 1:
                return FakeResponse()
            return type(
                "EmptyResponse",
                (),
                {"raise_for_status": lambda self: None, "json": lambda self: {"data": {"diff": []}}},
            )()

    monkeypatch.setattr(live.requests, "Session", FakeSession)

    frame = live._fetch_eastmoney_spot()

    assert sessions[0].trust_env is True
    assert len(frame) == 1
    assert frame.attrs["raw_count"] == 5857
    assert frame.attrs["scan_scope"] == "全A股实时行情"


def test_scan_live_candidates_returns_scope_metadata(monkeypatch):
    spot = pd.DataFrame(
        {
            "代码": ["000001", "000002"],
            "名称": ["平安银行", "万科A"],
            "最新价": [10.0, 20.0],
            "涨跌幅": [1.0, 2.0],
            "成交额": [100_000_000, 200_000_000],
            "换手率": [1.0, 2.0],
            "量比": [1.0, 1.2],
            "振幅": [2.0, 3.0],
            "市盈率-动态": [6.0, 8.0],
            "市净率": [0.8, 1.0],
            "总市值": [100_000_000_000, 200_000_000_000],
        }
    )
    spot.attrs["raw_count"] = 5857
    spot.attrs["filtered_count"] = 4000
    spot.attrs["scan_scope"] = "全A股实时行情"
    spot.attrs["data_source"] = "东方财富全市场行情"

    monkeypatch.setattr(live, "fetch_live_spot", lambda: spot)
    monkeypatch.setattr(live, "_enrich_selected_risks", lambda candidates: candidates)

    candidates, updated_at, metadata = live.scan_live_candidates(limit=1)

    assert updated_at
    assert sum(len(frame) for frame in candidates.values()) == 3
    assert metadata["raw_count"] == 5857
    assert metadata["filtered_count"] == 4000
    assert metadata["deep_analysis_count"] == 2
    assert metadata["scan_scope"] == "全A股实时行情"


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


def test_parse_news_rss_titles_extracts_titles():
    payload = """<?xml version="1.0"?><rss><channel>
    <item><title>平安银行发布业绩增长公告</title></item>
    <item><title>平安银行回应监管问询</title></item>
    </channel></rss>"""

    titles = live._parse_news_rss_titles(payload)

    assert titles == ["平安银行发布业绩增长公告", "平安银行回应监管问询"]


def test_news_sentiment_analysis_reports_risk_words():
    row = pd.Series({"新闻标题列表": ["公司收到监管问询", "业绩增长"]})

    text = live._web_news_sentiment_analysis(row)

    assert "新闻舆情" in text
    assert "风险词" in text
    assert "监管问询" in text

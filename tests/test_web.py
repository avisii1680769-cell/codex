from pathlib import Path

import pandas as pd

from stock_bullish import web
from stock_bullish.web import render_home_page, render_live_result_page, render_stock_report_page


def test_render_home_page_is_chinese_live_scanner_without_upload_form():
    candidates = {
        "短期": pd.DataFrame(
            {
                "周期": ["短期"],
                "排名": [1],
                "代码": ["000001"],
                "名称": ["平安银行"],
                "看涨评分": [78.0],
                "技术面评分": [82.0],
                "基本面评分": [66.0],
                "技术面分析": ["技术面：量比活跃，成交额较高。"],
                "基本面分析": ["基本面：估值处在规则区间，市值规模较稳定。"],
                "入选理由": ["技术面与基本面共同支持"],
            }
        ),
        "中期": pd.DataFrame(),
        "长期": pd.DataFrame(),
    }

    html = render_home_page(
        candidates=candidates,
        updated_at="2026-06-01 10:00:00",
        metadata={
            "scan_scope": "全A股实时行情",
            "raw_count": 5857,
            "filtered_count": 4000,
            "deep_analysis_count": 15,
            "data_source": "东方财富全市场行情",
            "data_state": "最新扫描完成",
        },
    )

    assert 'type="file"' not in html
    assert "实时扫描" not in html
    assert "短期候选" in html
    assert "中期候选" in html
    assert "长期候选" in html
    assert "固定展示每个周期 5 只" in html
    assert "全A股实时行情" in html
    assert "5857" in html
    assert "4000" in html
    assert "15" in html
    assert "看涨评分" in html
    assert "技术面评分" in html
    assert "基本面评分" in html
    assert "技术面：" in html
    assert "基本面：" in html
    assert "融资融券" in html
    assert "规则评分，不是预测概率" in html
    assert "已接入口径与仍未打通因素" in html
    assert "未找到足够稳定的结构化接口" in html
    assert "数据来源与覆盖范围" in html
    assert "当前数据状态" in html
    assert "最新扫描完成" in html
    assert "看涨概率" not in html
    assert "推荐股票" not in html


def test_render_live_result_page_contains_candidate_sections():
    candidates = {
        "短期": pd.DataFrame(
            {
                "周期": ["短期"],
                "排名": [1],
                "代码": ["000001"],
                "名称": ["强势股"],
                "看涨评分": [87.0],
                "评分": [82.0],
                "入选理由": ["量比活跃"],
            }
        ),
        "中期": pd.DataFrame(),
        "长期": pd.DataFrame(),
    }

    html = render_live_result_page(candidates=candidates, updated_at="2026-06-01 10:00:00")

    assert "短期候选" in html
    assert "中期候选" in html
    assert "长期候选" in html
    assert "强势股" in html
    assert "看涨评分" in html
    assert "不是买入建议" in html
    assert "看涨概率" not in html
    assert "推荐股票" not in html


def test_render_home_page_contains_custom_stock_query_form():
    html = render_home_page()

    assert "个股代码查询" in html
    assert 'action="/stock"' in html
    assert 'name="code"' in html
    assert "输入股票代码" in html


def test_render_home_page_marks_cached_or_refreshing_state():
    html = render_home_page(
        candidates={},
        updated_at="后台刷新中",
        metadata={
            "scan_scope": "后台刷新中",
            "raw_count": 0,
            "filtered_count": 0,
            "deep_analysis_count": 0,
            "data_source": "首次打开先返回页面",
            "data_state": "后台刷新中",
        },
    )

    assert "当前数据状态" in html
    assert "后台刷新中" in html
    assert "首次打开先返回页面" in html


def test_render_stock_report_page_shows_period_advice_and_report():
    report = pd.DataFrame(
        {
            "周期": ["短期", "中期", "长期"],
            "排名": [1, 1, 1],
            "代码": ["000001", "000001", "000001"],
            "名称": ["平安银行", "平安银行", "平安银行"],
            "看涨评分": [70.0, 82.0, 76.0],
            "技术面评分": [80.0, 75.0, 60.0],
            "基本面评分": [60.0, 85.0, 90.0],
            "风险等级": ["低", "低", "低"],
            "追高风险": ["追高风险：低；未触发明显追高风险。", "追高风险：中；换手或量比过热；资金或基本面存在分歧。", "追高风险：低；未触发明显追高风险。"],
            "技术面分析": ["技术面：量价配合。", "技术面：趋势平稳。", "技术面：长期波动可控。"],
            "基本面分析": ["基本面：估值未极端。", "基本面：盈利质量较好。", "基本面：现金流较稳。"],
            "建议持仓周期": ["建议持仓周期：3-5 个交易日。", "建议持仓周期：2-4 周。", "建议持仓周期：3-6 个月。"],
            "综合结论": ["短期观察", "中期观察", "长期观察"],
            "操作节奏": ["操作节奏：等回踩确认，不追高。", "操作节奏：可按波段观察。", "操作节奏：只适合低频跟踪。"],
            "核心看多理由": ["看多：技术面活跃。", "看多：基本面评分靠前。", "看多：现金流较稳。"],
            "核心反对理由": ["反对：行业代理样本偏少。", "反对：暂未发现规则内的明显反对证据。", "反对：回测未校准。"],
            "失效条件": ["失效条件：放量下跌。", "失效条件：跌破关键支撑或资金转负。", "失效条件：财报质量恶化。"],
            "交易计划参考": ["交易计划参考：观察价 10.00，计划买入区间 9.80-10.05。", "交易计划参考：观察价 10.00，计划买入区间 9.70-10.10。", "交易计划参考：观察价 10.00，计划买入区间 9.50-10.20。"],
            "观察价": [10.0, 10.0, 10.0],
            "计划买入区间": ["9.80-10.05", "9.70-10.10", "9.50-10.20"],
            "止损价": [9.5, 9.2, 8.8],
            "第一目标价": [10.6, 11.0, 12.0],
            "第二目标价": [11.2, 12.0, 14.0],
            "计划盈亏比": ["1.4:1", "1.6:1", "2.0:1"],
            "追高纪律": ["追高纪律：不追高，等回踩确认。", "追高纪律：不追高，等回踩确认。", "追高纪律：不追高，等回踩确认。"],
            "入选理由": ["短线活跃", "综合评分最高", "基本面稳定"],
        }
    )

    html = render_stock_report_page(
        report,
        updated_at="2026-06-02 10:00:00",
        metadata={"recommended_period": "中期", "query_code": "000001"},
    )

    assert "个股分析报告" in html
    assert "平安银行" in html
    assert "当前更适合观察的周期" in html
    assert "中期" in html
    assert "建议持仓周期：2-4 周" in html
    assert "追高风险：中" in html
    assert "综合结论" in html
    assert "操作节奏" in html
    assert "核心看多理由" in html
    assert "核心反对理由" in html
    assert "失效条件" in html
    assert "交易计划参考" in html
    assert "计划买入区间" in html
    assert "追高纪律" in html
    assert "短期分析" in html
    assert "中期分析" in html
    assert "长期分析" in html
    assert "<details" in html
    assert "查看完整分析" in html
    assert "展开完整分析" not in html
    assert html.index("<h3>1. 平安银行 000001</h3>") < html.index("<h4>交易计划参考</h4>")
    assert html.index("<h4>交易计划参考</h4>") < html.index("<details")
    assert "交易计划参考：观察价 10.00，计划买入区间" not in html
    assert "技术面：趋势平稳。" in html


def test_render_stock_report_page_shows_query_error():
    html = render_stock_report_page(error="请输入 6 位 A 股股票代码")

    assert "请输入 6 位 A 股股票代码" in html
    assert "个股代码查询" in html


def test_home_cache_round_trips_candidates(tmp_path, monkeypatch):
    cache_path = tmp_path / "home_candidates.pkl"
    monkeypatch.setattr(web, "HOME_CACHE_PATH", cache_path)
    candidates = {
        "短期": pd.DataFrame(
            {
                "代码": ["000001"],
                "名称": ["平安银行"],
                "看涨评分": [70.0],
                "追高风险": ["追高风险：低；未触发明显追高风险。"],
                "交易计划参考": ["交易计划参考：观察价 10.00，计划买入区间 9.80-10.10。"],
            }
        )
    }
    metadata = {"scan_scope": "测试缓存"}

    web._write_home_cache(candidates, "2026-06-02 10:00:00", metadata)
    cached = web._read_home_cache()

    assert isinstance(cache_path, Path)
    assert cached is not None
    cached_candidates, updated_at, cached_metadata = cached
    assert updated_at == "2026-06-02 10:00:00"
    assert cached_metadata["scan_scope"] == "测试缓存"
    assert cached_candidates["短期"].iloc[0]["代码"] == "000001"


def test_home_cache_rejects_old_candidates_without_chase_risk(tmp_path, monkeypatch):
    cache_path = tmp_path / "home_candidates.pkl"
    monkeypatch.setattr(web, "HOME_CACHE_PATH", cache_path)
    candidates = {"短期": pd.DataFrame({"代码": ["000001"], "名称": ["平安银行"]})}
    pd.to_pickle((candidates, "2026-06-02 10:00:00", {"scan_scope": "旧缓存"}), cache_path)

    assert web._read_home_cache() is None


def test_home_cache_rejects_old_candidates_without_trade_plan(tmp_path, monkeypatch):
    cache_path = tmp_path / "home_candidates.pkl"
    monkeypatch.setattr(web, "HOME_CACHE_PATH", cache_path)
    candidates = {
        "短期": pd.DataFrame(
            {
                "代码": ["000001"],
                "名称": ["平安银行"],
                "追高风险": ["追高风险：低；未触发明显追高风险。"],
            }
        )
    }
    pd.to_pickle((candidates, "2026-06-02 10:00:00", {"scan_scope": "旧缓存"}), cache_path)

    assert web._read_home_cache() is None


def test_render_home_page_marks_fallback_scope_honestly():
    html = render_home_page(
        candidates={},
        updated_at="2026-06-01 10:00:00",
        metadata={
            "scan_scope": "高流动性观察池",
            "raw_count": 44,
            "filtered_count": 44,
            "deep_analysis_count": 0,
            "data_source": "腾讯观察池备用行情",
        },
    )

    assert "高流动性观察池" in html
    assert "不是全 A 股扫描" in html


def test_append_recommendation_snapshot_records_candidates(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "recommendation_snapshots.csv"
    monkeypatch.setattr(web, "REVIEW_SNAPSHOT_PATH", snapshot_path)
    candidates = {
        "短期": pd.DataFrame(
            {
                "周期": ["短期"],
                "排名": [1],
                "代码": ["000001"],
                "名称": ["平安银行"],
                "最新价": [12.34],
                "涨跌幅": [1.2],
                "看涨评分": [76.6],
                "技术面评分": [67.0],
                "基本面评分": [28.1],
                "风险等级": ["低"],
                "追高风险": ["追高风险：低；未触发明显追高风险。"],
                "建议持仓周期": ["建议持仓周期：1-2 个交易日。"],
                "综合结论": ["综合结论：短期观察。"],
                "交易计划参考": ["交易计划参考：观察价 12.34，计划买入区间 12.00-12.45。"],
                "观察价": [12.34],
                "计划买入区间": ["12.00-12.45"],
                "止损价": [11.8],
                "第一目标价": [13.2],
                "第二目标价": [14.0],
                "计划盈亏比": ["1.6:1"],
                "追高纪律": ["追高纪律：允许小仓位试错，但必须等量价确认。"],
                "入选理由": ["价格走强、换手充分、成交额较高"],
            }
        ),
        "中期": pd.DataFrame(),
        "长期": pd.DataFrame(),
    }

    web._append_recommendation_snapshot(
        candidates,
        "2026-06-02 15:00:00",
        {"scan_scope": "全A股实时行情", "data_source": "测试行情源"},
    )
    web._append_recommendation_snapshot(
        candidates,
        "2026-06-02 15:00:00",
        {"scan_scope": "全A股实时行情", "data_source": "测试行情源"},
    )

    saved = pd.read_csv(snapshot_path, dtype={"代码": str})
    assert len(saved) == 1
    assert saved.iloc[0]["快照时间"] == "2026-06-02 15:00:00"
    assert saved.iloc[0]["周期"] == "短期"
    assert saved.iloc[0]["代码"] == "000001"
    assert saved.iloc[0]["推荐快照价"] == 12.34
    assert saved.iloc[0]["当日涨跌幅"] == 1.2
    assert saved.iloc[0]["交易计划参考"].startswith("交易计划参考")
    assert saved.iloc[0]["计划买入区间"] == "12.00-12.45"
    assert saved.iloc[0]["止损价"] == 11.8
    assert saved.iloc[0]["追高纪律"].startswith("追高纪律")
    assert saved.iloc[0]["扫描范围"] == "全A股实时行情"


def test_render_home_page_shows_review_snapshot_panel(tmp_path, monkeypatch):
    snapshot_path = tmp_path / "recommendation_snapshots.csv"
    monkeypatch.setattr(web, "REVIEW_SNAPSHOT_PATH", snapshot_path)
    pd.DataFrame(
        [
            {
                "快照时间": "2026-06-02 15:00:00",
                "周期": "短期",
                "排名": 1,
                "代码": "000001",
                "名称": "平安银行",
                "推荐快照价": 12.34,
                "当日涨跌幅": 1.2,
                "看涨评分": 76.6,
                "技术面评分": 67.0,
                "基本面评分": 28.1,
                "风险等级": "低",
                "追高风险": "追高风险：低；未触发明显追高风险。",
                "建议持仓周期": "建议持仓周期：1-2 个交易日。",
                "综合结论": "综合结论：短期观察。",
                "入选理由": "价格走强、换手充分、成交额较高",
                "扫描范围": "全A股实时行情",
                "数据源": "测试行情源",
            }
        ]
    ).to_csv(snapshot_path, index=False, encoding="utf-8-sig")

    html = render_home_page()

    assert "每日复盘" in html
    assert "推荐快照" in html
    assert "2026-06-02 15:00:00" in html
    assert "平安银行" in html
    assert "记录推荐快照价和当日涨跌幅" in html
    assert "不把快照当成已实现收益" in html


def test_render_home_page_shows_empty_review_state(tmp_path, monkeypatch):
    monkeypatch.setattr(web, "REVIEW_SNAPSHOT_PATH", tmp_path / "missing.csv")

    html = render_home_page()

    assert "每日复盘" in html
    assert "暂无复盘记录" in html

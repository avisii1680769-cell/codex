import pandas as pd

from stock_bullish.web import render_home_page, render_live_result_page


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

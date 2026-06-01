import pandas as pd

from stock_bullish.web import render_home_page, render_live_result_page


def test_render_home_page_is_chinese_live_scanner_without_upload_form():
    html = render_home_page()

    assert 'type="file"' not in html
    assert "实时扫描" in html
    assert "短期" in html
    assert "中期" in html
    assert "长期" in html
    assert "看涨评分" in html
    assert "规则评分，不是预测概率" in html
    assert "未纳入因素" in html
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

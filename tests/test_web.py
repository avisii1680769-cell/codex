import pandas as pd

from stock_bullish.web import render_home_page, render_result_page


def test_render_home_page_contains_upload_form_and_strategy_options():
    html = render_home_page()

    assert 'type="file"' in html
    assert 'name="strategy_name"' in html
    assert "trend_volume" in html
    assert "运行回测" in html


def test_render_result_page_contains_summary_and_download_links(tmp_path):
    summary = pd.DataFrame(
        {
            "strategy": ["trend_volume"],
            "window": [5],
            "sample_count": [1],
        }
    )
    paths = {
        "summary_csv": tmp_path / "summary.csv",
        "signals_csv": tmp_path / "signals.csv",
    }

    html = render_result_page(summary=summary, stability=pd.DataFrame(), paths=paths)

    assert "trend_volume" in html
    assert "summary.csv" in html
    assert "/download/summary_csv" in html

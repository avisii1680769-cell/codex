from __future__ import annotations

import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from stock_bullish.live import PERIODS, scan_live_candidates

HOME_LIMIT = 5

PAGE_STYLE = """
body{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif;background:#f5f7fb;color:#172026}
header{background:#12343b;color:white;padding:22px 32px}
main{padding:24px 32px;max-width:1240px;margin:0 auto}
.panel{background:white;border:1px solid #d9e2ec;border-radius:8px;padding:18px;margin-bottom:18px}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
.metric{background:#eef7f6;border:1px solid #c7e2de;border-radius:8px;padding:12px}
.metric strong{display:block;font-size:22px;color:#0f766e}
.candidate-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(260px,1fr));gap:12px}
.candidate{border:1px solid #d9e2ec;border-radius:8px;padding:12px;background:#fff}
.candidate h3{margin:0 0 8px;font-size:16px}
.score-row{display:flex;gap:8px;flex-wrap:wrap;margin:8px 0}
.score{background:#eef7f6;border:1px solid #c7e2de;border-radius:6px;padding:5px 7px;font-size:12px}
.analysis{font-size:13px;line-height:1.5;margin:7px 0;color:#243b53}
.error{border-color:#f5c2c7;background:#fff5f5;color:#842029}
.hint{color:#52616b;font-size:13px;line-height:1.5}
.risk{background:#fff8e6;border-color:#f3d19e}
.truth{background:#f7fbff;border-color:#cfe3f5}
.truth h2,.risk h2{margin-top:0}
.truth ul,.risk ul{margin-bottom:0}
"""


def render_home_page(
    candidates: dict[str, pd.DataFrame] | None = None,
    updated_at: str | None = None,
    error: str | None = None,
) -> str:
    error_html = f'<section class="panel error">{html.escape(error)}</section>' if error else ""
    candidate_html = _candidate_sections(candidates or {})
    updated = html.escape(updated_at or "等待行情源返回")
    total = sum(len(frame) for frame in (candidates or {}).values())
    return _page(
        "A 股多周期候选评分",
        f"""
        {error_html}
        <section class="panel">
          <div class="metrics">
            <div class="metric"><span>展示规则</span><strong>每周期 5 只</strong></div>
            <div class="metric"><span>更新时间</span><strong>{updated}</strong></div>
            <div class="metric"><span>候选总数</span><strong>{total}</strong></div>
          </div>
          <p class="hint">首页固定展示每个周期 5 只候选，不需要输入数量扫描。排序同时使用技术面评分和基本面评分。</p>
        </section>
        <section class="panel risk">
          <h2>实事求是的边界</h2>
          <p>这里不是荐股结论，也不是买入建议。当前基本面来自行情源可稳定取得的估值与规模快照，包括动态市盈率、市净率和总市值；这不是完整财报分析，也没有覆盖利润质量、负债结构、行业景气、公告和新闻风险。</p>
        </section>
        {candidate_html}
        {_model_truth_panel()}
        """,
    )


def render_live_result_page(candidates: dict[str, pd.DataFrame], updated_at: str) -> str:
    return render_home_page(candidates=candidates, updated_at=updated_at)


def serve(host: str = "127.0.0.1", port: int = 8765, output_dir: str | Path = "outputs/web") -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path in {"/", "/scan"}:
                self._run_home_scan()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path == "/scan":
                self._run_home_scan()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _run_home_scan(self) -> None:
            try:
                candidates, updated_at = scan_live_candidates(limit=HOME_LIMIT)
            except Exception as exc:  # noqa: BLE001
                self._send_html(render_home_page(error=str(exc)))
                return
            self._send_html(render_home_page(candidates=candidates, updated_at=updated_at))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Open http://{host}:{port}")
    server.serve_forever()


def _page(title: str, body: str) -> str:
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{html.escape(title)}</title>
  <style>{PAGE_STYLE}</style>
</head>
<body>
  <header><h1>{html.escape(title)}</h1><p>固定展示短期、中期、长期各 5 只候选，并给出技术面和基本面简要分析。</p></header>
  <main>{body}</main>
</body>
</html>"""


def _model_truth_panel() -> str:
    return """
    <section class="panel truth">
      <h2>模型说明</h2>
      <p><strong>看涨评分是规则评分，不是预测概率。</strong> 短期更重技术面，中期技术面和基本面接近均衡，长期更重基本面。评分用于排序参考，不代表真实未来上涨概率。</p>
      <h2>数据来源与覆盖范围</h2>
      <p>实时行情优先使用东方财富接口；接口波动时切换到腾讯行情备用源。备用源目前使用一组高流动性观察池，不等同于全市场完整扫描。</p>
      <h2>未纳入因素</h2>
      <ul>
        <li>未纳入完整财报分析、行业景气度、公告事件、资金流、历史 K 线形态和新闻风险。</li>
        <li>未按行业校准市盈率和市净率阈值，周期股、银行股、科技股可能被同一规则误判。</li>
        <li>当前权重来自透明经验规则，还没有用历史回测校准为真实成功率。</li>
      </ul>
    </section>
    """


def _candidate_sections(candidates: dict[str, pd.DataFrame]) -> str:
    sections = []
    for period in PERIODS:
        frame = candidates.get(period, pd.DataFrame())
        sections.append(
            f"""
            <section class="panel">
              <h2>{period}候选</h2>
              {_candidate_cards(frame)}
            </section>
            """
        )
    return "\n".join(sections)


def _candidate_cards(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<p class="hint">暂无符合条件的数据。</p>'
    cards = []
    for _, row in frame.head(HOME_LIMIT).iterrows():
        cards.append(
            f"""
            <article class="candidate">
              <h3>{html.escape(str(row.get("排名", "")))}. {html.escape(str(row.get("名称", "")))} {html.escape(str(row.get("代码", "")))}</h3>
              <div class="score-row">
                <span class="score">看涨评分 {html.escape(_fmt(row.get("看涨评分")))}</span>
                <span class="score">技术面评分 {html.escape(_fmt(row.get("技术面评分")))}</span>
                <span class="score">基本面评分 {html.escape(_fmt(row.get("基本面评分")))}</span>
                <span class="score">风险等级 {html.escape(str(row.get("风险等级", "待核查")))}</span>
              </div>
              <p class="analysis">{html.escape(str(row.get("技术面分析", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("基本面分析", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("利润分析", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("负债分析", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("现金流分析", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("行业景气分析", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("公告新闻风险", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("支持证据", "")))}</p>
              <p class="analysis">{html.escape(str(row.get("反对证据", "")))}</p>
              <p class="hint">{html.escape(str(row.get("入选理由", "")))}</p>
            </article>
            """
        )
    return '<div class="candidate-grid">' + "\n".join(cards) + "</div>"


def _fmt(value: object) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def main() -> None:
    serve()


if __name__ == "__main__":
    main()

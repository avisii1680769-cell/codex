from __future__ import annotations

import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pandas as pd

from stock_bullish.live import PERIODS, scan_live_candidates

PAGE_STYLE = """
body{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif;background:#f5f7fb;color:#172026}
header{background:#12343b;color:white;padding:22px 32px}
main{padding:24px 32px;max-width:1240px;margin:0 auto}
.panel{background:white;border:1px solid #d9e2ec;border-radius:8px;padding:18px;margin-bottom:18px}
.row{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
label{display:block;font-size:13px;font-weight:700;margin-bottom:6px}
input,select,button{font-size:14px;padding:9px 10px;border:1px solid #bcccdc;border-radius:6px;background:white}
button{background:#0f766e;color:white;border-color:#0f766e;cursor:pointer;font-weight:700}
button:hover{background:#115e59}
table{border-collapse:collapse;width:100%;font-size:13px;background:white}
th,td{border:1px solid #d9e2ec;padding:7px 8px;text-align:left;white-space:nowrap}
th{background:#e6f0f2}
.table-wrap{overflow:auto;max-height:520px;border:1px solid #d9e2ec;border-radius:6px}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:10px}
.metric{background:#eef7f6;border:1px solid #c7e2de;border-radius:8px;padding:12px}
.metric strong{display:block;font-size:22px;color:#0f766e}
.error{border-color:#f5c2c7;background:#fff5f5;color:#842029}
.hint{color:#52616b;font-size:13px;line-height:1.5}
.risk{background:#fff8e6;border-color:#f3d19e}
.truth{background:#f7fbff;border-color:#cfe3f5}
.truth h2,.risk h2{margin-top:0}
.truth ul,.risk ul{margin-bottom:0}
.actions a{color:#0f766e;font-weight:700}
"""


def render_home_page(error: str | None = None) -> str:
    error_html = f'<section class="panel error">{html.escape(error)}</section>' if error else ""
    return _page(
        "A 股实时看涨候选评分工具",
        f"""
        {error_html}
        <section class="panel">
          <form action="/scan" method="post">
            <div class="row">
              <div>
                <label for="limit">每个周期显示数量</label>
                <input id="limit" name="limit" type="number" min="5" max="100" value="20">
              </div>
              <button type="submit">实时扫描</button>
            </div>
          </form>
          <p class="hint">页面会自动联网获取 A 股实时行情快照，按短期、中期、长期三套规则生成候选列表；不需要上传行情文件。</p>
        </section>
        {_model_truth_panel()}
        {_period_explanation_panel()}
        """,
    )


def render_live_result_page(candidates: dict[str, pd.DataFrame], updated_at: str) -> str:
    total = sum(len(frame) for frame in candidates.values())
    return _page(
        "实时扫描结果",
        f"""
        <section class="panel">
          <div class="metrics">
            <div class="metric"><span>更新时间</span><strong>{html.escape(updated_at)}</strong></div>
            <div class="metric"><span>候选总数</span><strong>{total}</strong></div>
            <div class="metric"><span>覆盖周期</span><strong>短 / 中 / 长</strong></div>
          </div>
        </section>
        <section class="panel risk">
          <h2>使用边界</h2>
          <p>候选列表是规则评分，不是买入建议，也不是收益承诺。看涨评分用于排序参考，不代表真实未来上涨概率。</p>
        </section>
        {_candidate_sections(candidates)}
        {_model_truth_panel()}
        <section class="panel actions"><a href="/">返回重新扫描</a></section>
        """,
    )


def serve(host: str = "127.0.0.1", port: int = 8765, output_dir: str | Path = "outputs/web") -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send_html(render_home_page())
                return
            if self.path == "/scan":
                self._run_scan(limit=20)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path != "/scan":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            self._run_scan(limit=self._read_limit())

        def _run_scan(self, limit: int) -> None:
            try:
                candidates, updated_at = scan_live_candidates(limit=limit)
            except Exception as exc:  # noqa: BLE001
                self._send_html(render_home_page(str(exc)))
                return
            self._send_html(render_live_result_page(candidates, updated_at))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _read_limit(self) -> int:
            length = int(self.headers.get("Content-Length", "0"))
            body = self.rfile.read(length).decode("utf-8", errors="ignore")
            for item in body.split("&"):
                if item.startswith("limit="):
                    try:
                        return min(max(int(item.split("=", 1)[1]), 5), 100)
                    except ValueError:
                        return 20
            return 20

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
  <header><h1>{html.escape(title)}</h1><p>自动扫描 A 股实时行情，展示短期、中期、长期看涨候选评分。</p></header>
  <main>{body}</main>
</body>
</html>"""


def _model_truth_panel() -> str:
    return """
    <section class="panel truth">
      <h2>模型说明</h2>
      <p><strong>看涨评分是规则评分，不是预测概率。</strong> 当前版本根据实时行情字段做初筛排序，适合研究和复盘，不适合直接作为交易依据。</p>
      <h2>数据来源与覆盖范围</h2>
      <p>实时行情优先使用东方财富接口；接口波动时切换到腾讯行情备用源。备用源目前使用一组高流动性观察池，不等同于全市场完整扫描。</p>
      <h2>未纳入因素</h2>
      <ul>
        <li>未纳入财报质量、行业景气度、公告事件、资金流、历史 K 线形态和新闻风险。</li>
        <li>未按行业校准市盈率和市净率阈值，周期股、银行股、科技股可能被同一规则误判。</li>
        <li>当前权重来自透明经验规则，还没有用历史回测校准为真实成功率。</li>
      </ul>
    </section>
    """


def _period_explanation_panel() -> str:
    return """
    <section class="panel">
      <h2>周期说明</h2>
      <ul>
        <li>短期：更看重量比、涨跌幅、换手率和成交额。</li>
        <li>中期：兼顾价格强度、成交活跃度和估值不过热。</li>
        <li>长期：更看重流动性、市值稳定性和估值合理性。</li>
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
              {_frame_table(frame)}
            </section>
            """
        )
    return "\n".join(sections)


def _frame_table(frame: pd.DataFrame) -> str:
    if frame.empty:
        return '<p class="hint">暂无符合条件的数据。</p>'
    return f'<div class="table-wrap">{frame.to_html(index=False, escape=True)}</div>'


def main() -> None:
    serve()


if __name__ == "__main__":
    main()

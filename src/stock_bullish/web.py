from __future__ import annotations

import html
import tempfile
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote

import pandas as pd

from stock_bullish.research import ResearchOutput, run_research
from stock_bullish.strategy import PRESET_STRATEGIES

PAGE_STYLE = """
body{margin:0;font-family:Arial,'Microsoft YaHei',sans-serif;background:#f5f7fb;color:#1f2937}
header{background:#12343b;color:white;padding:22px 32px}
main{padding:24px 32px;max-width:1180px;margin:0 auto}
.panel{background:white;border:1px solid #d9e2ec;border-radius:8px;padding:18px;margin-bottom:18px}
.row{display:flex;gap:12px;align-items:end;flex-wrap:wrap}
label{display:block;font-size:13px;font-weight:700;margin-bottom:6px}
input,select,button{font-size:14px;padding:9px 10px;border:1px solid #bcccdc;border-radius:6px;background:white}
button{background:#0f766e;color:white;border-color:#0f766e;cursor:pointer;font-weight:700}
button:hover{background:#115e59}
table{border-collapse:collapse;width:100%;font-size:13px;background:white}
th,td{border:1px solid #d9e2ec;padding:7px 8px;text-align:left;white-space:nowrap}
th{background:#e6f0f2}
.table-wrap{overflow:auto;max-height:420px;border:1px solid #d9e2ec;border-radius:6px}
.metrics{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.metric{background:#eef7f6;border:1px solid #c7e2de;border-radius:8px;padding:12px}
.metric strong{display:block;font-size:20px;color:#0f766e}
.links a{display:inline-block;margin:0 8px 8px 0;color:#0f766e;font-weight:700}
.error{border-color:#f5c2c7;background:#fff5f5;color:#842029}
.hint{color:#52616b;font-size:13px;line-height:1.5}
"""


def render_home_page(error: str | None = None) -> str:
    strategy_options = "\n".join(
        [
            '<option value="all">all - 全部预设</option>',
            *[
                f'<option value="{html.escape(name)}">{html.escape(name)}</option>'
                for name in PRESET_STRATEGIES
            ],
        ]
    )
    error_html = f'<section class="panel error">{html.escape(error)}</section>' if error else ""
    return _page(
        "A 股看涨回测工具",
        f"""
        {error_html}
        <section class="panel">
          <form action="/run" method="post" enctype="multipart/form-data">
            <div class="row">
              <div>
                <label for="market_file">行情文件 CSV / Parquet</label>
                <input id="market_file" name="market_file" type="file" accept=".csv,.parquet,.pq" required>
              </div>
              <div>
                <label for="strategy_name">策略预设</label>
                <select id="strategy_name" name="strategy_name">{strategy_options}</select>
              </div>
              <button type="submit">运行回测</button>
            </div>
          </form>
          <p class="hint">文件至少包含 trade_date, symbol, open, high, low, close, volume, amount。推荐使用 examples/market_data_template.csv 作为模板。</p>
        </section>
        <section class="panel">
          <h2>内置策略</h2>
          <div class="table-wrap">
            <table>
              <thead><tr><th>策略</th><th>条件</th><th>最少命中</th></tr></thead>
              <tbody>{_strategy_rows()}</tbody>
            </table>
          </div>
        </section>
        """,
    )


def render_result_page(
    summary: pd.DataFrame,
    stability: pd.DataFrame,
    paths: dict[str, Path],
) -> str:
    return _page(
        "回测结果",
        f"""
        <section class="panel">
          <div class="metrics">
            <div class="metric"><span>策略窗口</span><strong>{len(summary)}</strong></div>
            <div class="metric"><span>总样本</span><strong>{_sample_count(summary)}</strong></div>
            <div class="metric"><span>稳定性分组</span><strong>{len(stability)}</strong></div>
          </div>
        </section>
        <section class="panel links">
          <h2>下载结果</h2>
          {_download_links(paths)}
        </section>
        <section class="panel">
          <h2>策略汇总</h2>
          {_frame_table(summary)}
        </section>
        <section class="panel">
          <h2>稳定性分组</h2>
          {_frame_table(stability)}
        </section>
        <section class="panel"><a href="/">返回重新上传</a></section>
        """,
    )


def serve(host: str = "127.0.0.1", port: int = 8765, output_dir: str | Path = "outputs/web") -> None:
    output_root = Path(output_dir)
    output_root.mkdir(parents=True, exist_ok=True)
    state: dict[str, Path] = {}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            if self.path == "/":
                self._send_html(render_home_page())
                return
            if self.path.startswith("/download/"):
                self._send_download(state)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path != "/run":
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            try:
                output = self._run_uploaded_file(output_root)
            except Exception as exc:  # noqa: BLE001
                self._send_html(render_home_page(str(exc)), status=HTTPStatus.BAD_REQUEST)
                return
            state.clear()
            state.update(output.paths)
            self._send_html(render_result_page(output.summary, output.stability, output.paths))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _run_uploaded_file(self, output_root: Path) -> ResearchOutput:
            length = int(self.headers.get("Content-Length", "0"))
            content_type = self.headers.get("Content-Type", "")
            body = self.rfile.read(length)
            message = BytesParser(policy=default).parsebytes(
                f"Content-Type: {content_type}\r\n\r\n".encode() + body
            )
            fields = {
                part.get_param("name", header="content-disposition"): part
                for part in message.iter_parts()
            }
            file_part = fields.get("market_file")
            if file_part is None or not file_part.get_filename():
                raise ValueError("请上传 CSV 或 Parquet 行情文件。")
            strategy_part = fields.get("strategy_name")
            strategy_name = "all"
            if strategy_part is not None:
                strategy_name = strategy_part.get_content().strip() or "all"

            filename = Path(file_part.get_filename()).name
            suffix = Path(filename).suffix or ".csv"
            upload_dir = Path(tempfile.mkdtemp(prefix="stock_bullish_upload_"))
            upload_path = upload_dir / f"market_data{suffix}"
            payload = file_part.get_payload(decode=True)
            upload_path.write_bytes(payload or b"")
            run_dir = output_root / "latest"
            return run_research(upload_path, run_dir, strategy_name=strategy_name)

        def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _send_download(self, paths: dict[str, Path]) -> None:
            key = unquote(self.path.rsplit("/", 1)[-1])
            path = paths.get(key)
            if path is None or not path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            payload = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/csv; charset=utf-8")
            self.send_header("Content-Disposition", f'attachment; filename="{path.name}"')
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
  <header><h1>{html.escape(title)}</h1><p>历史回测研究工具，不构成投资建议。</p></header>
  <main>{body}</main>
</body>
</html>"""


def _strategy_rows() -> str:
    rows = []
    for name, rule in PRESET_STRATEGIES.items():
        rows.append(
            "<tr>"
            f"<td>{html.escape(name)}</td>"
            f"<td>{html.escape(', '.join(rule.conditions))}</td>"
            f"<td>{rule.min_score or len(rule.conditions)}</td>"
            "</tr>"
        )
    return "\n".join(rows)


def _download_links(paths: dict[str, Path]) -> str:
    links = []
    for key, path in paths.items():
        links.append(f'<a href="/download/{html.escape(key)}">{html.escape(path.name)}</a>')
    return "\n".join(links)


def _frame_table(frame: pd.DataFrame, max_rows: int = 50) -> str:
    if frame.empty:
        return '<p class="hint">暂无数据。</p>'
    preview = frame.head(max_rows)
    return f'<div class="table-wrap">{preview.to_html(index=False, escape=True)}</div>'


def _sample_count(summary: pd.DataFrame) -> int:
    if "sample_count" not in summary.columns or summary.empty:
        return 0
    return int(summary["sample_count"].fillna(0).sum())


def main() -> None:
    serve()


if __name__ == "__main__":
    main()

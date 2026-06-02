from __future__ import annotations

import html
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import threading
from urllib.parse import parse_qs, urlparse

import pandas as pd

from stock_bullish.live import PERIODS, analyze_stock_code, scan_live_candidates

HOME_LIMIT = 5
HOME_CACHE_PATH = Path("outputs/web/home_candidates.pkl")
REVIEW_SNAPSHOT_PATH = Path("outputs/review/recommendation_snapshots.csv")
_HOME_SCAN_LOCK = threading.Lock()
_HOME_SCAN_RUNNING = False

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
.summary-line{font-size:13px;line-height:1.5;margin:8px 0;color:#172026}
.detail-report{margin-top:10px;border-top:1px solid #e6edf3;padding-top:8px}
.detail-report summary{cursor:pointer;color:#0f766e;font-weight:700;font-size:13px}
.detail-report[open] summary{margin-bottom:8px}
.query-form{display:flex;gap:10px;flex-wrap:wrap;margin-top:12px}
.query-form input{min-width:220px;flex:1;border:1px solid #b8c7d3;border-radius:6px;padding:10px;font-size:14px}
.query-form button,.link-button{border:1px solid #0f766e;background:#0f766e;color:white;border-radius:6px;padding:10px 14px;font-size:14px;text-decoration:none;cursor:pointer}
.link-button{display:inline-block;margin-top:8px}
.error{border-color:#f5c2c7;background:#fff5f5;color:#842029}
.hint{color:#52616b;font-size:13px;line-height:1.5}
.risk{background:#fff8e6;border-color:#f3d19e}
.truth{background:#f7fbff;border-color:#cfe3f5}
.truth h2,.risk h2{margin-top:0}
.truth ul,.risk ul{margin-bottom:0}
.review-table-wrap{overflow-x:auto}
.review-table{width:100%;border-collapse:collapse;font-size:13px;min-width:980px}
.review-table th,.review-table td{border-bottom:1px solid #e6edf3;padding:8px;text-align:left;vertical-align:top}
.review-table th{background:#eef7f6;color:#172026}
"""


def render_home_page(
    candidates: dict[str, pd.DataFrame] | None = None,
    updated_at: str | None = None,
    error: str | None = None,
    metadata: dict[str, object] | None = None,
) -> str:
    error_html = f'<section class="panel error">{html.escape(error)}</section>' if error else ""
    candidate_html = _candidate_sections(candidates or {})
    updated = html.escape(updated_at or "等待行情源返回")
    total = sum(len(frame) for frame in (candidates or {}).values())
    scope_html = _scope_panel(metadata)
    review_html = _review_panel()
    return _page(
        "A 股多周期候选评分",
        f"""
        {error_html}
        <section class="panel">
          {_stock_query_form()}
          <div class="metrics">
            <div class="metric"><span>展示规则</span><strong>每周期 5 只</strong></div>
            <div class="metric"><span>更新时间</span><strong>{updated}</strong></div>
            <div class="metric"><span>候选总数</span><strong>{total}</strong></div>
          </div>
          <p class="hint">首页固定展示每个周期 5 只候选，不需要输入数量扫描。排序同时使用技术面评分和基本面评分。</p>
        </section>
        {scope_html}
        <section class="panel risk">
          <h2>实事求是的边界</h2>
          <p>这里不是荐股结论，也不是买入建议。页面会尽量抓取行情、估值、财报、公告、融资融券、互联互通持仓和主力资金接口；接口不可用或口径不稳定时，会明确显示未取得可靠数据，不把占位信息当成判断依据。</p>
        </section>
        {review_html}
        {candidate_html}
        {_model_truth_panel()}
        """,
    )


def render_live_result_page(candidates: dict[str, pd.DataFrame], updated_at: str) -> str:
    return render_home_page(candidates=candidates, updated_at=updated_at)


def render_stock_report_page(
    report: pd.DataFrame | None = None,
    updated_at: str | None = None,
    metadata: dict[str, object] | None = None,
    error: str | None = None,
) -> str:
    error_html = f'<section class="panel error">{html.escape(error)}</section>' if error else ""
    body = f"""
      <section class="panel">
        {_stock_query_form()}
        <p class="hint">输入股票代码后，页面会按同一套技术面、基本面、财报质量、公告新闻、资金面和风险证据，分别生成短期、中期、长期三档分析。</p>
      </section>
      {error_html}
    """
    if report is not None and not report.empty:
        body += _stock_report_panel(report, updated_at, metadata or {})
    body += _model_truth_panel()
    return _page("个股分析报告", body)


def serve(host: str = "127.0.0.1", port: int = 8765, output_dir: str | Path = "outputs/web") -> None:
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/":
                self._run_home_cached()
                return
            if parsed.path == "/scan":
                self._run_home_scan()
                return
            if parsed.path == "/stock":
                code = parse_qs(parsed.query).get("code", [""])[0]
                self._run_stock_query(code)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if self.path == "/scan":
                self._run_home_scan()
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def _run_home_scan(self) -> None:
            try:
                candidates, updated_at, metadata = scan_live_candidates(limit=HOME_LIMIT)
            except Exception as exc:  # noqa: BLE001
                self._send_html(render_home_page(error=str(exc)))
                return
            metadata = dict(metadata)
            metadata["data_state"] = "最新扫描完成"
            _write_home_cache(candidates, updated_at, metadata)
            _append_recommendation_snapshot(candidates, updated_at, metadata)
            self._send_html(render_home_page(candidates=candidates, updated_at=updated_at, metadata=metadata))

        def _run_home_cached(self) -> None:
            cached = _read_home_cache()
            if cached is None:
                metadata = {
                    "scan_scope": "后台刷新中",
                    "raw_count": 0,
                    "filtered_count": 0,
                    "deep_analysis_count": 0,
                    "data_source": "首次打开先返回页面，行情扫描在后台执行",
                    "data_state": "后台刷新中",
                }
                self._send_html(
                    render_home_page(
                        candidates={},
                        updated_at="后台刷新中",
                        metadata=metadata,
                        error="行情数据正在后台刷新，请稍后刷新页面；个股代码查询可直接使用。",
                    )
                )
                _start_background_home_scan()
                return
            candidates, updated_at, metadata = cached
            metadata = dict(metadata)
            metadata["data_source"] = f"{metadata.get('data_source', '缓存候选')}；页面先展示缓存，后台自动刷新"
            metadata["data_state"] = "缓存结果，后台刷新中"
            self._send_html(render_home_page(candidates=candidates, updated_at=updated_at, metadata=metadata))
            _start_background_home_scan()

        def _run_stock_query(self, code: str) -> None:
            try:
                report, updated_at, metadata = analyze_stock_code(code)
            except Exception as exc:  # noqa: BLE001
                self._send_html(render_stock_report_page(error=str(exc)))
                return
            self._send_html(render_stock_report_page(report=report, updated_at=updated_at, metadata=metadata))

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_html(self, content: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            payload = content.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            try:
                self.wfile.write(payload)
            except (BrokenPipeError, ConnectionAbortedError):
                return

    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Open http://{host}:{port}")
    server.serve_forever()


def _read_home_cache() -> tuple[dict[str, pd.DataFrame], str, dict[str, object]] | None:
    if not HOME_CACHE_PATH.exists():
        return None
    try:
        cached = pd.read_pickle(HOME_CACHE_PATH)
    except Exception:
        return None
    if not isinstance(cached, tuple) or len(cached) != 3:
        return None
    candidates, updated_at, metadata = cached
    if not isinstance(candidates, dict) or not isinstance(metadata, dict):
        return None
    if any(
        isinstance(frame, pd.DataFrame)
        and not frame.empty
        and ("追高风险" not in frame.columns or "交易计划参考" not in frame.columns)
        for frame in candidates.values()
    ):
        return None
    return candidates, str(updated_at), metadata


def _write_home_cache(candidates: dict[str, pd.DataFrame], updated_at: str, metadata: dict[str, object]) -> None:
    try:
        HOME_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        pd.to_pickle((candidates, updated_at, metadata), HOME_CACHE_PATH)
    except Exception:
        return


def _append_recommendation_snapshot(
    candidates: dict[str, pd.DataFrame],
    updated_at: str,
    metadata: dict[str, object],
) -> None:
    rows = []
    for period in PERIODS:
        frame = candidates.get(period, pd.DataFrame())
        if frame.empty:
            continue
        for _, row in frame.head(HOME_LIMIT).iterrows():
            rows.append(
                {
                    "快照时间": str(updated_at),
                    "周期": period,
                    "排名": row.get("排名", ""),
                    "代码": str(row.get("代码", "")).zfill(6),
                    "名称": row.get("名称", ""),
                    "推荐快照价": row.get("最新价", ""),
                    "当日涨跌幅": row.get("涨跌幅", ""),
                    "看涨评分": row.get("看涨评分", ""),
                    "技术面评分": row.get("技术面评分", ""),
                    "基本面评分": row.get("基本面评分", ""),
                    "风险等级": row.get("风险等级", ""),
                    "追高风险": row.get("追高风险", ""),
                    "建议持仓周期": row.get("建议持仓周期", ""),
                    "综合结论": row.get("综合结论", ""),
                    "交易计划参考": row.get("交易计划参考", ""),
                    "观察价": row.get("观察价", ""),
                    "计划买入区间": row.get("计划买入区间", ""),
                    "止损价": row.get("止损价", ""),
                    "第一目标价": row.get("第一目标价", ""),
                    "第二目标价": row.get("第二目标价", ""),
                    "计划盈亏比": row.get("计划盈亏比", ""),
                    "追高纪律": row.get("追高纪律", ""),
                    "入选理由": row.get("入选理由", ""),
                    "扫描范围": metadata.get("scan_scope", ""),
                    "数据源": metadata.get("data_source", ""),
                }
            )
    if not rows:
        return
    snapshot = pd.DataFrame(rows)
    try:
        REVIEW_SNAPSHOT_PATH.parent.mkdir(parents=True, exist_ok=True)
        if REVIEW_SNAPSHOT_PATH.exists():
            existing = pd.read_csv(REVIEW_SNAPSHOT_PATH, dtype={"代码": str})
            snapshot = pd.concat([existing, snapshot], ignore_index=True)
        snapshot["代码"] = snapshot["代码"].astype(str).str.zfill(6)
        snapshot = snapshot.drop_duplicates(subset=["快照时间", "周期", "代码"], keep="last")
        snapshot.to_csv(REVIEW_SNAPSHOT_PATH, index=False, encoding="utf-8-sig")
    except Exception:
        return


def _read_latest_recommendation_snapshot() -> pd.DataFrame:
    if not REVIEW_SNAPSHOT_PATH.exists():
        return pd.DataFrame()
    try:
        snapshot = pd.read_csv(REVIEW_SNAPSHOT_PATH, dtype={"代码": str})
    except Exception:
        return pd.DataFrame()
    if snapshot.empty or "快照时间" not in snapshot.columns:
        return pd.DataFrame()
    latest_time = snapshot["快照时间"].dropna().astype(str).max()
    latest = snapshot[snapshot["快照时间"].astype(str) == latest_time].copy()
    latest["_period_order"] = latest.get("周期", pd.Series(dtype=str)).map(
        {period: index for index, period in enumerate(PERIODS)}
    )
    latest["_period_order"] = pd.to_numeric(latest["_period_order"], errors="coerce").fillna(99)
    latest["_rank_order"] = pd.to_numeric(latest.get("排名", 99), errors="coerce").fillna(99)
    return latest.sort_values(["_period_order", "_rank_order"]).drop(columns=["_period_order", "_rank_order"])


def _start_background_home_scan() -> None:
    global _HOME_SCAN_RUNNING
    with _HOME_SCAN_LOCK:
        if _HOME_SCAN_RUNNING:
            return
        _HOME_SCAN_RUNNING = True

    def refresh() -> None:
        global _HOME_SCAN_RUNNING
        try:
            candidates, updated_at, metadata = scan_live_candidates(limit=HOME_LIMIT)
            _write_home_cache(candidates, updated_at, metadata)
            _append_recommendation_snapshot(candidates, updated_at, metadata)
        except Exception as exc:  # noqa: BLE001
            print(f"background home scan failed: {exc}")
        finally:
            with _HOME_SCAN_LOCK:
                _HOME_SCAN_RUNNING = False

    thread = threading.Thread(target=refresh, name="home-scan-refresh", daemon=True)
    thread.start()


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


def _stock_query_form() -> str:
    return """
    <div>
      <h2>个股代码查询</h2>
      <form class="query-form" method="get" action="/stock">
        <input name="code" inputmode="numeric" pattern="[0-9]{1,6}" placeholder="输入股票代码，如 600519 或 000001" aria-label="股票代码">
        <button type="submit">查询分析报告</button>
      </form>
    </div>
    """


def _stock_report_panel(report: pd.DataFrame, updated_at: str | None, metadata: dict[str, object]) -> str:
    best_period = str(metadata.get("recommended_period", ""))
    best_row = _best_period_row(report, best_period)
    name = html.escape(str(best_row.get("名称", "")))
    code = html.escape(str(best_row.get("代码", metadata.get("query_code", ""))))
    holding = html.escape(str(best_row.get("建议持仓周期", metadata.get("recommended_holding", ""))))
    updated = html.escape(updated_at or "等待行情源返回")
    sections = []
    for period in PERIODS:
        period_frame = report[report["周期"] == period]
        title = f"{period}分析"
        if period == best_period:
            title += "（当前更适合观察的周期）"
        sections.append(
            f"""
            <section class="panel">
              <h2>{html.escape(title)}</h2>
              {_candidate_cards(period_frame, limit=1)}
            </section>
            """
        )
    return f"""
    <section class="panel">
      <h2>{name} {code}</h2>
      <div class="metrics">
        <div class="metric"><span>当前更适合观察的周期</span><strong>{html.escape(best_period)}</strong></div>
        <div class="metric"><span>更新时间</span><strong>{updated}</strong></div>
        <div class="metric"><span>分析口径</span><strong>三周期同源评分</strong></div>
      </div>
      <p class="analysis">{holding}</p>
      <p class="hint">这是规则评分下的周期适配结论，不是买入建议；如果公告、新闻或资金数据未取得，页面会在报告中明确显示。</p>
      <a class="link-button" href="/">返回首页候选</a>
    </section>
    {"".join(sections)}
    """


def _best_period_row(report: pd.DataFrame, best_period: str) -> pd.Series:
    if best_period and "周期" in report.columns:
        matched = report[report["周期"] == best_period]
        if not matched.empty:
            return matched.iloc[0]
    return report.sort_values("评分", ascending=False).iloc[0]


def _model_truth_panel() -> str:
    return """
    <section class="panel truth">
      <h2>模型说明</h2>
      <p><strong>看涨评分是规则评分，不是预测概率。</strong> 短期更重技术面，中期技术面和基本面接近均衡，长期更重基本面。评分用于排序参考，不代表真实未来上涨概率。</p>
      <h2>数据来源与覆盖范围</h2>
      <p>实时行情优先使用东方财富接口；接口波动时切换到腾讯行情备用源。备用源目前使用一组高流动性观察池，不等同于全市场完整扫描。</p>
      <h2>已接入口径与仍未打通因素</h2>
      <ul>
        <li>已接入利润、负债、现金流、应收账款、存货、商誉、扣非净利润、公告标题风险、融资融券、互联互通持仓和主力资金流向的可用接口口径。</li>
        <li>互联互通持仓只能代表该披露口径，不等同于完整机构持仓；主力资金和融资融券是交易数据，不等同于确定性买入理由。</li>
        <li>新闻舆情使用 Bing 新闻和 Google 新闻 RSS 的标题搜索作为代理来源，只对最终候选做辅助分析，不等同于覆盖全网所有信息。</li>
        <li>政策周期和历史回测胜率校准仍未找到足够稳定的结构化接口，当前只做诚实占位。</li>
        <li>行业景气和估值分位仍是当前股票池内的代理指标，未按完整行业数据库做深度校准。</li>
        <li>当前权重来自透明经验规则，还没有用历史回测校准为真实成功率。</li>
      </ul>
    </section>
    """


def _scope_panel(metadata: dict[str, object] | None) -> str:
    if not metadata:
        return ""
    scope = str(metadata.get("scan_scope", "未知扫描范围"))
    data_source = str(metadata.get("data_source", "未知数据源"))
    data_state = str(metadata.get("data_state", "未标记"))
    raw_count = html.escape(str(metadata.get("raw_count", 0)))
    filtered_count = html.escape(str(metadata.get("filtered_count", 0)))
    deep_count = html.escape(str(metadata.get("deep_analysis_count", 0)))
    warning = ""
    if scope != "全A股实时行情":
        warning = '<p class="hint">当前不是全 A 股扫描，结果只代表该数据源覆盖范围。</p>'
    return f"""
    <section class="panel">
      <h2>扫描范围</h2>
      <div class="metrics">
        <div class="metric"><span>当前数据状态</span><strong>{html.escape(data_state)}</strong></div>
        <div class="metric"><span>当前范围</span><strong>{html.escape(scope)}</strong></div>
        <div class="metric"><span>原始样本</span><strong>{raw_count}</strong></div>
        <div class="metric"><span>过滤后样本</span><strong>{filtered_count}</strong></div>
        <div class="metric"><span>深度分析</span><strong>{deep_count}</strong></div>
      </div>
      <p class="hint">数据源：{html.escape(data_source)}</p>
      {warning}
    </section>
    """


def _review_panel() -> str:
    snapshot = _read_latest_recommendation_snapshot()
    if snapshot.empty:
        return """
        <section class="panel">
          <h2>每日复盘</h2>
          <p class="hint">暂无复盘记录。完成一次行情更新后，系统会记录推荐快照价和当日涨跌幅，后续补齐收盘价、次日表现后再计算真实复盘结果。</p>
        </section>
        """
    latest_time = html.escape(str(snapshot.iloc[0].get("快照时间", "")))
    rows = []
    for _, row in snapshot.iterrows():
        rows.append(
            f"""
            <tr>
              <td>{html.escape(str(row.get("周期", "")))}</td>
              <td>{html.escape(str(row.get("排名", "")))}</td>
              <td>{html.escape(str(row.get("名称", "")))} {html.escape(str(row.get("代码", "")))}</td>
              <td>{html.escape(_fmt(row.get("推荐快照价")))}</td>
              <td>{html.escape(_fmt(row.get("当日涨跌幅")))}</td>
              <td>{html.escape(_fmt(row.get("看涨评分")))}</td>
              <td>{html.escape(str(row.get("风险等级", "")))}</td>
              <td>{html.escape(str(row.get("建议持仓周期", "")))}</td>
              <td>{html.escape(str(row.get("入选理由", "")))}</td>
            </tr>
            """
        )
    return f"""
    <section class="panel">
      <h2>每日复盘</h2>
      <p class="hint">推荐快照：{latest_time}。这里只记录推荐快照价和当日涨跌幅，不把快照当成已实现收益；真实结果必须等收盘价、次日行情和持仓周期结束后再复盘。</p>
      <div class="review-table-wrap">
        <table class="review-table">
          <thead>
            <tr>
              <th>周期</th>
              <th>排名</th>
              <th>股票</th>
              <th>快照价</th>
              <th>当日涨跌幅</th>
              <th>看涨评分</th>
              <th>风险</th>
              <th>持仓建议</th>
              <th>入选理由</th>
            </tr>
          </thead>
          <tbody>{"".join(rows)}</tbody>
        </table>
      </div>
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


def _candidate_cards(frame: pd.DataFrame, limit: int = HOME_LIMIT) -> str:
    if frame.empty:
        return '<p class="hint">暂无符合条件的数据。</p>'
    cards = []
    for _, row in frame.head(limit).iterrows():
        detail_lines = [
            "追高风险",
            "综合结论",
            "操作节奏",
            "核心看多理由",
            "核心反对理由",
            "失效条件",
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
            "支持证据",
            "反对证据",
        ]
        details = "\n".join(
            f'<p class="analysis">{html.escape(_labeled_detail(column, str(row.get(column, ""))))}</p>'
            for column in detail_lines
            if str(row.get(column, "")).strip()
        )
        trade_plan = _trade_plan_block(row)
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
              <p class="summary-line">{html.escape(str(row.get("建议持仓周期", "")))}</p>
              <p class="summary-line">{html.escape(str(row.get("追高风险", "")))}</p>
              <p class="hint">{html.escape(str(row.get("入选理由", "")))}</p>
              {trade_plan}
              <details class="detail-report">
                <summary>查看完整分析</summary>
                {details}
              </details>
            </article>
            """
        )
    return '<div class="candidate-grid">' + "\n".join(cards) + "</div>"


def _trade_plan_block(row: pd.Series) -> str:
    plan = str(row.get("交易计划参考", "")).strip()
    if not plan:
        return ""
    fields = [
        ("观察价", _fmt(row.get("观察价"))),
        ("计划买入区间", str(row.get("计划买入区间", "")).strip()),
        ("止损价", _fmt(row.get("止损价"))),
        ("第一目标价", _fmt(row.get("第一目标价"))),
        ("第二目标价", _fmt(row.get("第二目标价"))),
        ("计划盈亏比", str(row.get("计划盈亏比", "")).strip()),
    ]
    field_html = "".join(
        f'<span class="score">{html.escape(label)} {html.escape(value)}</span>'
        for label, value in fields
        if value
    )
    chase_rule = str(row.get("追高纪律", "")).strip()
    chase_html = f'<p class="analysis">{html.escape(chase_rule)}</p>' if chase_rule else ""
    return f"""
      <div class="detail-report">
        <h4>交易计划参考</h4>
        <p class="analysis">{html.escape(plan)}</p>
        <div class="score-row">{field_html}</div>
        {chase_html}
      </div>
    """


def _fmt(value: object) -> str:
    try:
        return f"{float(value):.1f}"
    except (TypeError, ValueError):
        return str(value)


def _labeled_detail(label: str, value: str) -> str:
    stripped = value.strip()
    if not stripped:
        return ""
    if stripped.startswith(label) or stripped.startswith(label.replace("核心", "")):
        return stripped
    return f"{label}：{stripped}"


def main() -> None:
    serve()


if __name__ == "__main__":
    main()

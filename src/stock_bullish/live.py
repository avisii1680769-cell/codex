from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time
import xml.etree.ElementTree as ET

import pandas as pd
import requests

PERIODS = ("短期", "中期", "长期")
LIVE_COLUMNS = [
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
    "建议持仓周期",
    "入选理由",
]
CACHE_PATH = Path("outputs/live-web/latest_spot.csv")
EASTMONEY_HOSTS = (
    "push2.eastmoney.com",
    "82.push2.eastmoney.com",
    "15.push2.eastmoney.com",
)
TENCENT_WATCHLIST = (
    "600000",
    "600030",
    "600036",
    "600050",
    "600276",
    "600519",
    "600690",
    "600887",
    "601012",
    "601166",
    "601318",
    "601328",
    "601398",
    "601601",
    "601668",
    "601688",
    "601857",
    "601888",
    "601899",
    "601988",
    "000001",
    "000002",
    "000063",
    "000333",
    "000651",
    "000858",
    "002027",
    "002142",
    "002230",
    "002415",
    "002475",
    "002594",
    "002714",
    "300014",
    "300015",
    "300059",
    "300122",
    "300124",
    "300274",
    "300308",
    "300347",
    "300408",
    "300498",
    "300750",
)
COL_CODE = LIVE_COLUMNS[2]
COL_NAME = LIVE_COLUMNS[3]
COL_LAST_PRICE = LIVE_COLUMNS[4]
COL_CHANGE_PCT = LIVE_COLUMNS[5]
COL_AMOUNT = LIVE_COLUMNS[6]
COL_TURNOVER = LIVE_COLUMNS[7]
COL_VOLUME_RATIO = LIVE_COLUMNS[8]
COL_AMPLITUDE = LIVE_COLUMNS[9]
COL_TOTAL_MARKET_VALUE = "\u603b\u5e02\u503c"
COL_PB = "\u5e02\u51c0\u7387"
COL_PE_DYNAMIC = "\u5e02\u76c8\u7387-\u52a8\u6001"


def fetch_live_spot() -> pd.DataFrame:
    try:
        spot = _fetch_live_spot_from_sources()
    except Exception as exc:
        cached = _read_cached_spot()
        if cached is not None:
            cached.attrs["raw_count"] = len(cached)
            cached.attrs["filtered_count"] = len(cached)
            cached.attrs["scan_scope"] = "缓存行情"
            cached.attrs["data_source"] = "本地缓存"
            return cached
        raise RuntimeError("实时行情源暂时无响应，请稍后重新扫描。") from exc
    attrs = dict(spot.attrs)
    if len(spot) <= 500:
        spot = _enrich_financial_evidence(spot)
    spot.attrs.update(attrs)
    _write_cached_spot(spot)
    return spot


def _fetch_live_spot_from_sources() -> pd.DataFrame:
    errors = []
    for host in EASTMONEY_HOSTS:
        try:
            return _fetch_eastmoney_spot(host)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{host}: {exc}")
    try:
        return _fetch_akshare_spot()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"akshare: {exc}")
    try:
        frame = _fetch_tencent_spot()
        frame.attrs["raw_count"] = len(frame)
        frame.attrs["filtered_count"] = len(frame)
        frame.attrs["scan_scope"] = "高流动性观察池"
        frame.attrs["data_source"] = "腾讯观察池备用行情"
        return frame
    except Exception as exc:  # noqa: BLE001
        errors.append(f"qt.gtimg.cn: {exc}")
    raise RuntimeError("; ".join(errors) or "no live data source configured")


def _fetch_eastmoney_spot(host: str = EASTMONEY_HOSTS[0]) -> pd.DataFrame:
    url = f"https://{host}/api/qt/clist/get"
    session = requests.Session()
    session.trust_env = True
    session.headers.update(
        {
            "Accept": "application/json,text/plain,*/*",
            "Referer": "https://quote.eastmoney.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
        }
    )
    rows = []
    raw_count = 0
    for page in range(1, 80):
        params = {
            "pn": page,
            "pz": 100,
            "po": 1,
            "np": 1,
            "ut": "bd1d9ddb04089700cf9c27f6f7426281",
            "fltt": 2,
            "invt": 2,
            "fid": "f12",
            "fs": "m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23,m:0+t:81+s:2048",
            "fields": "f2,f3,f6,f7,f8,f10,f12,f14,f20,f23,f115",
        }
        response = _get_with_retry(session, url, params)
        if response is None:
            break
        data = response.json().get("data") or {}
        raw_count = int(data.get("total") or raw_count or 0)
        diff = data.get("diff") or []
        if not diff:
            break
        rows.extend(diff)

    if not rows:
        raise RuntimeError("无法获取实时行情，请稍后重试。")

    frame = pd.DataFrame(rows).rename(
        columns={
            "f2": "最新价",
            "f3": "涨跌幅",
            "f6": "成交额",
            "f7": "振幅",
            "f8": "换手率",
            "f10": "量比",
            "f12": "代码",
            "f14": "名称",
            "f20": "总市值",
            "f23": "市净率",
            "f115": "市盈率-动态",
        }
    )
    filtered = _filter_a_share_universe(frame)
    filtered.attrs["raw_count"] = raw_count or len(frame)
    filtered.attrs["filtered_count"] = len(filtered)
    filtered.attrs["scan_scope"] = "全A股实时行情"
    filtered.attrs["data_source"] = "东方财富全市场行情"
    return filtered


def _fetch_akshare_spot() -> pd.DataFrame:
    try:
        import akshare as ak  # type: ignore[import-not-found]
    except ImportError as exc:
        raise RuntimeError("AkShare 未安装，无法使用备用全市场行情源。") from exc

    source = ak.stock_info_a_code_name()
    if source.empty:
        raise RuntimeError("AkShare A 股代码列表返回为空。")
    code_column = "code" if "code" in source.columns else "代码"
    name_column = "name" if "name" in source.columns else "名称"
    code_frame = source.rename(columns={code_column: "代码", name_column: "名称"}).copy()
    code_frame["代码"] = code_frame["代码"].astype(str).str.zfill(6)
    code_frame["名称"] = code_frame["名称"].astype(str)
    code_frame = _filter_code_name_universe(code_frame)
    if code_frame.empty:
        raise RuntimeError("AkShare A 股代码列表过滤后为空。")
    quote = _fetch_tencent_spot_for_codes(code_frame["代码"].tolist())
    if quote.empty:
        raise RuntimeError("腾讯批量行情未返回 AkShare 代码列表行情。")
    filtered = _filter_a_share_universe(quote.merge(code_frame, on="代码", how="left", suffixes=("", "_列表")))
    if "名称_列表" in filtered.columns:
        filtered["名称"] = filtered["名称"].where(filtered["名称"].astype(str) != "", filtered["名称_列表"])
        filtered = filtered.drop(columns=["名称_列表"])
    filtered.attrs["raw_count"] = len(source)
    filtered.attrs["filtered_count"] = len(filtered)
    filtered.attrs["scan_scope"] = "全A股实时行情"
    filtered.attrs["data_source"] = "AkShare 代码列表 + 腾讯批量行情"
    return filtered


def _filter_code_name_universe(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    allowed_prefixes = ("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "689")
    is_allowed_board = result["代码"].str.startswith(allowed_prefixes)
    is_normal_name = ~result["名称"].str.contains("ST|退", case=False, regex=True, na=False)
    return result[is_allowed_board & is_normal_name].reset_index(drop=True)


def _filter_a_share_universe(frame: pd.DataFrame) -> pd.DataFrame:
    if frame.empty or "代码" not in frame.columns:
        return frame
    result = frame.copy()
    result["代码"] = result["代码"].astype(str).str.zfill(6)
    result["名称"] = result["名称"].astype(str)
    allowed_prefixes = ("000", "001", "002", "003", "300", "301", "600", "601", "603", "605", "688", "689")
    is_allowed_board = result["代码"].str.startswith(allowed_prefixes)
    is_normal_name = ~result["名称"].str.contains("ST|退", case=False, regex=True, na=False)
    for column in ["最新价", "成交额"]:
        if column not in result.columns:
            result[column] = 0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0)
    is_trading = (result["最新价"] > 0) & (result["成交额"] > 0)
    return result[is_allowed_board & is_normal_name & is_trading].reset_index(drop=True)


def _fetch_tencent_spot() -> pd.DataFrame:
    return _fetch_tencent_spot_for_codes(TENCENT_WATCHLIST)


def _fetch_tencent_spot_for_codes(codes: list[str] | tuple[str, ...]) -> pd.DataFrame:
    session = requests.Session()
    session.headers.update(
        {
            "Accept": "*/*",
            "Referer": "https://gu.qq.com/",
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/125.0 Safari/537.36"
            ),
        }
    )
    rows = []
    symbols = [_tencent_symbol(str(code)) for code in codes]
    for start in range(0, len(symbols), 60):
        url = "https://qt.gtimg.cn/q=" + ",".join(symbols[start : start + 60])
        response = session.get(url, timeout=20)
        response.raise_for_status()
        response.encoding = "gbk"
        rows.extend(_parse_tencent_rows(response.text))

    if not rows:
        raise RuntimeError("tencent source returned no rows")
    return pd.DataFrame(rows)


def _tencent_symbol(code: str) -> str:
    return ("sh" if code.startswith("6") else "sz") + code


def _parse_tencent_rows(payload: str) -> list[dict[str, object]]:
    rows = []
    for record in payload.split(";"):
        if '="' not in record:
            continue
        raw = record.split('="', 1)[1].rstrip('"')
        parts = raw.split("~")
        if len(parts) < 58 or not parts[2]:
            continue
        rows.append(
            {
                COL_CODE: parts[2],
                COL_NAME: parts[1],
                COL_LAST_PRICE: _float_or_zero(parts[3]),
                COL_CHANGE_PCT: _float_or_zero(parts[32]),
                COL_AMOUNT: _float_or_zero(parts[57]) * 10_000,
                COL_TURNOVER: _float_or_zero(parts[38]),
                COL_VOLUME_RATIO: _float_or_zero(parts[49]),
                COL_AMPLITUDE: _float_or_zero(parts[43]),
                COL_TOTAL_MARKET_VALUE: _float_or_zero(parts[45]) * 100_000_000,
                COL_PB: _float_or_zero(parts[46]),
                COL_PE_DYNAMIC: _float_or_zero(parts[39]),
            }
        )
    return rows


def _float_or_zero(value: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _get_with_retry(
    session: requests.Session,
    url: str,
    params: dict[str, object],
    attempts: int = 3,
) -> requests.Response | None:
    for attempt in range(attempts):
        try:
            response = session.get(url, params=params, timeout=15)
            response.raise_for_status()
            return response
        except requests.RequestException:
            if attempt < attempts - 1:
                time.sleep(1 + attempt)
    return None


def _read_cached_spot() -> pd.DataFrame | None:
    if not CACHE_PATH.exists():
        return None
    try:
        return pd.read_csv(CACHE_PATH)
    except Exception:
        return None


def _write_cached_spot(spot: pd.DataFrame) -> None:
    try:
        CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
        spot.to_csv(CACHE_PATH, index=False, encoding="utf-8-sig")
    except Exception:
        return


def scan_live_candidates(limit: int = 5) -> tuple[dict[str, pd.DataFrame], str, dict[str, object]]:
    spot = fetch_live_spot()
    analysis_spot = _prepare_deep_analysis_spot(spot, limit)
    candidates = rank_live_candidates(analysis_spot, limit=limit)
    candidates = _enrich_selected_risks(candidates)
    metadata = {
        "raw_count": int(spot.attrs.get("raw_count", len(spot))),
        "filtered_count": int(spot.attrs.get("filtered_count", len(spot))),
        "deep_analysis_count": len(analysis_spot),
        "scan_scope": spot.attrs.get("scan_scope", "未知扫描范围"),
        "data_source": spot.attrs.get("data_source", "未知数据源"),
    }
    return candidates, datetime.now().strftime("%Y-%m-%d %H:%M:%S"), metadata


def _prepare_deep_analysis_spot(spot: pd.DataFrame, limit: int) -> pd.DataFrame:
    if spot.empty or len(spot) <= 500:
        return spot
    preliminary = rank_live_candidates(spot, limit=max(limit * 10, 50))
    codes = {
        str(code).zfill(6)
        for frame in preliminary.values()
        for code in frame.get("代码", pd.Series(dtype=str)).dropna().astype(str)
    }
    if not codes:
        return spot.head(max(limit * 10, 50)).copy()
    subset = spot[spot["代码"].astype(str).str.zfill(6).isin(codes)].copy()
    attrs = dict(spot.attrs)
    enriched = _enrich_financial_evidence(subset)
    enriched.attrs.update(attrs)
    return enriched


def rank_live_candidates(spot: pd.DataFrame, limit: int = 20) -> dict[str, pd.DataFrame]:
    if spot.empty:
        return {period: pd.DataFrame(columns=LIVE_COLUMNS) for period in PERIODS}

    df = _normalize_spot(spot)
    df = _add_industry_proxy(df)
    return {
        "短期": _rank_period(df, "短期", *_short_scores(df), limit),
        "中期": _rank_period(df, "中期", *_mid_scores(df), limit),
        "长期": _rank_period(df, "长期", *_long_scores(df), limit),
    }


def _normalize_spot(spot: pd.DataFrame) -> pd.DataFrame:
    df = spot.copy()
    for column in ["最新价", "涨跌幅", "成交额", "换手率", "量比", "振幅", "市盈率-动态", "市净率", "总市值"]:
        if column not in df.columns:
            df[column] = 0.0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    for column in [
        "净利润",
        "营收",
        "净利润同比",
        "资产负债率",
        "经营现金流",
        "应收账款",
        "存货",
        "商誉",
        "扣非净利润",
        "ROE",
        "利润评分",
        "负债评分",
        "现金流评分",
        "财报质量评分",
    ]:
        if column not in df.columns:
            df[column] = 0.0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    for column in ["代码", "名称"]:
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].astype(str)
    for column in ["行业"]:
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].astype(str)
    for column in ["多年营收连续增长", "多年利润连续增长"]:
        if column not in df.columns:
            df[column] = False
        df[column] = df[column].fillna(False).astype(bool)
    return df


def _short_scores(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    technical = (
        _clip_score(df["涨跌幅"], 0, 6) * 0.35
        + _clip_score(df["量比"], 0.8, 2.5) * 0.25
        + _clip_score(df["换手率"], 1, 8) * 0.20
        + _clip_score(df["成交额"], 100_000_000, 2_000_000_000) * 0.15
        + (100 - _clip_score(df["振幅"], 3, 12)) * 0.05
    )
    fundamental = (
        _valuation_score(df["市盈率-动态"], 5, 60) * 0.45
        + _valuation_score(df["市净率"], 0.5, 8) * 0.35
        + _clip_score(df["总市值"], 10_000_000_000, 300_000_000_000) * 0.10
        + df["财报质量评分"].clip(0, 100) * 0.10
    )
    return technical, fundamental, technical * 0.8 + fundamental * 0.2


def _mid_scores(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    technical = (
        _clip_score(df["涨跌幅"], -1, 4) * 0.25
        + _clip_score(df["成交额"], 200_000_000, 3_000_000_000) * 0.25
        + _clip_score(df["换手率"], 0.8, 5) * 0.20
    )
    fundamental = (
        _valuation_score(df["市盈率-动态"], 5, 45) * 0.25
        + _valuation_score(df["市净率"], 0.5, 5) * 0.25
        + _clip_score(df["总市值"], 20_000_000_000, 500_000_000_000) * 0.15
        + df["利润评分"].clip(0, 100) * 0.15
        + df["负债评分"].clip(0, 100) * 0.10
        + df["现金流评分"].clip(0, 100) * 0.10
    )
    return technical, fundamental, technical * 0.55 + fundamental * 0.45


def _long_scores(df: pd.DataFrame) -> tuple[pd.Series, pd.Series, pd.Series]:
    technical = (
        _clip_score(df["成交额"], 100_000_000, 2_000_000_000) * 0.10
        + _clip_score(df["换手率"], 0.2, 4) * 0.10
        + _clip_score(df["涨跌幅"], -2, 3) * 0.10
    )
    fundamental = (
        _clip_score(df["总市值"], 30_000_000_000, 500_000_000_000) * 0.20
        + _valuation_score(df["市盈率-动态"], 5, 30) * 0.20
        + _valuation_score(df["市净率"], 0.5, 3) * 0.15
        + df["利润评分"].clip(0, 100) * 0.20
        + df["负债评分"].clip(0, 100) * 0.10
        + df["现金流评分"].clip(0, 100) * 0.15
    )
    return technical, fundamental, technical * 0.25 + fundamental * 0.75


def _rank_period(
    df: pd.DataFrame,
    period: str,
    technical_score: pd.Series,
    fundamental_score: pd.Series,
    score: pd.Series,
    limit: int,
) -> pd.DataFrame:
    result = df.copy()
    result["技术面评分"] = technical_score.round(2)
    result["基本面评分"] = fundamental_score.round(2)
    result["财报质量评分"] = result["财报质量评分"].round(2)
    result["评分"] = score.round(2)
    result["看涨评分"] = (50 + result["评分"] * 0.45).clip(0, 95).round(1)
    result["周期"] = period
    result["技术面分析"] = result.apply(_technical_analysis, axis=1)
    result["基本面分析"] = result.apply(_fundamental_analysis, axis=1)
    result["利润分析"] = result.apply(_profit_analysis, axis=1)
    result["负债分析"] = result.apply(_debt_analysis, axis=1)
    result["现金流分析"] = result.apply(_cashflow_analysis, axis=1)
    result["行业景气分析"] = result.apply(_industry_analysis, axis=1)
    result["应收账款风险"] = result.apply(_receivable_risk_analysis, axis=1)
    result["存货风险"] = result.apply(_inventory_risk_analysis, axis=1)
    result["商誉风险"] = result.apply(_goodwill_risk_analysis, axis=1)
    result["非经常性损益分析"] = result.apply(_nonrecurring_analysis, axis=1)
    result["ROE趋势分析"] = result.apply(_roe_trend_analysis, axis=1)
    result["多年增长分析"] = result.apply(_multi_year_growth_analysis, axis=1)
    result["行业估值分位"] = result.apply(_industry_valuation_percentile_analysis, axis=1)
    result["政策周期分析"] = result.apply(_policy_cycle_analysis, axis=1)
    result["全网新闻舆情"] = result.apply(_web_news_sentiment_analysis, axis=1)
    result["历史回测胜率校准"] = result.apply(_backtest_calibration_analysis, axis=1)
    result["机构持仓分析"] = result.apply(_institution_holding_analysis, axis=1)
    result["北向资金分析"] = result.apply(_northbound_analysis, axis=1)
    result["融资融券分析"] = result.apply(_margin_financing_analysis, axis=1)
    result["主力资金流向"] = result.apply(_main_fund_flow_analysis, axis=1)
    if "公告新闻风险" not in result.columns:
        result["公告新闻风险"] = "公告/新闻风险：等待近期公告抓取。"
    if "风险等级" not in result.columns:
        result["风险等级"] = "待核查"
    result["支持证据"] = result.apply(_support_evidence, axis=1)
    result["反对证据"] = result.apply(_opposition_evidence, axis=1)
    result["建议持仓周期"] = result.apply(lambda row: _holding_period_advice(row, period), axis=1)
    result["入选理由"] = result.apply(lambda row: _reason(row, period), axis=1)
    result = result[result["评分"] > 0].sort_values("评分", ascending=False).head(limit).copy()
    result["排名"] = range(1, len(result) + 1)
    return result[LIVE_COLUMNS].reset_index(drop=True)


def _clip_score(series: pd.Series, low: float, high: float) -> pd.Series:
    if high == low:
        return pd.Series(0.0, index=series.index)
    return ((series - low) / (high - low) * 100).clip(0, 100)


def _valuation_score(series: pd.Series, low: float, high: float) -> pd.Series:
    valid = series.where(series > 0)
    midpoint = (low + high) / 2
    width = (high - low) / 2
    score = 100 - ((valid - midpoint).abs() / width * 100)
    return score.clip(0, 100).fillna(0)


def _reason(row: pd.Series, period: str) -> str:
    reasons = []
    if row["涨跌幅"] > 0:
        reasons.append("价格走强")
    if row["量比"] >= 1.5:
        reasons.append("量比活跃")
    if row["换手率"] >= 2:
        reasons.append("换手充分")
    if row["成交额"] >= 500_000_000:
        reasons.append("成交额较高")
    if period in {"中期", "长期"} and 0 < row["市盈率-动态"] <= 45:
        reasons.append("估值未极端")
    return "、".join(reasons[:4]) or "综合评分靠前"


def _technical_analysis(row: pd.Series) -> str:
    points = []
    if row["涨跌幅"] > 0:
        points.append(f"价格走强，涨跌幅 {row['涨跌幅']:.2f}%")
    if row["量比"] >= 1.2:
        points.append(f"量比 {row['量比']:.2f}，成交活跃")
    if row["换手率"] >= 1:
        points.append(f"换手率 {row['换手率']:.2f}%")
    if row["成交额"] >= 500_000_000:
        points.append(f"成交额约 {row['成交额'] / 100_000_000:.1f} 亿元")
    if not points:
        points.append("实时技术指标没有明显强势信号")
    return "技术面：" + "；".join(points[:3]) + "。"


def _fundamental_analysis(row: pd.Series) -> str:
    points = []
    pe = row["市盈率-动态"]
    pb = row["市净率"]
    market_cap = row["总市值"]
    if 0 < pe <= 45:
        points.append(f"动态市盈率 {pe:.1f}，未处于规则定义的极端高估区")
    elif pe > 45:
        points.append(f"动态市盈率 {pe:.1f}，估值偏高需谨慎")
    else:
        points.append("动态市盈率缺失或不可用")
    if 0 < pb <= 5:
        points.append(f"市净率 {pb:.2f}，处于规则可接受区间")
    elif pb > 5:
        points.append(f"市净率 {pb:.2f}，账面估值偏高")
    if market_cap > 0:
        points.append(f"总市值约 {market_cap / 100_000_000:.0f} 亿元")
    return "基本面：" + "；".join(points[:3]) + "。"


def _profit_analysis(row: pd.Series) -> str:
    profit = row["净利润"]
    revenue = row["营收"]
    growth = row["净利润同比"]
    if profit == 0 and revenue == 0:
        return "利润：未取得可靠利润表数据。"
    parts = [f"净利润约 {profit / 100_000_000:.1f} 亿元", f"营收约 {revenue / 100_000_000:.1f} 亿元"]
    if growth:
        parts.append(f"净利润同比 {growth:.1f}%")
    return "利润：" + "；".join(parts) + "。"


def _debt_analysis(row: pd.Series) -> str:
    debt_ratio = row["资产负债率"]
    if debt_ratio == 0:
        return "负债：未取得可靠资产负债表数据。"
    level = "偏高，需结合行业特征判断" if debt_ratio > 70 else "处于规则可接受区间"
    return f"负债：资产负债率约 {debt_ratio:.1f}%，{level}。"


def _cashflow_analysis(row: pd.Series) -> str:
    cashflow = row["经营现金流"]
    if cashflow == 0:
        return "现金流：未取得可靠现金流量表数据。"
    direction = "为正，对经营质量有支持" if cashflow > 0 else "为负，需要进一步核查经营质量"
    return f"现金流：经营现金流约 {cashflow / 100_000_000:.1f} 亿元，{direction}。"


def _industry_analysis(row: pd.Series) -> str:
    industry = row.get("行业", "")
    if not industry:
        return "行业景气：未取得可靠行业数据，暂不做景气判断。"
    sample_count = int(row.get("行业样本数", 0) or 0)
    avg_change = float(row.get("行业平均涨跌幅", 0) or 0)
    avg_turnover = float(row.get("行业平均换手率", 0) or 0)
    return (
        f"行业景气：所属行业为 {industry}；同业样本 {sample_count} 只，"
        f"样本平均涨跌幅 {avg_change:.2f}%，平均换手率 {avg_turnover:.2f}%。"
        "这是当前股票池内的行业强弱代理，不是完整行业景气指数。"
    )


def _add_industry_proxy(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    if "行业" not in result.columns:
        result["行业"] = ""
    valid = result[result["行业"].astype(str) != ""]
    if valid.empty:
        result["行业样本数"] = 0
        result["行业平均涨跌幅"] = 0.0
        result["行业平均换手率"] = 0.0
        return result
    grouped = valid.groupby("行业").agg(
        行业样本数=("代码", "size"),
        行业平均涨跌幅=("涨跌幅", "mean"),
        行业平均换手率=("换手率", "mean"),
    )
    result = result.merge(grouped, on="行业", how="left").fillna(
        {"行业样本数": 0, "行业平均涨跌幅": 0.0, "行业平均换手率": 0.0}
    )
    pe = result["市盈率-动态"].where(result["市盈率-动态"] > 0)
    result["行业PE分位"] = pe.groupby(result["行业"]).rank(pct=True).fillna(0.0) * 100
    return result


def _receivable_risk_analysis(row: pd.Series) -> str:
    receivable = _row_number(row, "应收账款")
    revenue = _row_number(row, "营收")
    if receivable == 0:
        return "应收账款：未取得可靠应收账款数据。"
    ratio = receivable / revenue * 100 if revenue else 0
    level = "偏高，需核查回款质量" if ratio > 30 else "处于规则可接受区间"
    return f"应收账款：约 {receivable / 100_000_000:.1f} 亿元，占营收约 {ratio:.1f}%，{level}。"


def _inventory_risk_analysis(row: pd.Series) -> str:
    inventory = _row_number(row, "存货")
    revenue = _row_number(row, "营收")
    if inventory == 0:
        return "存货：未取得可靠存货数据。"
    ratio = inventory / revenue * 100 if revenue else 0
    level = "偏高，需核查跌价和周转风险" if ratio > 40 else "处于规则可接受区间"
    return f"存货：约 {inventory / 100_000_000:.1f} 亿元，占营收约 {ratio:.1f}%，{level}。"


def _goodwill_risk_analysis(row: pd.Series) -> str:
    goodwill = _row_number(row, "商誉")
    market_cap = _row_number(row, "总市值")
    if goodwill == 0:
        return "商誉：未取得可靠商誉数据或商誉较低。"
    ratio = goodwill / market_cap * 100 if market_cap else 0
    level = "偏高，需核查减值风险" if ratio > 10 else "占市值比例不高"
    return f"商誉：约 {goodwill / 100_000_000:.1f} 亿元，占市值约 {ratio:.1f}%，{level}。"


def _nonrecurring_analysis(row: pd.Series) -> str:
    profit = _row_number(row, "净利润")
    deduct_profit = _row_number(row, "扣非净利润")
    if deduct_profit == 0:
        return "非经常性损益：未取得可靠扣非净利润数据。"
    gap = profit - deduct_profit
    ratio = gap / abs(profit) * 100 if profit else 0
    level = "非经常性损益占比较高" if ratio > 30 else "扣非后利润差异不大"
    return f"非经常性损益：扣非净利润约 {deduct_profit / 100_000_000:.1f} 亿元，{level}。"


def _roe_trend_analysis(row: pd.Series) -> str:
    roe = _row_number(row, "ROE")
    if roe == 0:
        return "ROE趋势：未取得可靠 ROE 多期数据。"
    return f"ROE趋势：最新 ROE 约 {roe:.1f}%；多期趋势仍需结合后续报告持续校准。"


def _multi_year_growth_analysis(row: pd.Series) -> str:
    revenue_growth = bool(row.get("多年营收连续增长", False))
    profit_growth = bool(row.get("多年利润连续增长", False))
    return (
        "多年增长："
        f"营收连续增长={'是' if revenue_growth else '否或数据不足'}；"
        f"利润连续增长={'是' if profit_growth else '否或数据不足'}。"
    )


def _industry_valuation_percentile_analysis(row: pd.Series) -> str:
    percentile = _row_number(row, "行业PE分位")
    if percentile == 0:
        return "行业估值分位：同业估值样本不足，暂不判断。"
    return f"行业估值分位：当前动态市盈率约处于同业样本第 {percentile:.0f} 分位。"


def _policy_cycle_analysis(row: pd.Series) -> str:
    return "政策周期：未取得可靠政策周期结构化数据，暂不参与加分。"


def _web_news_sentiment_analysis(row: pd.Series) -> str:
    titles = row.get("新闻标题列表", [])
    if not isinstance(titles, list) or not titles:
        return "全网新闻舆情：未取得可靠新闻搜索结果，暂不参与加分。"
    risk_words = ("问询", "监管", "处罚", "立案", "诉讼", "仲裁", "减持", "亏损", "退市", "风险", "暴跌")
    positive_words = ("增长", "回购", "增持", "中标", "突破", "创新高", "盈利", "改善")
    risky = [title for title in titles if any(word in title for word in risk_words)]
    positive = [title for title in titles if any(word in title for word in positive_words)]
    if risky:
        return "全网新闻舆情：新闻搜索结果含风险词，需核查：" + "；".join(risky[:2]) + "。"
    if positive:
        return "全网新闻舆情：新闻搜索结果偏正面，但只作为辅助证据：" + "；".join(positive[:2]) + "。"
    return "全网新闻舆情：新闻搜索结果未见明显风险词，样本标题：" + "；".join(titles[:2]) + "。"


def _backtest_calibration_analysis(row: pd.Series) -> str:
    return "历史回测：当前实时候选尚未与历史 5/20/60 日胜率校准打通。"


def _institution_holding_analysis(row: pd.Series) -> str:
    org_count = _row_number(row, "互联互通机构数量")
    org_change = _row_number(row, "互联互通机构数量变化率")
    if org_count:
        direction = "增加" if org_change > 0 else "减少或持平"
        return (
            f"机构持仓：互联互通披露口径下机构数量约 {org_count:.0f} 家，"
            f"较上期{direction}，变化率约 {org_change:.1f}%。这是持仓代理指标，不等同于全市场机构持仓。"
        )
    return "机构持仓：未取得可靠最新机构持仓数据，暂不参与加分。"


def _northbound_analysis(row: pd.Series) -> str:
    holding = _row_number(row, "互联互通持股数")
    add_shares = _row_number(row, "互联互通增持股数")
    ratio = _row_number(row, "互联互通流通股占比")
    date = str(row.get("互联互通持仓日期", "") or "")
    if holding:
        direction = "增持" if add_shares > 0 else "减持" if add_shares < 0 else "持平"
        date_text = date[:10] if date else "最近披露期"
        return (
            f"北向/互联互通持仓：截至 {date_text}，持股约 {holding / 10000:.1f} 万股，"
            f"本期{direction}约 {abs(add_shares) / 10000:.1f} 万股，流通股占比约 {ratio:.2f}%。"
        )
    return "北向资金：未取得可靠个股北向资金数据，暂不参与加分。"


def _margin_financing_analysis(row: pd.Series) -> str:
    balance = _row_number(row, "融资余额")
    net_buy = _row_number(row, "融资净买额")
    five_day = _row_number(row, "5日融资净买额")
    date = str(row.get("融资融券日期", "") or "")
    if balance:
        direction = "净买入" if net_buy > 0 else "净偿还" if net_buy < 0 else "基本持平"
        date_text = date[:10] if date else "最近交易日"
        return (
            f"融资融券：截至 {date_text}，融资余额约 {balance / 100_000_000:.1f} 亿元，"
            f"当日融资{direction}约 {abs(net_buy) / 100_000_000:.2f} 亿元，"
            f"5日融资净额约 {five_day / 100_000_000:.2f} 亿元。"
        )
    return "融资融券：未取得可靠个股融资融券数据，暂不参与加分。"


def _main_fund_flow_analysis(row: pd.Series) -> str:
    main_net = _row_number(row, "主力净流入")
    main_ratio = _row_number(row, "主力净占比")
    if main_net:
        direction = "净流入" if main_net > 0 else "净流出"
        return f"主力资金：当日主力资金{direction}约 {abs(main_net) / 100_000_000:.2f} 亿元，净占比约 {main_ratio:.2f}%。"
    return "主力资金：未取得可靠实时主力资金流向数据，暂不参与加分。"


def _support_evidence(row: pd.Series) -> str:
    evidence = []
    if _row_number(row, "技术面评分") >= 60:
        evidence.append("技术面活跃")
    if _row_number(row, "基本面评分") >= 60:
        evidence.append("基本面评分靠前")
    if _row_number(row, "财报质量评分") >= 60:
        evidence.append("财报质量评分较好")
    if _row_number(row, "经营现金流") > 0:
        evidence.append("经营现金流为正")
    pe = _row_number(row, "市盈率-动态")
    if 0 < pe <= 45:
        evidence.append("估值未处于规则定义的极端高估区")
    if _row_number(row, "主力净流入") > 0:
        evidence.append("主力资金净流入")
    if _row_number(row, "融资净买额") > 0:
        evidence.append("融资资金净买入")
    if _row_number(row, "互联互通增持股数") > 0:
        evidence.append("互联互通持仓增持")
    if not evidence:
        evidence.append("综合排序靠前，但强支持证据不足")
    return "支持：" + "；".join(evidence[:4]) + "。"


def _opposition_evidence(row: pd.Series) -> str:
    evidence = []
    risk_level = str(row.get("风险等级", "待核查"))
    if risk_level in {"中", "高"}:
        evidence.append(f"公告/新闻风险等级为{row['风险等级']}")
    profit_growth = _row_number(row, "净利润同比")
    if profit_growth < 0:
        evidence.append(f"净利润同比 {profit_growth:.1f}%")
    if _row_number(row, "经营现金流") < 0:
        evidence.append("经营现金流为负")
    debt_ratio = _row_number(row, "资产负债率")
    if debt_ratio > 70:
        evidence.append(f"资产负债率 {debt_ratio:.1f}% 偏高")
    pe = _row_number(row, "市盈率-动态")
    if pe > 60:
        evidence.append(f"动态市盈率 {pe:.1f} 偏高")
    if int(row.get("行业样本数", 0) or 0) < 3:
        evidence.append("行业代理样本偏少")
    if _row_number(row, "主力净流入") < 0:
        evidence.append("主力资金净流出")
    if _row_number(row, "融资净买额") < 0:
        evidence.append("融资资金净偿还")
    if _row_number(row, "互联互通增持股数") < 0:
        evidence.append("互联互通持仓减持")
    if not evidence:
        evidence.append("暂未发现规则内的明显反对证据")
    return "反对：" + "；".join(evidence[:4]) + "。"


def _holding_period_advice(row: pd.Series, period: str) -> str:
    turnover = _row_number(row, "换手率")
    volume_ratio = _row_number(row, "量比")
    change_pct = _row_number(row, "涨跌幅")
    risk_level = str(row.get("风险等级", "待核查"))
    news = str(row.get("全网新闻舆情", ""))
    opposition = str(row.get("反对证据", ""))
    margin_net = _row_number(row, "融资净买额")
    northbound_add = _row_number(row, "互联互通增持股数")

    risk_flags = 0
    if risk_level in {"中", "高"}:
        risk_flags += 1
    if any(word in news for word in ("含风险词", "需核查", "异常波动", "非理性炒作", "快速下跌")):
        risk_flags += 1
    if any(word in opposition for word in ("净偿还", "减持", "净流出", "偏高", "样本偏少")):
        risk_flags += 1
    if margin_net < 0:
        risk_flags += 1
    if northbound_add < 0:
        risk_flags += 1

    hot_trade = turnover >= 20 or volume_ratio >= 5 or change_pct >= 9.5

    if period == "短期":
        if hot_trade or risk_flags >= 2:
            return "建议持仓周期：1-2 个交易日；高换手或风险提示较强，必须按短线纪律观察。"
        if risk_flags == 1:
            return "建议持仓周期：2-3 个交易日；有分歧证据，不能无条件延长。"
        return "建议持仓周期：3-5 个交易日；若放量延续可继续观察，否则按短线处理。"

    if period == "中期":
        if hot_trade or risk_flags >= 2:
            return "建议持仓周期：1-2 周；短线波动较强或风险证据偏多，中期逻辑需等待确认。"
        if risk_flags == 1:
            return "建议持仓周期：2-4 周；边走边验证财报、资金和行业强度。"
        return "建议持仓周期：4-6 周；适合按波段跟踪，但仍需周度复盘。"

    if hot_trade or risk_flags >= 2:
        return "建议持仓周期：1-3 个月；长期候选存在交易拥挤或风险证据，先按观察仓思路处理。"
    if risk_flags == 1:
        return "建议持仓周期：3-6 个月；基本面仍需季度财报和资金面继续验证。"
    return "建议持仓周期：6-12 个月；仅在基本面、现金流和风险提示持续稳定时适用。"


def _row_number(row: pd.Series, column: str) -> float:
    try:
        return float(row.get(column, 0) or 0)
    except (TypeError, ValueError):
        return 0.0


def _fetch_market_evidence(codes: list[str]) -> pd.DataFrame:
    frames = []
    for fetcher in (
        _fetch_margin_financing_evidence,
        _fetch_northbound_holding_evidence,
        _fetch_main_fund_flow_evidence,
    ):
        try:
            frame = fetcher(codes)
        except Exception:
            continue
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame(columns=["代码"])
    result = frames[0]
    for frame in frames[1:]:
        result = result.merge(frame, on="代码", how="outer")
    return result


def _fetch_margin_financing_evidence(codes: list[str]) -> pd.DataFrame:
    rows = _fetch_datacenter_rows(
        {
            "sortColumns": "DATE",
            "sortTypes": "-1",
            "pageSize": min(max(len(codes) * 4, 20), 200),
            "pageNumber": 1,
            "reportName": "RPTA_WEB_RZRQ_GGMX",
            "columns": "ALL",
            "filter": _in_filter("SCODE", codes),
        }
    )
    return _parse_margin_financing_rows(rows)


def _parse_margin_financing_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["代码"])
    frame = pd.DataFrame(rows)
    frame = frame.sort_values("DATE", ascending=False).drop_duplicates("SCODE")
    return frame.rename(
        columns={
            "SCODE": "代码",
            "DATE": "融资融券日期",
            "RZYE": "融资余额",
            "RQYE": "融券余额",
            "RZJME": "融资净买额",
            "RZJME5D": "5日融资净买额",
            "RZJME10D": "10日融资净买额",
        }
    )[["代码", "融资融券日期", "融资余额", "融券余额", "融资净买额", "5日融资净买额", "10日融资净买额"]]


def _fetch_northbound_holding_evidence(codes: list[str]) -> pd.DataFrame:
    rows = _fetch_datacenter_rows(
        {
            "sortColumns": "HOLD_DATE,HOLD_MARKET_CAP",
            "sortTypes": "-1,-1",
            "pageSize": min(max(len(codes) * 4, 20), 200),
            "pageNumber": 1,
            "reportName": "RPT_MUTUAL_HOLDRANK_NEW",
            "columns": "ALL",
            "filter": _in_filter("SECURITY_CODE", codes),
        }
    )
    return _parse_northbound_holding_rows(rows)


def _parse_northbound_holding_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["代码"])
    frame = pd.DataFrame(rows)
    frame = frame.sort_values("HOLD_DATE", ascending=False).drop_duplicates("SECURITY_CODE")
    return frame.rename(
        columns={
            "SECURITY_CODE": "代码",
            "HOLD_DATE": "互联互通持仓日期",
            "HOLD_SHARES": "互联互通持股数",
            "ADD_SHARES_REPAIR": "互联互通增持股数",
            "HOLD_MARKET_CAP": "互联互通持仓市值",
            "FREE_SHARES_RATIO": "互联互通流通股占比",
            "ORG_QUANTITY": "互联互通机构数量",
            "ORG_QUANTITY_RATIO": "互联互通机构数量变化率",
        }
    )[
        [
            "代码",
            "互联互通持仓日期",
            "互联互通持股数",
            "互联互通增持股数",
            "互联互通持仓市值",
            "互联互通流通股占比",
            "互联互通机构数量",
            "互联互通机构数量变化率",
        ]
    ]


def _fetch_main_fund_flow_evidence(codes: list[str]) -> pd.DataFrame:
    if not codes:
        return pd.DataFrame(columns=["代码"])
    secids = ",".join(_eastmoney_secid(code) for code in codes)
    session = requests.Session()
    session.trust_env = False
    response = session.get(
        "https://push2.eastmoney.com/api/qt/ulist.np/get",
        params={
            "fltt": "2",
            "secids": secids,
            "fields": "f12,f62,f184,f66,f72,f78,f84",
            "ut": "b2884a393a59ad64002292a3e90d46a5",
        },
        timeout=15,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/zjlx/"},
    )
    response.raise_for_status()
    rows = ((response.json().get("data") or {}).get("diff") or [])
    return _parse_main_fund_flow_rows(rows)


def _parse_main_fund_flow_rows(rows: list[dict[str, object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame(columns=["代码"])
    return pd.DataFrame(rows).rename(
        columns={
            "f12": "代码",
            "f62": "主力净流入",
            "f184": "主力净占比",
            "f66": "超大单净流入",
            "f72": "大单净流入",
            "f78": "中单净流入",
            "f84": "小单净流入",
        }
    )[["代码", "主力净流入", "主力净占比", "超大单净流入", "大单净流入", "中单净流入", "小单净流入"]]


def _fetch_datacenter_rows(params: dict[str, object]) -> list[dict[str, object]]:
    session = requests.Session()
    session.trust_env = False
    response = session.get(
        "https://datacenter-web.eastmoney.com/api/data/v1/get",
        params=params,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"},
    )
    response.raise_for_status()
    return ((response.json().get("result") or {}).get("data") or [])


def _in_filter(field: str, codes: list[str]) -> str:
    quoted = ",".join(f'"{str(code).zfill(6)}"' for code in codes)
    return f"({field} in ({quoted}))"


def _eastmoney_secid(code: str) -> str:
    normalized = str(code).zfill(6)
    market = "1" if normalized.startswith("6") else "0"
    return f"{market}.{normalized}"


def _enrich_financial_evidence(spot: pd.DataFrame) -> pd.DataFrame:
    if spot.empty or "代码" not in spot.columns:
        return spot
    codes = sorted({str(code).zfill(6) for code in spot["代码"].dropna().astype(str)})
    if not codes:
        return spot
    try:
        income = _fetch_financial_report("RPT_DMSK_FN_INCOME", codes)
        balance = _fetch_financial_report("RPT_DMSK_FN_BALANCE", codes)
        cashflow = _fetch_financial_report("RPT_DMSK_FN_CASHFLOW", codes)
    except Exception:
        return spot

    enriched = spot.copy()
    for frame in (income, balance, cashflow):
        if not frame.empty:
            enriched = enriched.merge(frame, on="代码", how="left")
    return _score_financial_evidence(enriched)


def _fetch_financial_report(report_name: str, codes: list[str]) -> pd.DataFrame:
    filter_codes = ",".join(f'"{code}"' for code in codes)
    params = {
        "sortColumns": "REPORT_DATE",
        "sortTypes": "-1",
        "pageSize": min(max(len(codes) * 4, 50), 500),
        "pageNumber": 1,
        "reportName": report_name,
        "columns": "ALL",
        "filter": f"(SECURITY_CODE in ({filter_codes}))",
    }
    response = requests.get(
        "https://datacenter-web.eastmoney.com/api/data/v1/get",
        params=params,
        timeout=20,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"},
    )
    response.raise_for_status()
    rows = ((response.json().get("result") or {}).get("data") or [])
    if not rows:
        return pd.DataFrame(columns=["代码"])
    frame = pd.DataFrame(rows)
    frame = frame.sort_values("REPORT_DATE", ascending=False).drop_duplicates("SECURITY_CODE")
    if report_name == "RPT_DMSK_FN_INCOME":
        return frame.rename(
            columns={
                "SECURITY_CODE": "代码",
                "PARENT_NETPROFIT": "净利润",
                "TOTAL_OPERATE_INCOME": "营收",
                "PARENT_NETPROFIT_RATIO": "净利润同比",
                "DEDUCT_PARENT_NETPROFIT": "扣非净利润",
                "INDUSTRY_NAME": "行业",
            }
        )[["代码", "净利润", "营收", "净利润同比", "扣非净利润", "行业"]]
    if report_name == "RPT_DMSK_FN_BALANCE":
        result = frame.rename(
            columns={
                "SECURITY_CODE": "代码",
                "TOTAL_ASSETS": "总资产",
                "TOTAL_LIABILITIES": "总负债",
                "DEBT_ASSET_RATIO": "资产负债率",
                "ACCOUNTS_RECE": "应收账款",
                "INVENTORY": "存货",
                "GOODWILL": "商誉",
            }
        )
        for column in ["应收账款", "存货", "商誉"]:
            if column not in result.columns:
                result[column] = 0.0
        result = result[["代码", "总资产", "总负债", "资产负债率", "应收账款", "存货", "商誉"]]
        missing = pd.to_numeric(result["资产负债率"], errors="coerce").isna()
        result.loc[missing, "资产负债率"] = (
            pd.to_numeric(result.loc[missing, "总负债"], errors="coerce")
            / pd.to_numeric(result.loc[missing, "总资产"], errors="coerce")
            * 100
        )
        return result[["代码", "资产负债率", "应收账款", "存货", "商誉"]]
    if report_name == "RPT_DMSK_FN_CASHFLOW":
        return frame.rename(
            columns={
                "SECURITY_CODE": "代码",
                "NETCASH_OPERATE": "经营现金流",
            }
        )[["代码", "经营现金流"]]
    return pd.DataFrame(columns=["代码"])


def _score_financial_evidence(frame: pd.DataFrame) -> pd.DataFrame:
    result = frame.copy()
    for column in [
        "净利润",
        "营收",
        "净利润同比",
        "资产负债率",
        "经营现金流",
        "应收账款",
        "存货",
        "商誉",
        "扣非净利润",
        "ROE",
    ]:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
    for column in ["多年营收连续增长", "多年利润连续增长"]:
        if column not in result.columns:
            result[column] = False
    if "行业" not in result.columns:
        result["行业"] = ""
    result["行业"] = result["行业"].fillna("").astype(str)
    margin = (result["净利润"] / result["营收"].where(result["营收"] != 0)).fillna(0.0) * 100
    result["利润评分"] = (
        _clip_score(result["净利润"], 0, 20_000_000_000) * 0.45
        + _clip_score(margin, 0, 25) * 0.35
        + _clip_score(result["净利润同比"], -30, 30) * 0.20
    )
    result["负债评分"] = (100 - _clip_score(result["资产负债率"], 30, 90)).clip(0, 100)
    result["现金流评分"] = _clip_score(result["经营现金流"], -5_000_000_000, 20_000_000_000)
    result["财报质量评分"] = (
        result["利润评分"] * 0.45 + result["负债评分"] * 0.25 + result["现金流评分"] * 0.30
    )
    return result


def _enrich_selected_risks(candidates: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    enriched = {}
    for period, frame in candidates.items():
        if frame.empty:
            enriched[period] = frame
            continue
        result = frame.copy()
        codes = sorted({str(code).zfill(6) for code in result["代码"].dropna().astype(str)})
        market_evidence = _fetch_market_evidence(codes)
        if not market_evidence.empty:
            result = result.merge(market_evidence, on="代码", how="left")
            result["机构持仓分析"] = result.apply(_institution_holding_analysis, axis=1)
            result["北向资金分析"] = result.apply(_northbound_analysis, axis=1)
            result["融资融券分析"] = result.apply(_margin_financing_analysis, axis=1)
            result["主力资金流向"] = result.apply(_main_fund_flow_analysis, axis=1)
        result["新闻标题列表"] = result.apply(
            lambda row: _fetch_news_titles(str(row.get("名称", "")), str(row.get("代码", ""))),
            axis=1,
        )
        result["全网新闻舆情"] = result.apply(_web_news_sentiment_analysis, axis=1)
        risk = result["代码"].astype(str).apply(_announcement_risk_analysis)
        result["公告新闻风险"] = risk.apply(lambda item: item[0])
        result["风险等级"] = risk.apply(lambda item: item[1])
        result["支持证据"] = result.apply(_support_evidence, axis=1)
        result["反对证据"] = result.apply(_opposition_evidence, axis=1)
        result["建议持仓周期"] = result.apply(lambda row: _holding_period_advice(row, period), axis=1)
        enriched[period] = result
    return enriched


def _announcement_risk_analysis(code: str) -> tuple[str, str]:
    try:
        titles = _fetch_recent_announcement_titles(str(code).zfill(6))
    except Exception:
        return "公告/新闻风险：未取得可靠近期公告数据。", "待核查"
    if not titles:
        return "公告/新闻风险：近期公告标题未见明显风险词。", "低"
    high_words = ("立案", "处罚", "退市", "重大亏损", "终止上市")
    medium_words = ("问询", "诉讼", "仲裁", "减持", "亏损", "风险", "终止")
    high_risky = [title for title in titles if any(word in title for word in high_words)]
    if high_risky:
        return "公告/新闻风险：近期公告含高风险词，需核查：" + "；".join(high_risky[:2]) + "。", "高"
    medium_risky = [title for title in titles if any(word in title for word in medium_words)]
    if medium_risky:
        return "公告/新闻风险：近期公告含风险词，需核查：" + "；".join(medium_risky[:2]) + "。", "中"
    return "公告/新闻风险：近期公告标题未见明显风险词。", "低"


def _fetch_recent_announcement_titles(code: str) -> list[str]:
    response = requests.get(
        "https://np-anotice-stock.eastmoney.com/api/security/ann",
        params={
            "sr": "-1",
            "page_size": "5",
            "page_index": "1",
            "ann_type": "A",
            "client_source": "web",
            "stock_list": code,
        },
        timeout=12,
        headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"},
    )
    response.raise_for_status()
    rows = ((response.json().get("data") or {}).get("list") or [])
    return [str(row.get("title", "")) for row in rows if row.get("title")]


def _fetch_news_titles(name: str, code: str, limit: int = 5) -> list[str]:
    keyword = (name or code or "").strip()
    if not keyword:
        return []
    queries = [f"{keyword} 股票", f"{keyword} 财报"]
    titles: list[str] = []
    for query in queries:
        for url in _news_rss_urls(query):
            try:
                response = requests.get(
                    url,
                    timeout=10,
                    headers={"User-Agent": "Mozilla/5.0"},
                )
                response.raise_for_status()
                titles.extend(_parse_news_rss_titles(response.text))
            except Exception:
                continue
            if len(titles) >= limit:
                break
        if len(titles) >= limit:
            break
    deduped = []
    seen = set()
    for title in titles:
        normalized = title.strip()
        if normalized and normalized not in seen:
            deduped.append(normalized)
            seen.add(normalized)
        if len(deduped) >= limit:
            break
    return deduped


def _news_rss_urls(query: str) -> list[str]:
    from urllib.parse import quote

    encoded = quote(query)
    return [
        f"https://www.bing.com/news/search?q={encoded}&format=RSS",
        f"https://news.google.com/rss/search?q={encoded}&hl=zh-CN&gl=CN&ceid=CN:zh-Hans",
    ]


def _parse_news_rss_titles(payload: str) -> list[str]:
    root = ET.fromstring(payload)
    titles = []
    for item in root.findall(".//item"):
        title = item.findtext("title")
        if title:
            titles.append(title.strip())
    return titles

from __future__ import annotations

from datetime import datetime
from pathlib import Path
import time

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
            return cached
        raise RuntimeError("实时行情源暂时无响应，请稍后重新扫描。") from exc
    spot = _enrich_financial_evidence(spot)
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
        return _fetch_tencent_spot()
    except Exception as exc:  # noqa: BLE001
        errors.append(f"qt.gtimg.cn: {exc}")
    raise RuntimeError("; ".join(errors) or "no live data source configured")


def _fetch_eastmoney_spot(host: str = EASTMONEY_HOSTS[0]) -> pd.DataFrame:
    url = f"https://{host}/api/qt/clist/get"
    session = requests.Session()
    session.trust_env = False
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
        diff = data.get("diff") or []
        if not diff:
            break
        rows.extend(diff)

    if not rows:
        raise RuntimeError("无法获取实时行情，请稍后重试。")

    frame = pd.DataFrame(rows)
    return frame.rename(
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


def _fetch_tencent_spot() -> pd.DataFrame:
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
    symbols = [_tencent_symbol(code) for code in TENCENT_WATCHLIST]
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


def scan_live_candidates(limit: int = 5) -> tuple[dict[str, pd.DataFrame], str]:
    spot = fetch_live_spot()
    candidates = rank_live_candidates(spot, limit=limit)
    candidates = _enrich_selected_risks(candidates)
    return candidates, datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def rank_live_candidates(spot: pd.DataFrame, limit: int = 20) -> dict[str, pd.DataFrame]:
    if spot.empty:
        return {period: pd.DataFrame(columns=LIVE_COLUMNS) for period in PERIODS}

    df = _normalize_spot(spot)
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
    result["公告新闻风险"] = "公告/新闻风险：等待近期公告抓取。"
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
    return f"行业景气：所属行业为 {industry}；当前版本仅识别行业归属，尚未接入行业景气指数。"


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
                "INDUSTRY_NAME": "行业",
            }
        )[["代码", "净利润", "营收", "净利润同比", "行业"]]
    if report_name == "RPT_DMSK_FN_BALANCE":
        result = frame.rename(
            columns={
                "SECURITY_CODE": "代码",
                "TOTAL_ASSETS": "总资产",
                "TOTAL_LIABILITIES": "总负债",
                "DEBT_ASSET_RATIO": "资产负债率",
            }
        )[["代码", "总资产", "总负债", "资产负债率"]]
        missing = pd.to_numeric(result["资产负债率"], errors="coerce").isna()
        result.loc[missing, "资产负债率"] = (
            pd.to_numeric(result.loc[missing, "总负债"], errors="coerce")
            / pd.to_numeric(result.loc[missing, "总资产"], errors="coerce")
            * 100
        )
        return result[["代码", "资产负债率"]]
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
    for column in ["净利润", "营收", "净利润同比", "资产负债率", "经营现金流"]:
        if column not in result.columns:
            result[column] = 0.0
        result[column] = pd.to_numeric(result[column], errors="coerce").fillna(0.0)
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
        result["公告新闻风险"] = result["代码"].astype(str).apply(_announcement_risk_analysis)
        enriched[period] = result
    return enriched


def _announcement_risk_analysis(code: str) -> str:
    try:
        titles = _fetch_recent_announcement_titles(str(code).zfill(6))
    except Exception:
        return "公告/新闻风险：未取得可靠近期公告数据。"
    if not titles:
        return "公告/新闻风险：近期公告标题未见明显风险词。"
    risk_words = ("处罚", "问询", "立案", "诉讼", "仲裁", "减持", "亏损", "退市", "风险", "终止")
    risky = [title for title in titles if any(word in title for word in risk_words)]
    if risky:
        return "公告/新闻风险：近期公告含风险词，需核查：" + "；".join(risky[:2]) + "。"
    return "公告/新闻风险：近期公告标题未见明显风险词。"


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

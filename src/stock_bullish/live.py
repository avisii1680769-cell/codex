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
    "看涨概率",
    "评分",
    "入选理由",
]
CACHE_PATH = Path("outputs/live-web/latest_spot.csv")


def fetch_live_spot() -> pd.DataFrame:
    try:
        spot = _fetch_eastmoney_spot()
    except Exception as exc:
        cached = _read_cached_spot()
        if cached is not None:
            return cached
        raise RuntimeError("实时行情源暂时无响应，请稍后重新扫描。") from exc
    _write_cached_spot(spot)
    return spot


def _fetch_eastmoney_spot() -> pd.DataFrame:
    url = "https://push2.eastmoney.com/api/qt/clist/get"
    session = requests.Session()
    session.trust_env = False
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


def scan_live_candidates(limit: int = 20) -> tuple[dict[str, pd.DataFrame], str]:
    spot = fetch_live_spot()
    candidates = rank_live_candidates(spot, limit=limit)
    return candidates, datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def rank_live_candidates(spot: pd.DataFrame, limit: int = 20) -> dict[str, pd.DataFrame]:
    if spot.empty:
        return {period: pd.DataFrame(columns=LIVE_COLUMNS) for period in PERIODS}

    df = _normalize_spot(spot)
    return {
        "短期": _rank_period(df, "短期", _short_score(df), limit),
        "中期": _rank_period(df, "中期", _mid_score(df), limit),
        "长期": _rank_period(df, "长期", _long_score(df), limit),
    }


def _normalize_spot(spot: pd.DataFrame) -> pd.DataFrame:
    df = spot.copy()
    for column in ["最新价", "涨跌幅", "成交额", "换手率", "量比", "振幅", "市盈率-动态", "市净率", "总市值"]:
        if column not in df.columns:
            df[column] = 0.0
        df[column] = pd.to_numeric(df[column], errors="coerce").fillna(0.0)
    for column in ["代码", "名称"]:
        if column not in df.columns:
            df[column] = ""
        df[column] = df[column].astype(str)
    return df


def _short_score(df: pd.DataFrame) -> pd.Series:
    return (
        _clip_score(df["涨跌幅"], 0, 6) * 0.35
        + _clip_score(df["量比"], 0.8, 2.5) * 0.25
        + _clip_score(df["换手率"], 1, 8) * 0.20
        + _clip_score(df["成交额"], 100_000_000, 2_000_000_000) * 0.15
        + (100 - _clip_score(df["振幅"], 3, 12)) * 0.05
    )


def _mid_score(df: pd.DataFrame) -> pd.Series:
    return (
        _clip_score(df["涨跌幅"], -1, 4) * 0.25
        + _clip_score(df["成交额"], 200_000_000, 3_000_000_000) * 0.25
        + _clip_score(df["换手率"], 0.8, 5) * 0.20
        + _valuation_score(df["市盈率-动态"], 5, 45) * 0.15
        + _valuation_score(df["市净率"], 0.5, 5) * 0.15
    )


def _long_score(df: pd.DataFrame) -> pd.Series:
    return (
        _clip_score(df["成交额"], 100_000_000, 2_000_000_000) * 0.10
        + _clip_score(df["总市值"], 30_000_000_000, 500_000_000_000) * 0.20
        + _valuation_score(df["市盈率-动态"], 5, 30) * 0.35
        + _valuation_score(df["市净率"], 0.5, 3) * 0.25
        + _clip_score(df["涨跌幅"], -2, 3) * 0.10
    )


def _rank_period(df: pd.DataFrame, period: str, score: pd.Series, limit: int) -> pd.DataFrame:
    result = df.copy()
    result["评分"] = score.round(2)
    result["看涨概率"] = (50 + result["评分"] * 0.45).clip(0, 95).round(1)
    result["周期"] = period
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

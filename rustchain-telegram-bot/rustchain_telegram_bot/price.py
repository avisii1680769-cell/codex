from __future__ import annotations

import json
import os
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class PriceResult:
    available: bool
    text: str
    value: float | None = None


def _dot_get(data: Any, path: str) -> Any:
    cur = data
    for part in path.split("."):
        if isinstance(cur, dict):
            cur = cur.get(part)
        else:
            return None
    return cur


def get_wrtc_price() -> PriceResult:
    """Fetch wRTC price from a deployer-configured JSON endpoint.

    Raydium pool APIs change over time, so this bot avoids hard-coding a fragile
    pool URL. Deployers can point WRTC_PRICE_API_URL at Raydium, Jupiter, a
    hosted quote proxy, or their own indexer.
    """

    url = os.environ.get("WRTC_PRICE_API_URL", "").strip()
    if not url:
        return PriceResult(False, "wRTC price provider is not configured. Set WRTC_PRICE_API_URL.")
    path = os.environ.get("WRTC_PRICE_JSON_PATH", "price")
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "rustchain-telegram-bot/1.0"})
        with urllib.request.urlopen(req, timeout=20) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
        value = _dot_get(data, path)
        if value is None:
            return PriceResult(False, f"Price JSON path `{path}` not found.")
        price = float(value)
        return PriceResult(True, f"wRTC price: ${price:.6f}", price)
    except Exception as exc:
        return PriceResult(False, f"wRTC price unavailable: {exc}")

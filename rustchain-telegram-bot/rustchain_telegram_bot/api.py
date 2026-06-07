from __future__ import annotations

import json
import ssl
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class RustChainClient:
    base_url: str = "https://50.28.86.131"
    timeout: int = 20

    def _context(self) -> ssl.SSLContext | None:
        host = urllib.parse.urlparse(self.base_url).hostname
        if host == "50.28.86.131":
            return ssl._create_unverified_context()
        return None

    def get_json(self, path: str) -> dict[str, Any] | list[Any]:
        url = self.base_url.rstrip("/") + path
        req = urllib.request.Request(url, headers={"User-Agent": "rustchain-telegram-bot/1.0"})
        with urllib.request.urlopen(req, timeout=self.timeout, context=self._context()) as resp:
            raw = resp.read().decode("utf-8", errors="replace")
        return json.loads(raw)

    def health(self) -> dict[str, Any]:
        data = self.get_json("/health")
        return data if isinstance(data, dict) else {"status": "unknown", "raw": data}

    def miners(self) -> list[dict[str, Any]]:
        data = self.get_json("/api/miners")
        if isinstance(data, list):
            return [m if isinstance(m, dict) else {"miner_id": str(m)} for m in data]
        if isinstance(data, dict):
            miners = data.get("miners", data.get("active_miners", []))
            if isinstance(miners, list):
                return [m if isinstance(m, dict) else {"miner_id": str(m)} for m in miners]
        return []

    def epoch(self) -> dict[str, Any]:
        data = self.get_json("/epoch")
        return data if isinstance(data, dict) else {"raw": data}

    def balance(self, wallet: str) -> dict[str, Any]:
        path = "/wallet/balance?miner_id=" + urllib.parse.quote(wallet)
        data = self.get_json(path)
        return data if isinstance(data, dict) else {"raw": data}

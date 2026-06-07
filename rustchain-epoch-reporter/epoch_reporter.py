from __future__ import annotations

import argparse
import json
import os
import sqlite3
import ssl
import sys
import time
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any


@dataclass
class Config:
    node_url: str = os.environ.get("RUSTCHAIN_NODE_URL", "https://50.28.86.131")
    explorer_url: str = os.environ.get("RUSTCHAIN_EXPLORER_URL", "https://50.28.86.131/explorer")
    db_path: str = os.environ.get("EPOCH_REPORTER_DB", "epoch_reporter.db")
    discord_webhook_url: str = os.environ.get("DISCORD_WEBHOOK_URL", "")
    moltbook_api_url: str = os.environ.get("MOLTBOOK_API_URL", "")
    moltbook_api_key: str = os.environ.get("MOLTBOOK_API_KEY", "")
    x_dry_run_path: str = os.environ.get("X_DRY_RUN_PATH", "")


def ssl_context_for(url: str) -> ssl.SSLContext | None:
    host = urllib.parse.urlparse(url).hostname
    if host == "50.28.86.131":
        return ssl._create_unverified_context()
    return None


def get_json(url: str, timeout: int = 20) -> Any:
    req = urllib.request.Request(url, headers={"User-Agent": "rustchain-epoch-reporter/1.0"})
    with urllib.request.urlopen(req, timeout=timeout, context=ssl_context_for(url)) as resp:
        return json.loads(resp.read().decode("utf-8", errors="replace"))


def post_json(url: str, payload: dict[str, Any], headers: dict[str, str] | None = None) -> int:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=body, method="POST")
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    with urllib.request.urlopen(req, timeout=20, context=ssl_context_for(url)) as resp:
        return resp.status


def init_db(path: str) -> sqlite3.Connection:
    con = sqlite3.connect(path)
    con.execute("CREATE TABLE IF NOT EXISTS posted_epochs (epoch TEXT PRIMARY KEY, posted_at INTEGER NOT NULL)")
    con.commit()
    return con


def was_posted(con: sqlite3.Connection, epoch: str) -> bool:
    row = con.execute("SELECT 1 FROM posted_epochs WHERE epoch = ?", (epoch,)).fetchone()
    return row is not None


def mark_posted(con: sqlite3.Connection, epoch: str) -> None:
    con.execute("INSERT OR IGNORE INTO posted_epochs(epoch, posted_at) VALUES (?, ?)", (epoch, int(time.time())))
    con.commit()


def normalize_miners(data: Any) -> list[dict[str, Any]]:
    if isinstance(data, list):
        return [m if isinstance(m, dict) else {"miner": str(m)} for m in data]
    if isinstance(data, dict):
        miners = data.get("miners", data.get("active_miners", []))
        if isinstance(miners, list):
            return [m if isinstance(m, dict) else {"miner": str(m)} for m in miners]
    return []


def summarize_miners(miners: list[dict[str, Any]]) -> tuple[int, str, str]:
    families: dict[str, int] = {}
    top = None
    for miner in miners:
        family = str(miner.get("device_family") or miner.get("hardware_type") or miner.get("device_arch") or "unknown")
        families[family] = families.get(family, 0) + 1
        if top is None or float(miner.get("antiquity_multiplier") or 0) > float(top.get("antiquity_multiplier") or 0):
            top = miner
    family_text = ", ".join(f"{count} {name}" for name, count in sorted(families.items(), key=lambda x: (-x[1], x[0]))[:5])
    top_text = "unknown"
    if top:
        top_text = str(top.get("miner") or top.get("miner_id") or top.get("id") or "unknown")
        if top.get("antiquity_multiplier") is not None:
            top_text += f" ({top.get('antiquity_multiplier')}x)"
    return len(miners), family_text or "unknown", top_text


def epoch_id(epoch_data: dict[str, Any]) -> str:
    value = epoch_data.get("epoch", epoch_data.get("current_epoch", epoch_data.get("id")))
    if value is None:
        raise ValueError("Epoch response did not include epoch/current_epoch/id")
    return str(value)


def build_message(epoch_data: dict[str, Any], miners: list[dict[str, Any]], explorer_url: str) -> str:
    epoch = epoch_id(epoch_data)
    miner_count, family_text, top_text = summarize_miners(miners)
    reward = epoch_data.get("total_reward", epoch_data.get("reward", epoch_data.get("distributed_rtc", "unknown")))
    height = epoch_data.get("height", epoch_data.get("block_height", "unknown"))
    total_mined = epoch_data.get("total_mined", epoch_data.get("supply", "unknown"))
    return "\n".join(
        [
            f"Epoch {epoch} Complete",
            "",
            f"RTC distributed: {reward}",
            f"Top miner signal: {top_text}",
            f"Active miners: {miner_count} ({family_text})",
            f"Block height: {height}",
            f"Total RTC mined: {total_mined}",
            "",
            f"Explorer: {explorer_url}",
        ]
    )


def post_outputs(config: Config, message: str, dry_run: bool) -> list[str]:
    results: list[str] = []
    if dry_run:
        results.append("dry-run: skipped external posting")
        if config.x_dry_run_path:
            with open(config.x_dry_run_path, "w", encoding="utf-8") as f:
                f.write(message[:280])
            results.append(f"x-dry-run: wrote {config.x_dry_run_path}")
        return results
    if config.discord_webhook_url:
        status = post_json(config.discord_webhook_url, {"content": message})
        results.append(f"discord: HTTP {status}")
    if config.moltbook_api_url:
        headers = {"Authorization": f"Bearer {config.moltbook_api_key}"} if config.moltbook_api_key else {}
        status = post_json(config.moltbook_api_url, {"content": message}, headers)
        results.append(f"moltbook: HTTP {status}")
    if config.x_dry_run_path:
        with open(config.x_dry_run_path, "w", encoding="utf-8") as f:
            f.write(message[:280])
        results.append(f"x-ready: wrote {config.x_dry_run_path}")
    if not results:
        results.append("no outputs configured")
    return results


def run_once(config: Config, dry_run: bool = False) -> str:
    epoch_data = get_json(config.node_url.rstrip("/") + "/epoch")
    if not isinstance(epoch_data, dict):
        raise ValueError("/epoch did not return a JSON object")
    epoch = epoch_id(epoch_data)
    con = init_db(config.db_path)
    if was_posted(con, epoch):
        return f"Epoch {epoch} already posted"
    miners = normalize_miners(get_json(config.node_url.rstrip("/") + "/api/miners"))
    message = build_message(epoch_data, miners, config.explorer_url)
    results = post_outputs(config, message, dry_run)
    if not dry_run:
        mark_posted(con, epoch)
    return message + "\n\n" + "\n".join(results)


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Post RustChain epoch summaries")
    parser.add_argument("--once", action="store_true", help="Run one poll cycle")
    parser.add_argument("--dry-run", action="store_true", help="Print without posting or marking epoch as posted")
    parser.add_argument("--db", help="Override SQLite state path")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    config = Config()
    if args.db:
        config.db_path = args.db
    if not args.once:
        print("Use --once from cron/systemd timer.", file=sys.stderr)
        return 2
    print(run_once(config, dry_run=args.dry_run))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

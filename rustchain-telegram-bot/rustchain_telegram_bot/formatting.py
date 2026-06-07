from __future__ import annotations

from typing import Any


def fmt_health(data: dict[str, Any]) -> str:
    status = data.get("status", data.get("ok", "unknown"))
    version = data.get("version", data.get("node_version", "unknown"))
    return f"RustChain health: {status}\nVersion: {version}"


def fmt_miners(miners: list[dict[str, Any]]) -> str:
    sample = []
    for miner in miners[:5]:
        sample.append(str(miner.get("miner_id") or miner.get("miner") or miner.get("id") or miner.get("wallet") or miner))
    suffix = "\nSample: " + ", ".join(sample) if sample else ""
    return f"Active miners: {len(miners)}{suffix}"


def fmt_epoch(data: dict[str, Any], explorer_url: str) -> str:
    epoch = data.get("epoch", data.get("current_epoch", data.get("id", "unknown")))
    height = data.get("height", data.get("block_height", "unknown"))
    reward = data.get("total_reward", data.get("reward", data.get("distributed_rtc", "unknown")))
    return f"Epoch: {epoch}\nBlock height: {height}\nReward: {reward} RTC\nExplorer: {explorer_url}"


def fmt_balance(wallet: str, data: dict[str, Any]) -> str:
    balance = data.get("balance", data.get("rtc_balance", data.get("amount", "unknown")))
    return f"Wallet `{wallet}` balance: {balance} RTC"

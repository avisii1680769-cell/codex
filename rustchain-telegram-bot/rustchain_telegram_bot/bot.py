from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass, field

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

from .api import RustChainClient
from .formatting import fmt_balance, fmt_epoch, fmt_health, fmt_miners
from .price import get_wrtc_price


@dataclass
class WatchState:
    last_epoch: str | None = None
    last_miner_count: int | None = None
    last_price: float | None = None
    watched_chats: set[int] = field(default_factory=set)


def client() -> RustChainClient:
    return RustChainClient(os.environ.get("RUSTCHAIN_NODE_URL", "https://50.28.86.131"))


def explorer_url() -> str:
    return os.environ.get("RUSTCHAIN_EXPLORER_URL", "https://50.28.86.131/explorer")


async def reply(update: Update, text: str) -> None:
    if update.effective_message:
        await update.effective_message.reply_text(text, disable_web_page_preview=True)


async def health(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, fmt_health(client().health()))


async def miners(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, fmt_miners(client().miners()))


async def epoch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, fmt_epoch(client().epoch(), explorer_url()))


async def balance(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.args:
        await reply(update, "Usage: /balance <wallet-or-miner-id>")
        return
    wallet = context.args[0]
    await reply(update, fmt_balance(wallet, client().balance(wallet)))


async def price(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await reply(update, get_wrtc_price().text)


async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    state: WatchState = context.application.bot_data.setdefault("watch_state", WatchState())
    state.watched_chats.add(update.effective_chat.id)
    await reply(update, "RustChain alerts enabled for this chat.")


async def unwatch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.effective_chat:
        return
    state: WatchState = context.application.bot_data.setdefault("watch_state", WatchState())
    state.watched_chats.discard(update.effective_chat.id)
    await reply(update, "RustChain alerts disabled for this chat.")


async def alert_tick(context: ContextTypes.DEFAULT_TYPE) -> None:
    state: WatchState = context.application.bot_data.setdefault("watch_state", WatchState())
    if not state.watched_chats:
        return
    c = client()
    messages: list[str] = []
    try:
        epoch_data = c.epoch()
        current_epoch = str(epoch_data.get("epoch", epoch_data.get("current_epoch", "")))
        if current_epoch and state.last_epoch and current_epoch != state.last_epoch:
            messages.append("New RustChain epoch detected:\n" + fmt_epoch(epoch_data, explorer_url()))
        if current_epoch:
            state.last_epoch = current_epoch
    except Exception as exc:
        messages.append(f"Epoch check failed: {exc}")

    try:
        miner_count = len(c.miners())
        if state.last_miner_count is not None and miner_count != state.last_miner_count:
            messages.append(f"Active miner count changed: {state.last_miner_count} -> {miner_count}")
        state.last_miner_count = miner_count
    except Exception as exc:
        messages.append(f"Miner check failed: {exc}")

    price_result = get_wrtc_price()
    threshold = float(os.environ.get("WRTC_PRICE_ALERT_PCT", "5"))
    if price_result.available and price_result.value is not None:
        if state.last_price:
            pct = abs(price_result.value - state.last_price) / state.last_price * 100
            if pct >= threshold:
                messages.append(f"wRTC price moved {pct:.2f}%: ${state.last_price:.6f} -> ${price_result.value:.6f}")
        state.last_price = price_result.value

    for chat_id in list(state.watched_chats):
        for message in messages:
            await context.bot.send_message(chat_id=chat_id, text=message, disable_web_page_preview=True)


def build_application() -> Application:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is required")
    app = Application.builder().token(token).build()
    app.add_handler(CommandHandler("health", health))
    app.add_handler(CommandHandler("miners", miners))
    app.add_handler(CommandHandler("epoch", epoch))
    app.add_handler(CommandHandler("balance", balance))
    app.add_handler(CommandHandler("price", price))
    app.add_handler(CommandHandler("watch", watch))
    app.add_handler(CommandHandler("unwatch", unwatch))
    interval = int(os.environ.get("RUSTCHAIN_ALERT_INTERVAL_SEC", "60"))
    app.job_queue.run_repeating(alert_tick, interval=interval, first=interval)
    return app


def main() -> None:
    app = build_application()
    app.run_polling(close_loop=False)


if __name__ == "__main__":
    main()

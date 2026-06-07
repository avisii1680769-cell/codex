# RustChain Telegram Community Bot

Telegram community bot for RustChain status, miner, epoch, balance, and wRTC price commands.

## Commands

- `/health` - RustChain node health
- `/miners` - active miner count and sample miner IDs
- `/epoch` - current epoch summary
- `/balance <wallet>` - RTC wallet balance
- `/price` - wRTC price lookup with a Raydium/Jupiter-ready provider hook
- `/watch` - start mining and price alert loops in the current chat
- `/unwatch` - stop alert loops for the current chat

## Quick Start

```bash
cd rustchain-telegram-bot
python -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export TELEGRAM_BOT_TOKEN="123456:your-token"
export RUSTCHAIN_NODE_URL="https://50.28.86.131"
python -m rustchain_telegram_bot.bot
```

Windows PowerShell:

```powershell
cd rustchain-telegram-bot
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:TELEGRAM_BOT_TOKEN="123456:your-token"
$env:RUSTCHAIN_NODE_URL="https://50.28.86.131"
python -m rustchain_telegram_bot.bot
```

## Configuration

| Environment variable | Default | Notes |
|---|---:|---|
| `TELEGRAM_BOT_TOKEN` | required | Telegram BotFather token |
| `RUSTCHAIN_NODE_URL` | `https://50.28.86.131` | RustChain API base URL |
| `RUSTCHAIN_EXPLORER_URL` | `https://50.28.86.131/explorer` | Explorer link in messages |
| `RUSTCHAIN_ALERT_INTERVAL_SEC` | `60` | Watch loop interval |
| `WRTC_PRICE_API_URL` | empty | Optional JSON endpoint for wRTC price |
| `WRTC_PRICE_JSON_PATH` | `price` | Dot path inside custom price JSON |
| `WRTC_PRICE_ALERT_PCT` | `5` | Price movement alert threshold |

The bot uses read-only RustChain endpoints. It never sends RTC or stores private keys.

## Deployment

Example systemd service:

```ini
[Unit]
Description=RustChain Telegram Community Bot
After=network-online.target

[Service]
WorkingDirectory=/opt/rustchain-telegram-bot
Environment=TELEGRAM_BOT_TOKEN=replace-me
Environment=RUSTCHAIN_NODE_URL=https://50.28.86.131
ExecStart=/opt/rustchain-telegram-bot/.venv/bin/python -m rustchain_telegram_bot.bot
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

## Local Verification

Run unit tests:

```bash
python -m unittest discover -s tests -v
```

Run a real API smoke check without Telegram:

```bash
python -m rustchain_telegram_bot.smoke
```

Expected smoke output includes node health, epoch summary, and active miner count.

## Notes

`/price` supports a configurable HTTP JSON provider through `WRTC_PRICE_API_URL`. If no provider is configured or the provider fails, the bot returns a clear unavailable message instead of inventing a price. This keeps community output honest while leaving Raydium/Jupiter integration deployer-configurable.

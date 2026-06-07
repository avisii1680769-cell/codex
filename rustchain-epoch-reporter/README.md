# RustChain Epoch Reporter

Cron-friendly Python bot that posts RustChain epoch summaries after epoch changes.

## Features

- Polls the real RustChain `/epoch` endpoint
- Reads active miners from `/api/miners`
- Tracks posted epochs in SQLite so the same epoch is not posted twice
- Posts to Discord webhooks
- Posts to Moltbook-compatible APIs
- Prints an X/Twitter-ready message for schedulers or external tweepy wrappers
- Configurable through environment variables

## Quick Start

```bash
cd rustchain-epoch-reporter
python -m venv .venv
. .venv/bin/activate

export RUSTCHAIN_NODE_URL="https://50.28.86.131"
export DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python -m epoch_reporter --once
```

Windows PowerShell:

```powershell
cd rustchain-epoch-reporter
python -m venv .venv
.\.venv\Scripts\Activate.ps1
$env:RUSTCHAIN_NODE_URL="https://50.28.86.131"
$env:DISCORD_WEBHOOK_URL="https://discord.com/api/webhooks/..."
python -m epoch_reporter --once
```

## Environment

| Variable | Default | Notes |
|---|---:|---|
| `RUSTCHAIN_NODE_URL` | `https://50.28.86.131` | RustChain node API |
| `RUSTCHAIN_EXPLORER_URL` | `https://50.28.86.131/explorer` | Link in posts |
| `EPOCH_REPORTER_DB` | `epoch_reporter.db` | SQLite state file |
| `DISCORD_WEBHOOK_URL` | empty | Enables Discord posting |
| `MOLTBOOK_API_URL` | empty | Enables Moltbook posting |
| `MOLTBOOK_API_KEY` | empty | Bearer token for Moltbook |
| `X_DRY_RUN_PATH` | empty | Writes X-ready text to this file |

## Cron

Run every minute:

```cron
* * * * * cd /opt/rustchain-epoch-reporter && /opt/rustchain-epoch-reporter/.venv/bin/python -m epoch_reporter --once
```

## Systemd Timer

Use a timer if you prefer systemd-managed scheduling:

```ini
[Unit]
Description=RustChain epoch reporter

[Service]
WorkingDirectory=/opt/rustchain-epoch-reporter
Environment=RUSTCHAIN_NODE_URL=https://50.28.86.131
Environment=DISCORD_WEBHOOK_URL=replace-me
ExecStart=/opt/rustchain-epoch-reporter/.venv/bin/python -m epoch_reporter --once
```

## Local Verification

```bash
python -m unittest discover -s tests -v
python -m epoch_reporter --once --dry-run
```

The dry run uses live RustChain read-only endpoints and prints the message without posting.

# RTC Reward Action

Reusable GitHub Action that rewards merged pull requests with RTC.

## Features

- Runs on merged pull requests
- Configurable RTC amount
- Reads contributor wallet from PR body or `.rtc-wallet`
- Supports dry-run mode
- Calls a RustChain node reward endpoint when not in dry-run
- Posts a confirmation comment on the PR
- Does not print admin secrets

## Usage

```yaml
name: RTC reward

on:
  pull_request:
    types: [closed]

permissions:
  contents: read
  pull-requests: write

jobs:
  reward:
    if: github.event.pull_request.merged == true
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: avisii1680769-cell/codex/rtc-reward-action@main
        with:
          node-url: https://50.28.86.131
          amount: 5
          wallet-from: project-fund
          admin-key: ${{ secrets.RTC_ADMIN_KEY }}
          dry-run: "true"
```

## Wallet Discovery

The action searches in this order:

1. PR body lines like `RTC Wallet: wallet-id`, `Wallet: wallet-id`, or `miner_id: wallet-id`
2. `.rtc-wallet` in the repository root

## Inputs

| Input | Required | Default | Description |
|---|---|---:|---|
| `node-url` | yes | | RustChain node base URL |
| `amount` | yes | | RTC amount to award |
| `wallet-from` | yes | | Funding wallet/miner id |
| `admin-key` | no | | Admin key for payment endpoint |
| `dry-run` | no | `true` | When true, no payment request is sent |
| `wallet-file` | no | `.rtc-wallet` | Fallback wallet file path |

## Payment Endpoint

By default the action posts to:

```text
POST <node-url>/wallet/transfer/admin
```

Payload:

```json
{
  "from": "project-fund",
  "to": "contributor-wallet",
  "amount": 5,
  "reason": "GitHub PR merge reward",
  "repository": "owner/repo",
  "pull_request": 123
}
```

If a deployment uses a different endpoint, adapt `src/main.js`.

## Safety

- `dry-run` defaults to `true`
- Missing wallet fails the action with a clear message
- `admin-key` is never logged
- The PR comment says whether payment was dry-run or submitted

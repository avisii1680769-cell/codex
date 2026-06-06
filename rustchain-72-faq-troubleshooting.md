# RustChain FAQ and Troubleshooting Guide

This guide is a practical first stop for miners, node operators, wallet users, and contributors who hit common RustChain setup or runtime problems. It focuses on symptoms, likely causes, and concrete commands to collect evidence before filing an issue.

## Quick Triage Checklist

Before debugging a specific subsystem, capture the basics:

```bash
python --version
pip --version
pip show clawrtc || true
clawrtc --help
```

For node or API problems, also capture:

```bash
curl -s https://50.28.86.131/api/health
curl -s https://50.28.86.131/api/miners | python -m json.tool
```

If a command fails, save the exact command, full output, operating system, CPU architecture, and whether the machine is physical hardware, a VM, WSL, or a container.

## Installation

### `pip install clawrtc` fails

Likely causes:

- Old Python or pip version
- Network or PyPI mirror problem
- Local virtual environment not active
- System Python blocked by OS package manager

Try:

```bash
python -m pip install --upgrade pip
python -m pip install clawrtc
```

If your OS blocks global installs, use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip clawrtc
```

On Windows PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
py -m pip install --upgrade pip clawrtc
```

### `clawrtc` command not found

The package may be installed into a Python environment that is not on your shell path.

Check:

```bash
python -m pip show clawrtc
python -m clawrtc --help
```

If `python -m clawrtc` works but `clawrtc` does not, reactivate the virtual environment or add the environment's script directory to your path.

## Miner Setup

### Dry run works, real mining does not

Dry run checks local configuration and fingerprint collection. Real mining also needs network access, attestation submission, and a node that accepts the request.

Collect:

```bash
clawrtc mine --wallet YOUR_WALLET --dry-run
clawrtc mine --wallet YOUR_WALLET --verbose
curl -s https://50.28.86.131/api/health
```

Likely causes:

- Node endpoint unavailable
- Wallet string rejected by validation
- Hardware fingerprint fails one of the anti-VM checks
- Local clock is far from network time
- Firewall or proxy blocks outbound HTTPS

### Hardware fingerprint is rejected

RustChain rewards hardware identity and antiquity, so the attestation flow is intentionally strict. Rejections are more likely on VMs, ephemeral containers, cloud hosts, or environments that hide CPU and board identifiers.

Useful checks:

```bash
uname -a
python - <<'PY'
import platform
print(platform.platform())
print(platform.machine())
print(platform.processor())
PY
```

If you are on WSL, Docker, a VPS, or a CI runner, try a physical machine. If you believe the rejection is wrong, include the dry-run fingerprint output and a description of the hardware in your issue.

### Mining appears slow

RustChain is not designed as a pure hash-rate race. Older or rarer hardware may receive different scoring treatment than a modern high-throughput CPU. Slow-looking output is not automatically a bug.

Check:

```bash
clawrtc mine --wallet YOUR_WALLET --dry-run
curl -s https://50.28.86.131/api/miners | python -m json.tool
```

Look for whether your miner appears, whether epoch data changes, and whether the node reports healthy status.

## Wallets and Payouts

### Which wallet should I provide?

Use the wallet format requested by the bounty or maintainer. For wRTC on Solana, provide the Solana address that can receive the wrapped RTC token. For native RTC, ask maintainers which native wallet format and tooling they currently expect.

Do not post private keys, seed phrases, browser wallet export files, or recovery words. A payout claim should only include a public receiving address or registered wallet name.

### My token does not appear in the wallet UI

If the wallet supports custom Solana tokens, add the mint address and metadata from the current RustChain/wRTC documentation. Confirm that the mint, decimals, symbol, and network are correct. If the wallet still does not show a balance, check whether the token account exists and whether the transfer has settled.

## API and Node Access

### `/agent/*` endpoint returns 404

Some documentation and bounty issues mention Agent Economy endpoints such as `/agent/jobs` and `/agent/stats`. If the public base URL returns 404, the feature may be deployed on a different node, behind a different host, or temporarily unavailable.

Collect:

```bash
curl -i https://rustchain.org/agent/stats
curl -i https://rustchain.org/agent/jobs
curl -k -i https://50.28.86.131/agent/stats
```

When reporting this, include the full URL, HTTP status, timestamp, and whether TLS verification was required.

### `curl` works with `-k` but not without it

That points to a certificate trust problem. Do not disable TLS verification in production automation unless maintainers explicitly document that endpoint as IP-only or self-signed. For testing, `curl -k` can prove the service is reachable, but production clients should use a hostname with a valid certificate.

### API output is not valid JSON

Use headers to confirm whether the server returned an error page:

```bash
curl -i https://50.28.86.131/api/health
```

If the response is HTML, a proxy, gateway, or error handler may be responding instead of the RustChain API.

## Node Operation

### Node starts then exits immediately

Check the log before changing configuration:

```bash
python rustchainnode/node.py
echo $?
```

Common causes:

- Missing environment variables
- Port already in use
- Database path not writable
- Required dependency not installed
- Invalid genesis or ledger file

On Linux, check ports:

```bash
ss -ltnp | grep -E '5000|8000|8097'
```

On Windows PowerShell:

```powershell
netstat -ano | findstr :5000
```

### Peer or epoch state looks stale

A stale node can be caused by network isolation, failed peer sync, or local state that no longer matches the active chain.

Collect:

```bash
curl -s http://127.0.0.1:5000/api/health
curl -s http://127.0.0.1:5000/api/stats
curl -s https://50.28.86.131/api/health
```

Compare local and public node state. If they differ, include both outputs in your report.

## BoTTube and Bridge Integrations

### Upload API fails

BoTTube upload automation usually needs an API key, a valid media file, and file size below the documented limit. Before debugging the bot, test the platform health and verify the payload independently.

Checklist:

- API key is present in an environment variable, not hard-coded
- Video file exists and is below the size limit
- MIME type matches the file
- Title and description are non-empty
- Upload endpoint is reachable from the machine

### RTC bridge or tipping flow fails

Bridge failures can come from either side: BoTTube event detection or RustChain payout/transfer execution. Keep logs separate:

- BoTTube API polling log
- Reward calculation log
- Transfer signing log
- RustChain API response

Never include signing keys in logs or GitHub issues.

## Contributing and Bounty Claims

### What should a good bug report include?

Include:

- Expected behavior
- Actual behavior
- Exact command or request
- Full output
- OS, Python version, and hardware type
- Whether the environment is physical hardware, VM, WSL, Docker, or cloud
- Screenshots only when text logs are not enough

### What should a good bounty claim include?

Include:

- Issue number
- Deliverable link
- What changed
- How it was verified
- Any limitations or assumptions
- Public payout address or wallet name

Avoid:

- Duplicate claims without new work
- Private keys or seed phrases
- Vague "done" comments with no verification
- Claims for external services that are not publicly verifiable

## Responsible Security Reporting

If you find a vulnerability, do not post exploit details in a public issue unless the repository's security policy says to do so. Prepare:

- Impact summary
- Affected endpoint or file
- Reproduction steps
- Suggested fix
- Whether funds, keys, identity, rewards, or consensus are affected

Then follow the current `SECURITY.md` process.

## Evidence Template

Use this template when asking for help:

```text
Component:
Command or URL:
Expected result:
Actual result:
OS and version:
Python version:
Hardware:
Physical / VM / WSL / Docker / cloud:
Timestamp:
Logs:
What I already tried:
```

The fastest reports to resolve are the ones that let maintainers reproduce the failure without guessing.

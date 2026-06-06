# RIP-302 Agent Economy MCP + CLI

This package is a standalone Model Context Protocol server and terminal client for the RustChain RIP-302 Agent Economy API.

It covers the job lifecycle endpoints described in the RustChain bounty:

- `POST /agent/jobs`
- `GET /agent/jobs`
- `GET /agent/jobs/<id>`
- `POST /agent/jobs/<id>/claim`
- `POST /agent/jobs/<id>/deliver`
- `POST /agent/jobs/<id>/accept`
- `POST /agent/jobs/<id>/dispute`
- `POST /agent/jobs/<id>/cancel`
- `GET /agent/reputation/<wallet>`
- `GET /agent/stats`

The implementation is intentionally useful even when the live endpoint is unavailable: client logic, MCP tool registration, worker ranking, metrics formatting, and CLI behavior are covered by local tests with mocked HTTP responses.

## Install

```bash
npm install
npm run build
```

## Configuration

```bash
export RIP302_BASE_URL=https://50.28.86.131
export RIP302_TIMEOUT_MS=15000
```

On Windows PowerShell:

```powershell
$env:RIP302_BASE_URL = "https://50.28.86.131"
$env:RIP302_TIMEOUT_MS = "15000"
```

## CLI Examples

```bash
rip302-agent jobs
rip302-agent stats
rip302-agent reputation JNCjmuxhJgAUg1WL9rq7tZCRSVT2f1yRhhWdFj9UpsU
```

Post a job:

```bash
rip302-agent post '{
  "poster_wallet": "demo-poster",
  "title": "Write a RustChain mining note",
  "description": "500+ words about the RIP-302 agent economy",
  "category": "writing",
  "reward_rtc": 5,
  "tags": ["writing", "rustchain"]
}'
```

Deliver a job:

```bash
rip302-agent deliver job_123 '{
  "worker_wallet": "demo-worker",
  "deliverable_url": "https://example.com/deliverable",
  "result_summary": "Delivered the requested writing task."
}'
```

## MCP Usage

Add this server to an MCP client:

```json
{
  "mcpServers": {
    "rip302-agent-economy": {
      "command": "node",
      "args": ["dist/mcp.js"],
      "env": {
        "RIP302_BASE_URL": "https://50.28.86.131"
      }
    }
  }
}
```

Available tools:

- `list_jobs`
- `get_job`
- `post_job`
- `claim_job`
- `deliver_job`
- `get_reputation`
- `get_marketplace_stats`
- `format_marketplace_metrics`
- `rank_workers_for_job`

## Worker Ranking

`rank_workers_for_job` is a local helper for the auto-matching tier. It scores workers with:

- Trust score: 40 points
- Category history: 35 points
- Reward fit: 15 points
- Recent completion: 10 points

This does not mutate the RustChain API. It is safe to run offline and can be used as an advisory step before assigning or claiming work.

## Prometheus Metrics Helper

The `metrics` CLI command and `format_marketplace_metrics` MCP tool convert marketplace stats into Prometheus text format:

```text
rip302_jobs_total 7
rip302_jobs_open 2
rip302_rtc_volume_total 42.5
```

## Verification

```bash
npm test
```

The tests verify:

- configured base URL is used for job lifecycle API calls
- HTTP failures return actionable errors
- worker ranking prefers high-trust, category-fit, recent workers
- marketplace stats can be emitted as Prometheus-compatible metrics

## Live Endpoint Note

During local verification on 2026-06-06, `https://rustchain.org/agent/*` returned 404 and `https://50.28.86.131/agent/*` presented a certificate trust issue from PowerShell. This package therefore includes mock-backed tests and clear `RIP302_BASE_URL` configuration so maintainers can run it against the active node endpoint when available.

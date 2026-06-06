import assert from "node:assert/strict";
import { test } from "node:test";
import { Rip302Client, formatMetrics, pickBestWorkers } from "../dist/client.js";

test("client posts, claims, delivers, and accepts a job through configured base URL", async () => {
  const calls = [];
  const fetchImpl = async (url, init = {}) => {
    calls.push({ url: String(url), init });
    if (String(url).endsWith("/agent/jobs") && init.method === "POST") {
      return jsonResponse({ id: "job_123", status: "open" });
    }
    if (String(url).endsWith("/agent/jobs/job_123/claim")) {
      return jsonResponse({ id: "job_123", status: "claimed" });
    }
    if (String(url).endsWith("/agent/jobs/job_123/deliver")) {
      return jsonResponse({ id: "job_123", status: "delivered" });
    }
    if (String(url).endsWith("/agent/jobs/job_123/accept")) {
      return jsonResponse({ id: "job_123", status: "completed" });
    }
    throw new Error(`unexpected ${url}`);
  };

  const client = new Rip302Client({ baseUrl: "https://example.test", fetchImpl });
  assert.equal((await client.postJob({ poster_wallet: "alice", title: "Research", category: "research", reward_rtc: 1 })).status, "open");
  assert.equal((await client.claimJob("job_123", { worker_wallet: "bob" })).status, "claimed");
  assert.equal((await client.deliverJob("job_123", { worker_wallet: "bob", deliverable_url: "https://example.test/d", result_summary: "done" })).status, "delivered");
  assert.equal((await client.acceptJob("job_123", { poster_wallet: "alice", rating: 5 })).status, "completed");
  assert.deepEqual(calls.map((c) => c.init.method), ["POST", "POST", "POST", "POST"]);
});

test("client returns actionable errors for offline or invalid endpoints", async () => {
  const client = new Rip302Client({
    baseUrl: "https://example.test",
    fetchImpl: async () => jsonResponse({ error: "not found" }, 404)
  });

  await assert.rejects(
    () => client.getStats(),
    /RIP-302 API request failed: GET https:\/\/example.test\/agent\/stats returned 404/
  );
});

test("worker matching ranks by trust, category fit, reward history, and recency", () => {
  const workers = pickBestWorkers({
    job: { category: "writing", reward_rtc: 10, created_at: "2026-06-01T00:00:00Z" },
    workers: [
      { wallet: "low", trust_score: 45, categories: { writing: 2 }, avg_reward_rtc: 2, last_completed_at: "2026-01-01T00:00:00Z" },
      { wallet: "best", trust_score: 95, categories: { writing: 8 }, avg_reward_rtc: 9, last_completed_at: "2026-05-30T00:00:00Z" },
      { wallet: "generalist", trust_score: 90, categories: { testing: 10 }, avg_reward_rtc: 30, last_completed_at: "2026-05-29T00:00:00Z" }
    ]
  });

  assert.equal(workers[0].wallet, "best");
  assert.ok(workers[0].score > workers[1].score);
});

test("metrics formatter emits Prometheus-compatible marketplace gauges", () => {
  const text = formatMetrics({
    total_jobs: 7,
    open_jobs: 2,
    completed_jobs: 5,
    total_rtc_volume: 42.5,
    escrow_balance: 3
  });

  assert.match(text, /rip302_jobs_total 7/);
  assert.match(text, /rip302_jobs_open 2/);
  assert.match(text, /rip302_rtc_volume_total 42.5/);
});

function jsonResponse(body, status = 200) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" }
  });
}

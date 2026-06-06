#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { Rip302Client, formatMetrics, pickBestWorkers } from "./client.js";

const server = new McpServer({ name: "rip302-agent-economy-mcp", version: "0.1.0" });
const client = new Rip302Client();

server.tool("list_jobs", "List RIP-302 Agent Economy jobs from the configured RustChain API.", {
  status: z.string().optional(),
  category: z.string().optional()
}, async (input) => safeCall(() => client.getJobs(input)));

server.tool("get_job", "Get one RIP-302 job by id.", {
  job_id: z.string().describe("RIP-302 job id")
}, async ({ job_id }) => safeCall(() => client.getJob(job_id)));

server.tool("post_job", "Post a RIP-302 job. This may lock escrow on live nodes, so use only with an authorized wallet.", {
  poster_wallet: z.string(),
  title: z.string(),
  description: z.string().optional(),
  category: z.string(),
  reward_rtc: z.number().positive(),
  tags: z.array(z.string()).optional()
}, async (input) => safeCall(() => client.postJob(input)));

server.tool("claim_job", "Claim an open RIP-302 job with a worker wallet.", {
  job_id: z.string(),
  worker_wallet: z.string()
}, async ({ job_id, ...payload }) => safeCall(() => client.claimJob(job_id, payload)));

server.tool("deliver_job", "Submit a deliverable URL and summary for a claimed RIP-302 job.", {
  job_id: z.string(),
  worker_wallet: z.string(),
  deliverable_url: z.string().url(),
  result_summary: z.string()
}, async ({ job_id, ...payload }) => safeCall(() => client.deliverJob(job_id, payload)));

server.tool("get_reputation", "Read RIP-302 reputation for a wallet.", {
  wallet: z.string()
}, async ({ wallet }) => safeCall(() => client.getReputation(wallet)));

server.tool("get_marketplace_stats", "Read RIP-302 marketplace statistics.", {}, async () => safeCall(() => client.getStats()));

server.tool("format_marketplace_metrics", "Return Prometheus text metrics from a stats object.", {
  stats: z.record(z.unknown())
}, async ({ stats }) => ({ content: [{ type: "text", text: formatMetrics(stats) }] }));

server.tool("rank_workers_for_job", "Rank candidate workers for a job using trust score, category history, reward fit, and recency.", {
  job: z.object({
    category: z.string().optional(),
    reward_rtc: z.number().optional(),
    created_at: z.string().optional()
  }),
  workers: z.array(z.object({
    wallet: z.string(),
    trust_score: z.number().optional(),
    categories: z.record(z.number()).optional(),
    avg_reward_rtc: z.number().optional(),
    last_completed_at: z.string().optional()
  }))
}, async (input) => ({ content: [{ type: "text", text: JSON.stringify(pickBestWorkers(input), null, 2) }] }));

await server.connect(new StdioServerTransport());

async function safeCall(fn: () => Promise<unknown>) {
  try {
    const result = await fn();
    return { content: [{ type: "text" as const, text: JSON.stringify(result, null, 2) }] };
  } catch (error) {
    return {
      isError: true,
      content: [{ type: "text" as const, text: error instanceof Error ? error.message : String(error) }]
    };
  }
}

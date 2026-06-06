#!/usr/bin/env node
import { readFileSync } from "node:fs";
import { Rip302Client, formatMetrics, pickBestWorkers } from "./client.js";

const [command, ...args] = process.argv.slice(2);
const client = new Rip302Client();

try {
  const result = await run(command, args);
  if (typeof result === "string") {
    process.stdout.write(result.endsWith("\n") ? result : `${result}\n`);
  } else {
    process.stdout.write(`${JSON.stringify(result, null, 2)}\n`);
  }
} catch (error) {
  process.stderr.write(`${error instanceof Error ? error.message : String(error)}\n`);
  process.exitCode = 1;
}

async function run(cmd: string | undefined, args: string[]) {
  switch (cmd) {
    case "jobs":
      return client.getJobs();
    case "job":
      requireArg(args[0], "job id");
      return client.getJob(args[0]);
    case "post":
      return client.postJob(readJsonArg(args[0]));
    case "claim":
      requireArg(args[0], "job id");
      return client.claimJob(args[0], readJsonArg(args[1]));
    case "deliver":
      requireArg(args[0], "job id");
      return client.deliverJob(args[0], readJsonArg(args[1]));
    case "accept":
      requireArg(args[0], "job id");
      return client.acceptJob(args[0], readJsonArg(args[1]));
    case "dispute":
      requireArg(args[0], "job id");
      return client.disputeJob(args[0], readJsonArg(args[1]));
    case "cancel":
      requireArg(args[0], "job id");
      return client.cancelJob(args[0], readJsonArg(args[1]));
    case "reputation":
      requireArg(args[0], "wallet");
      return client.getReputation(args[0]);
    case "stats":
      return client.getStats();
    case "metrics":
      return formatMetrics(await client.getStats() as Record<string, unknown>);
    case "match":
      return pickBestWorkers(readJsonArg(args[0]));
    default:
      return usage();
  }
}

function readJsonArg(value: string | undefined) {
  requireArg(value, "JSON string or @path");
  const raw = value!.startsWith("@") ? readFileSync(value!.slice(1), "utf8") : value!;
  return JSON.parse(raw);
}

function requireArg(value: string | undefined, name: string): asserts value is string {
  if (!value) throw new Error(`Missing ${name}`);
}

function usage() {
  return `Usage:
  rip302-agent jobs
  rip302-agent job <job_id>
  rip302-agent post '<json>' | @payload.json
  rip302-agent claim <job_id> '<json>'
  rip302-agent deliver <job_id> '<json>'
  rip302-agent accept <job_id> '<json>'
  rip302-agent dispute <job_id> '<json>'
  rip302-agent cancel <job_id> '<json>'
  rip302-agent reputation <wallet>
  rip302-agent stats
  rip302-agent metrics
  rip302-agent match '<json>' | @match.json

Environment:
  RIP302_BASE_URL defaults to https://50.28.86.131
  RIP302_TIMEOUT_MS defaults to 15000`;
}

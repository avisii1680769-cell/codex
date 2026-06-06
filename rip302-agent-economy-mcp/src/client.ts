export type FetchLike = (url: string | URL, init?: RequestInit) => Promise<Response>;

export interface Rip302ClientOptions {
  baseUrl?: string;
  fetchImpl?: FetchLike;
  timeoutMs?: number;
}

export interface WorkerProfile {
  wallet: string;
  trust_score?: number;
  categories?: Record<string, number>;
  avg_reward_rtc?: number;
  last_completed_at?: string;
}

export interface MatchInput {
  job: {
    category?: string;
    reward_rtc?: number;
    created_at?: string;
  };
  workers: WorkerProfile[];
}

export interface WorkerMatch extends WorkerProfile {
  score: number;
  score_breakdown: {
    trust: number;
    category: number;
    reward_fit: number;
    recency: number;
  };
}

export class Rip302Client {
  private readonly baseUrl: string;
  private readonly fetchImpl: FetchLike;
  private readonly timeoutMs: number;

  constructor(options: Rip302ClientOptions = {}) {
    this.baseUrl = (options.baseUrl ?? process.env.RIP302_BASE_URL ?? "https://50.28.86.131").replace(/\/+$/, "");
    this.fetchImpl = options.fetchImpl ?? fetch;
    this.timeoutMs = options.timeoutMs ?? Number(process.env.RIP302_TIMEOUT_MS ?? 15000);
  }

  getJobs(params: Record<string, string | number | boolean | undefined> = {}) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined) query.set(key, String(value));
    }
    return this.request(`/agent/jobs${query.size ? `?${query}` : ""}`);
  }

  getJob(jobId: string) {
    return this.request(`/agent/jobs/${encodeURIComponent(jobId)}`);
  }

  postJob(payload: Record<string, unknown>) {
    return this.request("/agent/jobs", { method: "POST", body: payload });
  }

  claimJob(jobId: string, payload: Record<string, unknown>) {
    return this.request(`/agent/jobs/${encodeURIComponent(jobId)}/claim`, { method: "POST", body: payload });
  }

  deliverJob(jobId: string, payload: Record<string, unknown>) {
    return this.request(`/agent/jobs/${encodeURIComponent(jobId)}/deliver`, { method: "POST", body: payload });
  }

  acceptJob(jobId: string, payload: Record<string, unknown>) {
    return this.request(`/agent/jobs/${encodeURIComponent(jobId)}/accept`, { method: "POST", body: payload });
  }

  disputeJob(jobId: string, payload: Record<string, unknown>) {
    return this.request(`/agent/jobs/${encodeURIComponent(jobId)}/dispute`, { method: "POST", body: payload });
  }

  cancelJob(jobId: string, payload: Record<string, unknown>) {
    return this.request(`/agent/jobs/${encodeURIComponent(jobId)}/cancel`, { method: "POST", body: payload });
  }

  getReputation(wallet: string) {
    return this.request(`/agent/reputation/${encodeURIComponent(wallet)}`);
  }

  getStats() {
    return this.request("/agent/stats");
  }

  private async request(path: string, options: { method?: string; body?: unknown } = {}) {
    const method = options.method ?? "GET";
    const url = `${this.baseUrl}${path}`;
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), this.timeoutMs);
    try {
      const response = await this.fetchImpl(url, {
        method,
        signal: controller.signal,
        headers: options.body ? { "Content-Type": "application/json" } : undefined,
        body: options.body ? JSON.stringify(options.body) : undefined
      });
      const text = await response.text();
      const data = text ? parseJson(text) : null;
      if (!response.ok) {
        throw new Error(`RIP-302 API request failed: ${method} ${url} returned ${response.status}; body=${truncate(text)}`);
      }
      return data;
    } catch (error) {
      if (error instanceof Error) {
        throw new Error(`RIP-302 API request failed: ${method} ${url}: ${error.message}`);
      }
      throw error;
    } finally {
      clearTimeout(timer);
    }
  }
}

export function pickBestWorkers(input: MatchInput): WorkerMatch[] {
  const category = input.job.category ?? "";
  const reward = Math.max(Number(input.job.reward_rtc ?? 0), 0);
  const now = input.job.created_at ? Date.parse(input.job.created_at) : Date.now();

  return input.workers.map((worker) => {
    const trust = clamp(Number(worker.trust_score ?? 0), 0, 100) * 0.4;
    const categoryCount = category ? Number(worker.categories?.[category] ?? 0) : 0;
    const categoryScore = Math.min(categoryCount / 10, 1) * 35;
    const avgReward = Math.max(Number(worker.avg_reward_rtc ?? 0), 0);
    const rewardFit = reward <= 0 || avgReward <= 0 ? 5 : Math.max(0, 15 - Math.abs(avgReward - reward));
    const last = worker.last_completed_at ? Date.parse(worker.last_completed_at) : 0;
    const days = last ? Math.max((now - last) / 86400000, 0) : 365;
    const recency = Math.max(0, 10 - Math.min(days / 7, 10));
    const breakdown = { trust, category: categoryScore, reward_fit: rewardFit, recency };
    return {
      ...worker,
      score: Number((trust + categoryScore + rewardFit + recency).toFixed(2)),
      score_breakdown: breakdown
    };
  }).sort((a, b) => b.score - a.score);
}

export function formatMetrics(stats: Record<string, unknown>): string {
  const map: Record<string, string> = {
    total_jobs: "rip302_jobs_total",
    open_jobs: "rip302_jobs_open",
    claimed_jobs: "rip302_jobs_claimed",
    completed_jobs: "rip302_jobs_completed",
    disputed_jobs: "rip302_jobs_disputed",
    total_rtc_volume: "rip302_rtc_volume_total",
    escrow_balance: "rip302_escrow_balance"
  };
  const lines = [];
  for (const [source, metric] of Object.entries(map)) {
    const value = stats[source];
    if (typeof value === "number") lines.push(`# TYPE ${metric} gauge`, `${metric} ${value}`);
  }
  return `${lines.join("\n")}\n`;
}

function parseJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function truncate(text: string, max = 400) {
  return text.length > max ? `${text.slice(0, max)}...` : text;
}

function clamp(value: number, min: number, max: number) {
  return Math.min(Math.max(value, min), max);
}

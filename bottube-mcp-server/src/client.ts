export type FetchLike = (url: string, init?: RequestInit) => Promise<Response>;

export interface BoTTubeClientOptions {
  baseUrl?: string;
  apiKey?: string;
  fetchImpl?: FetchLike;
}

export class BoTTubeClient {
  private readonly baseUrl: string;
  private readonly apiKey?: string;
  private readonly fetchImpl: FetchLike;

  constructor(options: BoTTubeClientOptions = {}) {
    this.baseUrl = (options.baseUrl || process.env.BOTTUBE_BASE_URL || "https://bottube.ai").replace(/\/+$/, "");
    this.apiKey = options.apiKey || process.env.BOTTUBE_API_KEY;
    this.fetchImpl = options.fetchImpl || fetch;
  }

  trending() {
    return this.get("/api/trending");
  }

  search(query: string) {
    return this.get(`/api/search?q=${encodeURIComponent(query).replace(/%20/g, "+")}`);
  }

  video(videoId: string) {
    return this.get(`/api/videos/${encodeURIComponent(videoId)}`);
  }

  videoComments(videoId: string) {
    return this.get(`/api/videos/${encodeURIComponent(videoId)}/comments`);
  }

  agent(agentName: string) {
    return this.get(`/api/agents/${encodeURIComponent(agentName)}`);
  }

  stats() {
    return this.get("/api/stats");
  }

  register(agentName: string, displayName: string) {
    return this.postJson("/api/register", { agent_name: agentName, display_name: displayName }, false);
  }

  comment(videoId: string, content: string) {
    return this.postJson(`/api/videos/${encodeURIComponent(videoId)}/comment`, { content }, true);
  }

  vote(videoId: string, vote: 1 | -1) {
    return this.postJson(`/api/videos/${encodeURIComponent(videoId)}/vote`, { vote }, true);
  }

  upload(input: { filePath?: string; title: string; description?: string; tags?: string[] }) {
    if (!input.filePath) {
      throw new Error("bottube_upload requires filePath. Remote file transfer is not supported by this stdio server.");
    }
    this.requireApiKey();
    throw new Error("bottube_upload is scaffolded for authenticated use; run from a host process that can provide file streams.");
  }

  private async get(path: string) {
    const response = await this.fetchImpl(`${this.baseUrl}${path}`);
    return this.parseResponse(response);
  }

  private async postJson(path: string, body: unknown, authenticated: boolean) {
    const headers: Record<string, string> = { "Content-Type": "application/json" };
    if (authenticated) headers["X-API-Key"] = this.requireApiKey();
    const response = await this.fetchImpl(`${this.baseUrl}${path}`, {
      method: "POST",
      headers,
      body: JSON.stringify(body),
    });
    return this.parseResponse(response);
  }

  private requireApiKey() {
    if (!this.apiKey) throw new Error("BOTTUBE_API_KEY is required for this write tool");
    return this.apiKey;
  }

  private async parseResponse(response: Response) {
    const text = await response.text();
    const data = text ? tryJson(text) : {};
    if (!response.ok) {
      throw new Error(`BoTTube API error HTTP ${response.status}: ${typeof data === "string" ? data : JSON.stringify(data)}`);
    }
    return data;
  }
}

function tryJson(text: string) {
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

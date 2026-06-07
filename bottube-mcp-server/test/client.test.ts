import { describe, expect, it, vi } from "vitest";
import { BoTTubeClient } from "../src/client.js";

describe("BoTTubeClient", () => {
  it("normalizes base URLs and calls trending", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toBe("https://bottube.ai/api/trending");
      return new Response(JSON.stringify({ videos: [] }), { status: 200 });
    });
    const client = new BoTTubeClient({ baseUrl: "https://bottube.ai///", fetchImpl: fetchMock });
    await expect(client.trending()).resolves.toEqual({ videos: [] });
  });

  it("encodes search queries", async () => {
    const fetchMock = vi.fn(async (url: string) => {
      expect(url).toBe("https://bottube.ai/api/search?q=retro+computing");
      return new Response(JSON.stringify({ results: [] }), { status: 200 });
    });
    const client = new BoTTubeClient({ fetchImpl: fetchMock });
    await client.search("retro computing");
  });

  it("requires an API key for authenticated writes", async () => {
    const client = new BoTTubeClient({ fetchImpl: vi.fn() });
    await expect(client.comment("video-1", "Nice")).rejects.toThrow(/BOTTUBE_API_KEY/);
  });

  it("sends authenticated JSON comments", async () => {
    const fetchMock = vi.fn(async (_url: string, init?: RequestInit) => {
      expect(init?.method).toBe("POST");
      expect((init?.headers as Record<string, string>)["X-API-Key"]).toBe("secret");
      expect(JSON.parse(String(init?.body))).toEqual({ content: "Useful video" });
      return new Response(JSON.stringify({ ok: true }), { status: 200 });
    });
    const client = new BoTTubeClient({ apiKey: "secret", fetchImpl: fetchMock });
    await expect(client.comment("abc", "Useful video")).resolves.toEqual({ ok: true });
  });
});

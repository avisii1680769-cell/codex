import { z } from "zod";
import { BoTTubeClient } from "./client.js";

type ToolDefinition = {
  name: string;
  description: string;
  schema: Record<string, z.ZodTypeAny>;
  handler: (args: Record<string, unknown>) => Promise<unknown> | unknown;
};

export function formatResult(data: unknown) {
  return {
    content: [{ type: "text" as const, text: typeof data === "string" ? data : JSON.stringify(data, null, 2) }],
  };
}

export function formatError(error: unknown) {
  const message = error instanceof Error ? error.message : String(error);
  return { content: [{ type: "text" as const, text: message }], isError: true };
}

export function toolDefinitions(client = new BoTTubeClient()): ToolDefinition[] {
  return [
    {
      name: "bottube_trending",
      description: "Get BoTTube trending videos. Read-only and does not require an API key.",
      schema: {},
      handler: async () => client.trending(),
    },
    {
      name: "bottube_search",
      description: "Search BoTTube videos by query. Returns matching video records from the public API.",
      schema: { query: z.string().min(1).describe("Search query, for example retro computing") },
      handler: async (args) => client.search(String(args.query)),
    },
    {
      name: "bottube_video",
      description: "Get a BoTTube video detail record and its comments.",
      schema: { video_id: z.string().min(1).describe("BoTTube video ID") },
      handler: async (args) => {
        const video_id = String(args.video_id);
        const [video, comments] = await Promise.all([client.video(video_id), client.videoComments(video_id)]);
        return { video, comments };
      },
    },
    {
      name: "bottube_agent",
      description: "Get a BoTTube agent profile and videos by agent name.",
      schema: { agent_name: z.string().min(1).describe("BoTTube agent name") },
      handler: async (args) => client.agent(String(args.agent_name)),
    },
    {
      name: "bottube_stats",
      description: "Get BoTTube public platform statistics.",
      schema: {},
      handler: async () => client.stats(),
    },
    {
      name: "bottube_register",
      description: "Register a BoTTube agent profile. Public endpoint; no API key required by current API docs.",
      schema: {
        agent_name: z.string().min(1).describe("Unique agent handle"),
        display_name: z.string().min(1).describe("Human-readable display name"),
      },
      handler: async (args) => client.register(String(args.agent_name), String(args.display_name)),
    },
    {
      name: "bottube_comment",
      description: "Post a comment on a BoTTube video. Requires BOTTUBE_API_KEY.",
      schema: {
        video_id: z.string().min(1).describe("BoTTube video ID"),
        content: z.string().min(1).max(4000).describe("Comment text"),
      },
      handler: async (args) => client.comment(String(args.video_id), String(args.content)),
    },
    {
      name: "bottube_vote",
      description: "Upvote or downvote a BoTTube video. Requires BOTTUBE_API_KEY.",
      schema: {
        video_id: z.string().min(1).describe("BoTTube video ID"),
        vote: z.union([z.literal(1), z.literal(-1)]).describe("1 for upvote, -1 for downvote"),
      },
      handler: async (args) => client.vote(String(args.video_id), args.vote === -1 ? -1 : 1),
    },
    {
      name: "bottube_upload",
      description: "Prepare an authenticated BoTTube upload from a local file path. Requires BOTTUBE_API_KEY.",
      schema: {
        filePath: z.string().min(1).describe("Local video file path on the MCP host"),
        title: z.string().min(1).describe("Video title"),
        description: z.string().default("").describe("Video description"),
        tags: z.array(z.string()).default([]).describe("Video tags"),
      },
      handler: async (args) => client.upload({
        filePath: String(args.filePath),
        title: String(args.title),
        description: String(args.description || ""),
        tags: Array.isArray(args.tags) ? args.tags.map(String) : [],
      }),
    },
  ];
}

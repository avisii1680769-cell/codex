#!/usr/bin/env node
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { fileURLToPath } from "node:url";
import { formatError, formatResult, toolDefinitions } from "./tools.js";

export function createServer() {
  const server = new McpServer({ name: "bottube-mcp-server", version: "0.1.0" });
  for (const tool of toolDefinitions()) {
    server.tool(tool.name, tool.description, tool.schema, async (args) => {
      try {
        const result = await tool.handler(args as never);
        return formatResult(result);
      } catch (error) {
        return formatError(error);
      }
    });
  }
  return server;
}

if (process.argv[1] && fileURLToPath(import.meta.url) === process.argv[1]) {
  const server = createServer();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const transport = new StdioClientTransport({
  command: process.execPath,
  args: ["dist/index.js"],
  stderr: "pipe",
});

const client = new Client({ name: "bottube-mcp-smoke", version: "0.1.0" });
await client.connect(transport);

const result = await client.listTools();
const names = result.tools.map((tool) => tool.name).sort();
for (const required of ["bottube_trending", "bottube_search", "bottube_upload", "bottube_vote"]) {
  if (!names.includes(required)) throw new Error(`Missing tool ${required}`);
}

console.log(`stdio smoke ok: ${names.length} tools`);
await client.close();

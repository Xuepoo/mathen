import { describe, expect, test } from "bun:test";
import { handleMcpRequest, mcpAuthorized } from "./mcp.js";

const backend = {
  listSystems: async () => [{ id: "git" }],
  getSystem: async (id: string) => ({ id }),
  searchFeatures: async (query: string) => [{ query }],
  listFeatureRelations: async () => [],
  listCompositions: async () => [],
  getModelingBundle: async (id: string) => ({ id }),
};

describe("hosted MCP boundary", () => {
  test("requires an exact bearer token", () => {
    expect(
      mcpAuthorized(new Request("https://example.test/mcp"), "secret"),
    ).toBe(false);
    expect(
      mcpAuthorized(
        new Request("https://example.test/mcp", {
          headers: { Authorization: "Bearer secret" },
        }),
        "secret",
      ),
    ).toBe(true);
  });

  test("serves initialize and tools/list as JSON-RPC", async () => {
    const initialize = await handleMcpRequest(
      new Request("https://example.test/mcp", {
        method: "POST",
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "initialize" }),
      }),
      backend,
    );
    expect(initialize.status).toBe(200);
    const initialized = (await initialize.json()) as {
      result: { serverInfo: { name: string } };
    };
    expect(initialized.result.serverInfo.name).toBe("mathen-hosted");

    const tools = await handleMcpRequest(
      new Request("https://example.test/mcp", {
        method: "POST",
        body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }),
      }),
      backend,
    );
    const listed = (await tools.json()) as { result: { tools: unknown[] } };
    expect(listed.result.tools).toHaveLength(6);
  });

  test("calls reviewed tools without draft arguments", async () => {
    const response = await handleMcpRequest(
      new Request("https://example.test/mcp", {
        method: "POST",
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 3,
          method: "tools/call",
          params: { name: "get_system", arguments: { system_id: "git" } },
        }),
      }),
      backend,
    );
    const result = (await response.json()) as {
      result: { content: Array<{ text: string }> };
    };
    expect(JSON.parse(result.result.content[0]!.text)).toEqual({ id: "git" });
  });
});

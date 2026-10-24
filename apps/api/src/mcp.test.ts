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

function jsonRequest(body: unknown) {
  return new Request("https://example.test/api/mcp", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

describe("hosted MCP boundary", () => {
  test("requires an exact bearer token", () => {
    expect(mcpAuthorized(new Request("https://example.test/mcp"), "secret")).toBe(false);
    expect(
      mcpAuthorized(
        new Request("https://example.test/mcp", {
          headers: { Authorization: "Bearer secret" },
        }),
        "secret",
      ),
    ).toBe(true);
    expect(
      mcpAuthorized(
        new Request("https://example.test/mcp", {
          headers: { Authorization: "Bearer secret " },
        }),
        "secret",
      ),
    ).toBe(true);
  });

  test("serves initialize and tools/list as JSON-RPC", async () => {
    const initialize = await handleMcpRequest(
      jsonRequest({ jsonrpc: "2.0", id: 1, method: "initialize" }),
      backend,
    );
    expect(initialize.status).toBe(200);
    const initialized = (await initialize.json()) as {
      result: { serverInfo: { name: string } };
    };
    expect(initialized.result.serverInfo.name).toBe("mathen-hosted");

    const tools = await handleMcpRequest(
      jsonRequest({ jsonrpc: "2.0", id: 2, method: "tools/list" }),
      backend,
    );
    const listed = (await tools.json()) as { result: { tools: unknown[] } };
    expect(listed.result.tools).toHaveLength(6);
  });

  test("calls reviewed tools without draft arguments", async () => {
    const response = await handleMcpRequest(
      jsonRequest({
        jsonrpc: "2.0",
        id: 3,
        method: "tools/call",
        params: { name: "get_system", arguments: { system_id: "git" } },
      }),
      backend,
    );
    const result = (await response.json()) as {
      result: { content: Array<{ text: string }> };
    };
    expect(JSON.parse(result.result.content[0]!.text)).toEqual({ id: "git" });
  });

  test("rejects non-JSON requests and invalid JSON-RPC ids", async () => {
    const contentType = await handleMcpRequest(
      new Request("https://example.test/api/mcp", {
        method: "POST",
        body: "{}",
      }),
      backend,
    );
    expect(contentType.status).toBe(400);
    expect((await contentType.json()) as { error: { code: number } }).toMatchObject({
      error: { code: -32700 },
    });

    const invalidId = await handleMcpRequest(
      jsonRequest({ jsonrpc: "2.0", id: {}, method: "tools/list" }),
      backend,
    );
    expect((await invalidId.json()) as { error: { code: number } }).toMatchObject({
      error: { code: -32600 },
    });

    const notification = await handleMcpRequest(
      jsonRequest({ jsonrpc: "2.0", method: "tools/list" }),
      backend,
    );
    expect(notification.status).toBe(202);
    expect(await notification.text()).toBe("");
  });

  test("accepts initialized notifications without producing a result", async () => {
    const response = await handleMcpRequest(
      jsonRequest({ jsonrpc: "2.0", method: "notifications/initialized" }),
      backend,
    );
    expect(response.status).toBe(202);
    expect(await response.text()).toBe("");
  });

  test("rejects notification ids", async () => {
    const response = await handleMcpRequest(
      jsonRequest({
        jsonrpc: "2.0",
        id: 1,
        method: "notifications/initialized",
      }),
      backend,
    );
    expect((await response.json()) as { error: { code: number } }).toMatchObject({
      error: { code: -32600 },
    });
  });
});

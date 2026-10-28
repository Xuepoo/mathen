import { describe, expect, test } from "bun:test";
import {
  handleMcpRequest,
  mcpAuthorized,
  mcpCorsHeaders,
  mcpForwardedAuthorization,
  mcpOAuthChallenge,
  mcpOriginAllowed,
  mcpProtectedResourceMetadata,
} from "./mcp.js";

const backend = {
  listSystems: async () => [{ id: "git" }],
  getSystem: async (id: string) => ({ id }),
  searchFeatures: async (query: string) => [{ query }],
  listFeatureRelations: async () => [],
  listCompositions: async () => [],
  getModelingBundle: async (id: string) => ({ id }),
  getLayeredGraph: async () => ({ nodes: [], edges: [] }),
  searchRetrieval: async (path: string) => ({ path }),
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

  test("forwards the authenticated header without replacing it with the legacy token", () => {
    const oauthRequest = new Request("https://example.test/api/mcp", {
      headers: { Authorization: "Bearer auth0-access-token" },
    });
    expect(mcpForwardedAuthorization(oauthRequest, "legacy-service-token")).toBe(
      "Bearer auth0-access-token",
    );
    expect(
      mcpForwardedAuthorization(
        new Request("https://example.test/api/mcp"),
        "legacy-service-token",
      ),
    ).toBe("Bearer legacy-service-token");
    expect(mcpForwardedAuthorization(new Request("https://example.test/api/mcp"))).toBe("");
  });

  test("allows only configured browser origins and emits CORS headers", () => {
    const allowed = new Request("https://example.test/api/mcp", {
      headers: { Origin: "https://client.example" },
    });
    const denied = new Request("https://example.test/api/mcp", {
      headers: { Origin: "https://other.example" },
    });
    expect(mcpOriginAllowed(allowed, "https://client.example")).toBe(true);
    expect(mcpOriginAllowed(denied, "https://client.example")).toBe(false);
    expect(
      mcpCorsHeaders(allowed, "https://client.example").get("Access-Control-Allow-Origin"),
    ).toBe("https://client.example");
  });

  test("advertises protected-resource metadata in OAuth challenges", () => {
    const request = new Request("https://example.test/api/mcp");
    expect(mcpOAuthChallenge(request, true, "read:cards")).toBe(
      'Bearer realm="mathen-mcp", resource_metadata="https://example.test/api/.well-known/oauth-protected-resource", error="invalid_token", scope="read:cards"',
    );
    expect(
      mcpProtectedResourceMetadata(request, "https://tenant.example.test/", ["read:cards"]),
    ).toEqual({
      resource: "https://example.test/api/mcp",
      bearer_methods_supported: ["header"],
      authorization_servers: ["https://tenant.example.test/"],
      scopes_supported: ["read:cards"],
    });
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
    expect(listed.result.tools).toHaveLength(8);
    expect(
      (listed.result.tools as Array<{ name: string }>).some(
        (tool) => tool.name === "get_layered_graph",
      ),
    ).toBe(true);
  });

  test("calls the reviewed layered graph projection with an origin", async () => {
    const response = await handleMcpRequest(
      jsonRequest({
        jsonrpc: "2.0",
        id: 4,
        method: "tools/call",
        params: {
          name: "get_layered_graph",
          arguments: { origin: "local-analysis" },
        },
      }),
      backend,
    );
    expect(response.status).toBe(200);
    const result = (await response.json()) as {
      result: { content: Array<{ text: string }> };
    };
    expect(JSON.parse(result.result.content[0]!.text)).toEqual({
      nodes: [],
      edges: [],
    });
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

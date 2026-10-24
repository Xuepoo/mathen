/** Minimal stateless Streamable HTTP MCP handler for the reviewed read boundary. */

type McpBackend = {
  listSystems(): Promise<unknown>;
  getSystem(systemId: string): Promise<unknown>;
  searchFeatures(
    query: string,
    category?: string,
    claimType?: string,
    limit?: number,
  ): Promise<unknown>;
  listFeatureRelations(
    systemId?: string,
    featureId?: string,
    targetSystemId?: string,
    type?: string,
    limit?: number,
  ): Promise<unknown>;
  listCompositions(inputSystem?: string, claimStatus?: string, limit?: number): Promise<unknown>;
  getModelingBundle(systemId: string): Promise<unknown>;
};

type JsonRpcRequest = {
  jsonrpc?: unknown;
  id?: unknown;
  method?: unknown;
  params?: unknown;
};

export function mcpAuthorized(request: Request, token?: string): boolean {
  const expected = token?.trim();
  return Boolean(expected && request.headers.get("Authorization")?.trim() === `Bearer ${expected}`);
}

export async function handleMcpRequest(request: Request, backend: McpBackend): Promise<Response> {
  if (request.method !== "POST") {
    return new Response(null, { status: 405, headers: { Allow: "POST" } });
  }
  const contentType = request.headers.get("Content-Type")?.split(";", 1)[0]?.trim().toLowerCase();
  if (contentType !== "application/json") {
    return jsonRpcError(null, -32700, "Content-Type must be application/json");
  }
  let body: unknown;
  try {
    body = await request.json();
  } catch {
    return jsonRpcError(null, -32700, "Invalid JSON");
  }
  if (!isRecord(body)) return jsonRpcError(null, -32600, "Invalid Request");
  const message = body as JsonRpcRequest;
  const id = isValidId(message.id) ? message.id : null;
  if (
    message.jsonrpc !== "2.0" ||
    typeof message.method !== "string" ||
    (hasId(message) && !isValidId(message.id))
  ) {
    return jsonRpcError(id, -32600, "Invalid Request");
  }
  if (message.method === "notifications/initialized" && !hasId(message))
    return new Response(null, { status: 202 });
  if (message.method.startsWith("notifications/")) {
    if (hasId(message)) {
      return jsonRpcError(id, -32600, "Notifications must not include an id");
    }
    return new Response(null, { status: 202 });
  }
  if (!hasId(message)) return new Response(null, { status: 202 });
  try {
    switch (message.method) {
      case "initialize":
        return jsonRpcResult(id, {
          protocolVersion: "2025-06-18",
          capabilities: { tools: {} },
          serverInfo: { name: "mathen-hosted", version: "0.0.1" },
        });
      case "tools/list":
        return jsonRpcResult(id, { tools: toolDefinitions() });
      case "tools/call":
        return jsonRpcResult(id, await callTool(message.params, backend));
      default:
        return jsonRpcError(id, -32601, `Method not found: ${message.method}`);
    }
  } catch (error) {
    return jsonRpcResult(id, {
      content: [
        {
          type: "text",
          text: JSON.stringify({
            error: error instanceof Error ? error.message : "MCP tool failed",
          }),
        },
      ],
      isError: true,
    });
  }
}

export function createMcpApiBackend(request: (path: string) => Promise<unknown>): McpBackend {
  return {
    listSystems: () => request("/systems"),
    getSystem: (systemId) => request(`/systems/${encodeURIComponent(systemId)}`),
    searchFeatures: (query, category, claimType, limit) => {
      const params = new URLSearchParams({ query, limit: String(limit ?? 20) });
      if (category) params.set("category", category);
      if (claimType) params.set("claim_type", claimType);
      return request(`/features?${params}`);
    },
    listFeatureRelations: (systemId, featureId, targetSystemId, type, limit) => {
      const params = new URLSearchParams({ limit: String(limit ?? 20) });
      if (systemId) params.set("system_id", systemId);
      if (featureId) params.set("feature_id", featureId);
      if (targetSystemId) params.set("target_system_id", targetSystemId);
      if (type) params.set("type", type);
      return request(`/feature-relations?${params}`);
    },
    listCompositions: (inputSystem, claimStatus, limit) => {
      const params = new URLSearchParams({ limit: String(limit ?? 20) });
      if (inputSystem) params.set("input_system", inputSystem);
      if (claimStatus) params.set("claim_status", claimStatus);
      return request(`/compositions?${params}`);
    },
    getModelingBundle: (systemId) => request(`/modeling/${encodeURIComponent(systemId)}`),
  };
}

async function callTool(params: unknown, backend: McpBackend) {
  const record = isRecord(params) ? params : {};
  const name = record.name;
  const args = isRecord(record.arguments) ? record.arguments : {};
  if (typeof name !== "string") throw new Error("tools/call requires a tool name");
  let value: unknown;
  switch (name) {
    case "list_systems":
      value = await backend.listSystems();
      break;
    case "get_system":
      value = await backend.getSystem(requiredString(args.system_id, "system_id"));
      break;
    case "search_features":
      value = await backend.searchFeatures(
        requiredString(args.query, "query"),
        optionalString(args.category),
        optionalString(args.claim_type),
        optionalLimit(args.limit),
      );
      break;
    case "list_feature_relations":
      value = await backend.listFeatureRelations(
        optionalString(args.system_id),
        optionalString(args.feature_id),
        optionalString(args.target_system_id),
        optionalString(args.type),
        optionalLimit(args.limit),
      );
      break;
    case "list_compositions":
      value = await backend.listCompositions(
        optionalString(args.input_system),
        optionalString(args.claim_status),
        optionalLimit(args.limit),
      );
      break;
    case "get_modeling_bundle":
      value = await backend.getModelingBundle(requiredString(args.system_id, "system_id"));
      break;
    default:
      throw new Error(`Unknown tool: ${name}`);
  }
  return { content: [{ type: "text", text: JSON.stringify(value, null, 2) }] };
}

function toolDefinitions() {
  type ToolDefinitionInput = [
    name: string,
    description: string,
    properties: Record<string, unknown>,
    required?: string[],
  ];
  const definitions: ToolDefinitionInput[] = [
    ["list_systems", "List reviewed Mathen architecture cards.", {}],
    [
      "get_system",
      "Get one reviewed architecture card.",
      { system_id: { type: "string" } },
      ["system_id"],
    ],
    [
      "search_features",
      "Search reviewed reusable architecture features.",
      {
        query: { type: "string" },
        category: { type: "string" },
        claim_type: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 50 },
      },
      ["query"],
    ],
    [
      "list_feature_relations",
      "List reviewed evidence-backed feature relations.",
      {
        system_id: { type: "string" },
        feature_id: { type: "string" },
        target_system_id: { type: "string" },
        type: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 50 },
      },
      [],
    ],
    [
      "list_compositions",
      "List reviewed composition proposals.",
      {
        input_system: { type: "string" },
        claim_status: { type: "string" },
        limit: { type: "integer", minimum: 1, maximum: 50 },
      },
      [],
    ],
    [
      "get_modeling_bundle",
      "Get one fixed-commit modeling bundle.",
      { system_id: { type: "string" } },
      ["system_id"],
    ],
  ];
  return definitions.map(([name, description, properties, required]) => ({
    name,
    description,
    inputSchema: {
      type: "object",
      properties,
      additionalProperties: false,
      ...(required?.length ? { required } : {}),
    },
  }));
}

function jsonRpcResult(id: unknown, result: unknown) {
  return Response.json(
    { jsonrpc: "2.0", id, result },
    { headers: { "Mcp-Protocol-Version": "2025-06-18" } },
  );
}

function jsonRpcError(id: unknown, code: number, message: string) {
  return Response.json(
    { jsonrpc: "2.0", id, error: { code, message } },
    { status: 400, headers: { "Mcp-Protocol-Version": "2025-06-18" } },
  );
}

function hasId(message: JsonRpcRequest): boolean {
  return Object.hasOwn(message, "id");
}

function isValidId(value: unknown): value is string | number | null {
  return (
    value === null ||
    typeof value === "string" ||
    (typeof value === "number" && Number.isFinite(value))
  );
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null && !Array.isArray(value);
}

function requiredString(value: unknown, name: string): string {
  if (typeof value !== "string" || !value.trim()) throw new Error(`${name} is required`);
  return value;
}

function optionalString(value: unknown): string | undefined {
  return typeof value === "string" && value.trim() ? value : undefined;
}

function optionalLimit(value: unknown): number | undefined {
  return typeof value === "number" && Number.isInteger(value) && value > 0
    ? Math.min(value, 50)
    : undefined;
}

import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";
import { BackendError, createBackend } from "./backend.js";

const repositoryRoot = resolveRepositoryRoot();
const backend = createBackend(repositoryRoot);

function jsonResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

function errorResult(error: unknown) {
  return jsonResult({
    error: error instanceof BackendError ? error.message : "backend request failed",
  });
}

const server = new McpServer({ name: "mathen", version: "0.0.2" });

server.registerTool(
  "get_layered_graph",
  {
    description:
      "Get the deterministic read-only projection of reviewed graph layers. Drafts and navigation categories are excluded.",
    inputSchema: { origin: z.string().min(1).optional() },
  },
  async ({ origin }) => {
    try {
      return jsonResult(await backend.getLayeredGraph(origin));
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "list_systems",
  {
    description: "List reviewed Mathen architecture cards.",
    inputSchema: {},
  },
  async () => {
    try {
      return jsonResult(await backend.listSystems(false));
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "get_system",
  {
    description: "Get one reviewed architecture card by ID.",
    inputSchema: { system_id: z.string().regex(/^[a-z0-9-]+$/) },
  },
  async ({ system_id }) => {
    try {
      const card = await backend.getSystem(system_id, false);
      return jsonResult(card ?? { error: `system not found: ${system_id}` });
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "search_features",
  {
    description: "Search reusable architecture features across reviewed cards.",
    inputSchema: {
      query: z.string().min(1),
      category: z.string().optional(),
      claim_type: z.string().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ query, category, claim_type, limit }) => {
    try {
      return jsonResult(
        await backend.searchFeatures(query, category, claim_type, false, limit ?? 20),
      );
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "list_feature_relations",
  {
    description: "List evidence-backed feature relations from reviewed cards.",
    inputSchema: {
      system_id: z
        .string()
        .regex(/^[a-z0-9-]+$/)
        .optional(),
      feature_id: z
        .string()
        .regex(/^[a-z0-9-]+$/)
        .optional(),
      target_system_id: z
        .string()
        .regex(/^[a-z0-9-]+$/)
        .optional(),
      type: z
        .enum([
          "implements",
          "refines",
          "requires",
          "supports",
          "conflicts-with",
          "composes",
          "resembles",
        ])
        .optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ system_id, feature_id, target_system_id, type, limit }) => {
    try {
      return jsonResult({
        data: await backend.listFeatureRelations(
          system_id,
          feature_id,
          target_system_id,
          type,
          false,
          limit ?? 20,
        ),
      });
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "list_compositions",
  {
    description:
      "List reviewed composition proposals, optionally filtered by input system or claim status.",
    inputSchema: {
      input_system: z
        .string()
        .regex(/^[a-z0-9-]+$/)
        .optional(),
      claim_status: z
        .enum(["proposed", "under-review", "accepted", "rejected", "deprecated"])
        .optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ input_system, claim_status, limit }) => {
    try {
      return jsonResult(
        await backend.listCompositions(input_system, claim_status, false, limit ?? 20),
      );
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "get_modeling_bundle",
  {
    description: "Get a fixed-commit evidence bundle for LLM-assisted modeling.",
    inputSchema: { system_id: z.string().regex(/^[a-z0-9-]+$/) },
  },
  async ({ system_id }) => {
    try {
      return jsonResult(await backend.getModelingBundle(system_id));
    } catch (error) {
      return errorResult(error);
    }
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);

function resolveRepositoryRoot(): string {
  return process.env.MATHEN_ROOT ?? fileURLToPath(new URL("../../..", import.meta.url));
}

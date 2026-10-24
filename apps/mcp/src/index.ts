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

const server = new McpServer({ name: "mathen", version: "0.1.0" });

server.registerTool(
  "list_systems",
  {
    description: "List reviewed Mathen architecture cards, optionally including drafts.",
    inputSchema: { include_drafts: z.boolean().optional() },
  },
  async ({ include_drafts }) => {
    try {
      return jsonResult(await backend.listSystems(include_drafts ?? false));
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "get_system",
  {
    description: "Get one reviewed or draft architecture card by ID.",
    inputSchema: {
      system_id: z.string().regex(/^[a-z0-9-]+$/),
      include_drafts: z.boolean().optional(),
    },
  },
  async ({ system_id, include_drafts }) => {
    try {
      const card = await backend.getSystem(system_id, include_drafts ?? false);
      return jsonResult(card ?? { error: `system not found: ${system_id}` });
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "search_features",
  {
    description: "Search reusable architecture features across reviewed cards and optional drafts.",
    inputSchema: {
      query: z.string().min(1),
      category: z.string().optional(),
      claim_type: z.string().optional(),
      include_drafts: z.boolean().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ query, category, claim_type, include_drafts, limit }) => {
    try {
      return jsonResult(
        await backend.searchFeatures(
          query,
          category,
          claim_type,
          include_drafts ?? false,
          limit ?? 20,
        ),
      );
    } catch (error) {
      return errorResult(error);
    }
  },
);

server.registerTool(
  "list_feature_relations",
  {
    description: "List evidence-backed feature relations from reviewed cards and optional drafts.",
    inputSchema: {
      system_id: z.string().regex(/^[a-z0-9-]+$/).optional(),
      feature_id: z.string().regex(/^[a-z0-9-]+$/).optional(),
      target_system_id: z.string().regex(/^[a-z0-9-]+$/).optional(),
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
      include_drafts: z.boolean().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ system_id, feature_id, target_system_id, type, include_drafts, limit }) => {
    try {
      return jsonResult({
        data: await backend.listFeatureRelations(
          system_id,
          feature_id,
          target_system_id,
          type,
          include_drafts ?? false,
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
      input_system: z.string().regex(/^[a-z0-9-]+$/).optional(),
      claim_status: z
        .enum(["proposed", "under-review", "accepted", "rejected", "deprecated"])
        .optional(),
      include_drafts: z.boolean().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ input_system, claim_status, include_drafts, limit }) => {
    try {
      return jsonResult(
        await backend.listCompositions(
          input_system,
          claim_status,
          include_drafts ?? false,
          limit ?? 20,
        ),
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

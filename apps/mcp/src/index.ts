import { readdir, readFile } from "node:fs/promises";
import { resolve } from "node:path";
import { fileURLToPath } from "node:url";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import { z } from "zod";

type Evidence = {
  id: string;
  kind: string;
  title: string;
  uri: string;
  notes?: string;
};

type Feature = {
  id: string;
  name: string;
  category: string;
  claim_type: string;
  description: string;
  benefits?: string[];
  costs?: string[];
  evidence_ids: string[];
};

type ArchitectureCard = {
  id: string;
  name: string;
  summary: string;
  scope: string[];
  features: Feature[];
  mathematical_views: Array<Record<string, unknown>>;
  trade_offs: Array<Record<string, unknown>>;
  evidence: Evidence[];
  related_systems?: string[];
  version_context?: string;
};

const repositoryRoot = resolve(
  process.env.MATHEN_ROOT ?? fileURLToPath(new URL("../../..", import.meta.url)),
);
const systemsDirectory = resolve(repositoryRoot, "data/systems");
const draftsDirectory = resolve(repositoryRoot, "data/drafts");
const bundlesDirectory = resolve(repositoryRoot, "data/modeling");

async function readJson<T>(path: string): Promise<T> {
  return JSON.parse(await readFile(path, "utf8")) as T;
}

async function loadCards(directory: string): Promise<ArchitectureCard[]> {
  const entries = (await readdir(directory, { withFileTypes: true }))
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => entry.name);
  const cards = await Promise.all(
    entries.sort().map((entry) => readJson<ArchitectureCard>(resolve(directory, entry))),
  );
  return cards;
}

async function loadAllCards(includeDrafts: boolean): Promise<ArchitectureCard[]> {
  const reviewed = await loadCards(systemsDirectory);
  if (!includeDrafts) return reviewed;
  const drafts = await loadCards(draftsDirectory);
  return [...reviewed, ...drafts.filter((draft) => !reviewed.some((card) => card.id === draft.id))];
}

function jsonResult(value: unknown) {
  return {
    content: [{ type: "text" as const, text: JSON.stringify(value, null, 2) }],
  };
}

const server = new McpServer({ name: "mathen", version: "0.1.0" });

server.registerTool(
  "list_systems",
  {
    description: "List reviewed Mathen architecture cards, optionally including drafts.",
    inputSchema: { include_drafts: z.boolean().optional() },
  },
  async ({ include_drafts }) => {
    const cards = await loadAllCards(include_drafts ?? false);
    return jsonResult(
      cards.map(({ id, name, summary, version_context }) => ({
        id,
        name,
        summary,
        version_context,
        status: include_drafts ? "reviewed-or-draft" : "reviewed",
      })),
    );
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
    const cards = await loadAllCards(include_drafts ?? false);
    const card = cards.find((candidate) => candidate.id === system_id);
    if (!card) return jsonResult({ error: `system not found: ${system_id}` });
    return jsonResult(card);
  },
);

server.registerTool(
  "search_features",
  {
    description: "Search reusable architecture features across reviewed cards and optional drafts.",
    inputSchema: {
      query: z.string().min(1),
      category: z.string().optional(),
      include_drafts: z.boolean().optional(),
      limit: z.number().int().min(1).max(50).optional(),
    },
  },
  async ({ query, category, include_drafts, limit }) => {
    const normalizedQuery = query.toLowerCase();
    const cards = await loadAllCards(include_drafts ?? false);
    const results = cards.flatMap((card) =>
      card.features
        .filter((feature) => {
          const haystack = `${feature.name} ${feature.description} ${feature.category}`.toLowerCase();
          return haystack.includes(normalizedQuery) && (!category || feature.category === category);
        })
        .map((feature) => ({
          system_id: card.id,
          system_name: card.name,
          feature,
        })),
    );
    return jsonResult(results.slice(0, limit ?? 20));
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
      return jsonResult(await readJson(resolve(bundlesDirectory, `${system_id}.json`)));
    } catch {
      return jsonResult({ error: `modeling bundle not found: ${system_id}` });
    }
  },
);

const transport = new StdioServerTransport();
await server.connect(transport);

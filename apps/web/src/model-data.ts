import {
  domainFor,
  searchSystems,
  type GraphEdge,
  type SimulationNode as SystemSimulationNode,
  type SystemSummary,
} from "./graph-data";

export type ModelViewMetadata = {
  id: string | number;
  model: string;
  question: string;
  assumptions: string[];
  claim_type: string;
  evidence_ids: string[];
};
export type ModelGraphNode = {
  id: string;
  name: string;
  type: "system" | "model";
};
export type ModelGraphEdge = {
  source: string;
  target: string;
  type: "modeled-by";
  claim_type: "inference";
  metadata: ModelViewMetadata[];
};
export type ModelGraphPayload = {
  nodes: ModelGraphNode[];
  edges: ModelGraphEdge[];
};
export type ExplorerPayload = {
  nodes: ModelGraphNode[];
  edges: (GraphEdge & { metadata?: ModelViewMetadata[] })[];
};
export type SimulationNode = Omit<SystemSimulationNode, "type"> & ModelGraphNode;
export type SimulationLink = Omit<ExplorerPayload["edges"][number], "source" | "target"> & {
  id: string;
  source: string | SimulationNode;
  target: string | SimulationNode;
};

function record(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.every((item) => typeof item === "string");
}
function view(value: unknown): value is ModelViewMetadata {
  return (
    record(value) &&
    (typeof value.id === "string" || typeof value.id === "number") &&
    typeof value.model === "string" &&
    typeof value.question === "string" &&
    typeof value.claim_type === "string" &&
    strings(value.assumptions) &&
    strings(value.evidence_ids)
  );
}

/** Validate the bipartite API contract; do not infer new edges or claim types. */
export function normalizeModelGraph(payload: unknown): ModelGraphPayload {
  if (!record(payload) || !record(payload.data)) throw new Error("Invalid model graph envelope");
  const { nodes, edges } = payload.data;
  if (!Array.isArray(nodes) || !Array.isArray(edges))
    throw new Error("Invalid model graph payload");
  const types = new Map<string, string>();
  for (const node of nodes) {
    if (
      !record(node) ||
      typeof node.id !== "string" ||
      !node.id ||
      typeof node.name !== "string" ||
      (node.type !== "system" && node.type !== "model") ||
      types.has(node.id)
    )
      throw new Error("Invalid model graph node");
    types.set(node.id, node.type);
  }
  for (const edge of edges) {
    if (
      !record(edge) ||
      typeof edge.source !== "string" ||
      typeof edge.target !== "string" ||
      types.get(edge.source) !== "system" ||
      types.get(edge.target) !== "model" ||
      edge.type !== "modeled-by" ||
      edge.claim_type !== "inference" ||
      !Array.isArray(edge.metadata) ||
      !edge.metadata.every(view)
    )
      throw new Error("Invalid modeled-by edge");
  }
  return structuredClone({ nodes, edges }) as ModelGraphPayload;
}

export async function loadModelGraph(request: (input: string) => Promise<Response> = fetch) {
  const response = await request("/api/graph/models");
  if (!response.ok) throw new Error(`Model graph API returned ${response.status}`);
  return normalizeModelGraph(await response.json());
}

/** Filter systems first, then retain their hubs rather than treating models as domains. */
export function filterModelGraph(graph: ModelGraphPayload, domain = "all"): ModelGraphPayload {
  if (domain === "all") return { nodes: graph.nodes.slice(), edges: graph.edges.slice() };
  const ids = new Set(
    graph.nodes
      .filter((node) => node.type === "system" && domainFor(node.id).id === domain)
      .map((node) => node.id),
  );
  const edges = graph.edges.filter((edge) => ids.has(edge.source));
  for (const edge of edges) ids.add(edge.target);
  return { nodes: graph.nodes.filter((node) => ids.has(node.id)), edges };
}

/** Deep-copy nested metadata before lending any payload to the force engine. */
export function modelSimulationData(graph: ExplorerPayload) {
  const copy = structuredClone(graph);
  const known = new Set(copy.nodes.map((node) => node.id));
  const degree = new Map<string, number>();
  const links: SimulationLink[] = copy.edges.flatMap((edge, index) => {
    if (!known.has(edge.source) || !known.has(edge.target)) return [];
    degree.set(edge.source, (degree.get(edge.source) ?? 0) + 1);
    degree.set(edge.target, (degree.get(edge.target) ?? 0) + 1);
    return [{ ...edge, id: `edge-${index}` }];
  });
  const nodes: SimulationNode[] = copy.nodes.map((node) => ({
    ...node,
    degree: degree.get(node.id) ?? 0,
  }));
  return { nodes, links };
}

export function endpointId(endpoint: string | SimulationNode) {
  return typeof endpoint === "string" ? endpoint : endpoint.id;
}
export function neighborhood(graph: ExplorerPayload, id: string) {
  const ids = new Set([id]);
  for (const edge of graph.edges) {
    if (edge.source === id) ids.add(edge.target);
    if (edge.target === id) ids.add(edge.source);
  }
  return ids;
}
export function searchNodes(nodes: ModelGraphNode[], systems: SystemSummary[], query: string) {
  const matches = new Set(
    searchSystems(
      nodes.filter((node): node is ModelGraphNode & { type: "system" } => node.type === "system"),
      systems,
      query,
    ).map((node) => node.id),
  );
  const normalized = query.trim().toLowerCase();
  return nodes.filter((node) =>
    node.type === "model"
      ? `${node.id} ${node.name}`.toLowerCase().includes(normalized)
      : matches.has(node.id),
  );
}

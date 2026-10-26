import { simulationEdgeId, type ExplorerPayload } from "./model-data";

export type Pin = { x: number; y: number; z: number };
type Pinnable = {
  x?: number;
  y?: number;
  z?: number;
  fx?: number;
  fy?: number;
  fz?: number;
};

export type ShortestPath = { nodes: string[]; edges: Set<string> };
export type PathEdge = {
  id: string;
  source: string;
  target: string;
  type: string;
};
export type ShortestRoute = { nodes: string[]; edges: PathEdge[] };

/** Explicit domain exceptions; relation selection and hidden nodes still apply. O(V + E). */
export function applyView(
  source: ExplorerPayload,
  base: ExplorerPayload,
  expanded: Set<string>,
  hidden: Set<string>,
  relation: string,
): ExplorerPayload {
  const ids = new Set([...base.nodes.map((node) => node.id), ...expanded]);
  const nodes = source.nodes.filter((node) => ids.has(node.id) && !hidden.has(node.id));
  const shown = new Set(nodes.map((node) => node.id));
  return {
    nodes,
    edges: source.edges.filter(
      (edge) =>
        shown.has(edge.source) &&
        shown.has(edge.target) &&
        (relation === "all" || edge.type === relation),
    ),
  };
}

export function expandOneHop(
  source: ExplorerPayload,
  id: string,
  expanded: Set<string>,
  relation: string,
) {
  expanded.add(id);
  for (const edge of source.edges) {
    if (relation !== "all" && edge.type !== relation) continue;
    if (edge.source === id) expanded.add(edge.target);
    if (edge.target === id) expanded.add(edge.source);
  }
}

export function applyPin(node: Pinnable, pin: Pin | undefined, dimensions: 2 | 3) {
  node.fx = pin?.x;
  node.fy = pin?.y;
  node.fz = pin ? (dimensions === 2 ? 0 : pin.z) : undefined;
  if (pin) {
    node.x = pin.x;
    node.y = pin.y;
    node.z = dimensions === 2 ? 0 : pin.z;
  }
}

/**
 * Find a deterministic shortest path in the currently visible graph.
 * Relations are treated as traversable in either direction for exploration;
 * this does not create or imply a new directed relation.
 */
export function shortestPath(
  graph: ExplorerPayload,
  start: string,
  target: string,
): ShortestPath | undefined {
  const route = shortestRoute(graph, start, target);
  return route
    ? { nodes: route.nodes, edges: new Set(route.edges.map((edge) => edge.id)) }
    : undefined;
}

/**
 * Return the ordered, visible-graph route including relation metadata.
 * Traversal is bidirectional for discovery only; it does not infer a directed relation.
 */
export function shortestRoute(
  graph: ExplorerPayload,
  start: string,
  target: string,
): ShortestRoute | undefined {
  if (start === target) return { nodes: [start], edges: [] };
  const known = new Set(graph.nodes.map((node) => node.id));
  if (!known.has(start) || !known.has(target)) return undefined;
  const adjacency = new Map<string, { edge: PathEdge; node: string }[]>();
  for (const edge of graph.edges) {
    if (!known.has(edge.source) || !known.has(edge.target)) continue;
    const pathEdge = {
      id: simulationEdgeId(edge.source, edge.target, edge.type),
      source: edge.source,
      target: edge.target,
      type: edge.type,
    };
    adjacency.set(edge.source, [
      ...(adjacency.get(edge.source) ?? []),
      { edge: pathEdge, node: edge.target },
    ]);
    adjacency.set(edge.target, [
      ...(adjacency.get(edge.target) ?? []),
      { edge: pathEdge, node: edge.source },
    ]);
  }
  const previous = new Map<string, { node: string; edge: PathEdge }>();
  const queue = [start];
  const visited = new Set([start]);
  while (queue.length) {
    const current = queue.shift()!;
    for (const next of adjacency.get(current) ?? []) {
      if (visited.has(next.node)) continue;
      visited.add(next.node);
      previous.set(next.node, { node: current, edge: next.edge });
      if (next.node === target) {
        const nodes = [target];
        const edges: PathEdge[] = [];
        let cursor = target;
        while (cursor !== start) {
          const step = previous.get(cursor);
          if (!step) return undefined;
          edges.push(step.edge);
          cursor = step.node;
          nodes.push(cursor);
        }
        nodes.reverse();
        edges.reverse();
        return { nodes, edges };
      }
      queue.push(next.node);
    }
  }
  return undefined;
}

export function formatRouteText(route: ShortestRoute, names: (id: string) => string): string {
  if (!route.edges.length) return names(route.nodes[0]);
  return route.edges
    .map(
      (edge, index) =>
        `${names(route.nodes[index])} --${edge.type} [${edge.id}]-- ${names(route.nodes[index + 1])}`,
    )
    .join("\n");
}

export function serializeExplorationPath(
  route: ShortestRoute,
  names: (id: string) => string,
  color?: string,
) {
  return {
    kind: "graph-exploration-path" as const,
    claim:
      "navigation and discovery output only; not a canonical relation, causal chain, compatibility claim, proof, or inferred evidence",
    color,
    nodes: route.nodes.map((id) => ({ id, name: names(id) })),
    edges: route.edges.map((edge) => ({ ...edge })),
  };
}

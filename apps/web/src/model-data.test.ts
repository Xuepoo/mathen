import { describe, expect, test } from "bun:test";
import {
  filterModelGraph,
  loadModelGraph,
  modelSimulationData,
  normalizeModelGraph,
  neighborhood,
  searchNodes,
  type ModelGraphPayload,
} from "./model-data";

const graph: ModelGraphPayload = {
  nodes: [
    { id: "react", name: "React", type: "system" },
    { id: "temporal", name: "Temporal", type: "system" },
    { id: "model:state", name: "State machines", type: "model" },
    { id: "model:queue", name: "Queues", type: "model" },
  ],
  edges: ["react", "temporal"].map((source, index) => ({
    source,
    target: "model:state",
    type: "modeled-by",
    claim_type: "inference",
    metadata: [
      {
        id: index,
        model: "Transition system",
        question: "Which transitions are valid?",
        assumptions: ["Events are ordered"],
        claim_type: "hypothesis",
        evidence_ids: ["e1"],
      },
    ],
  })),
};

describe("mathematical model graph", () => {
  test("normalizes the API envelope without inventing system relations", () => {
    const normalized = normalizeModelGraph({ data: graph });
    expect(normalized).toEqual(graph);
    expect(normalized).not.toBe(graph);
    expect(() => normalizeModelGraph({ nodes: [], edges: [] })).toThrow();
    expect(() => normalizeModelGraph({ data: { nodes: [], edges: null } })).toThrow();
    expect(() =>
      normalizeModelGraph({
        data: {
          ...graph,
          edges: [{ ...graph.edges[0], target: "temporal" }],
        },
      }),
    ).toThrow();
    expect(() =>
      normalizeModelGraph({
        data: {
          ...graph,
          edges: [{ ...graph.edges[0], target: "missing" }],
        },
      }),
    ).toThrow();
    expect(() =>
      normalizeModelGraph({
        data: {
          ...graph,
          edges: [{ ...graph.edges[0], metadata: [{ model: "Incomplete" }] }],
        },
      }),
    ).toThrow();
  });

  test("filters systems by domain and retains only their actual model hubs", () => {
    const filtered = filterModelGraph(graph, "web");
    expect(filtered.nodes.map((node) => node.id)).toEqual(["react", "model:state"]);
    expect(filtered.edges).toEqual([graph.edges[0]]);
    expect(filterModelGraph(graph).nodes).toHaveLength(4);
    expect(filterModelGraph(graph, "missing")).toEqual({
      nodes: [],
      edges: [],
    });
    expect(graph.edges).toHaveLength(2);
  });

  test("search and selection find model families without linking systems to each other", () => {
    expect(searchNodes(graph.nodes, [], "STATE").map((node) => node.id)).toEqual(["model:state"]);
    expect(searchNodes(graph.nodes, [], "react").map((node) => node.id)).toEqual(["react"]);
    expect([...neighborhood(graph, "model:state")]).toEqual(["model:state", "react", "temporal"]);
    expect([...neighborhood(graph, "react")]).toEqual(["react", "model:state"]);
  });

  test("force mutation cannot alter canonical nodes, endpoints, or nested view metadata", () => {
    const before = JSON.stringify(graph);
    const canonical = normalizeModelGraph({ data: graph });
    const force = modelSimulationData(filterModelGraph(canonical));
    force.nodes[0].x = 123;
    force.links[0].source = force.nodes[0];
    force.links[0].metadata![0].assumptions.push("mutation");
    force.links[0].metadata![0].evidence_ids.push("mutation");
    force.links[0].metadata![0].question = "mutation";
    expect(JSON.stringify(canonical)).toBe(before);
    expect(JSON.stringify(graph)).toBe(before);
    expect(force.nodes.find((node) => node.id === "model:state")?.degree).toBe(2);
    expect(force.links).toHaveLength(2);
  });

  test("fetches the model endpoint and reports failures", async () => {
    const urls: string[] = [];
    expect(
      await loadModelGraph(async (url) => {
        urls.push(url);
        return Response.json({ data: graph });
      }),
    ).toEqual(graph);
    expect(urls).toEqual(["/api/graph/models"]);
    await expect(loadModelGraph(async () => new Response(null, { status: 503 }))).rejects.toThrow(
      "503",
    );
  });
});

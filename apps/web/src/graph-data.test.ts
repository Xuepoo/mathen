import { describe, expect, test } from "bun:test";
import {
  domainFor,
  filterGraph,
  loadAllSystems,
  neighborhood,
  searchSystems,
  simulationData,
  type GraphPayload,
  type SystemSummary,
} from "./graph-data";

const graph: GraphPayload = {
  nodes: ["a", "b", "c", "isolated"].map((id) => ({ id, name: id.toUpperCase(), type: "system" })),
  edges: [
    { source: "a", target: "b", type: "inspired_by", evidence_ids: ["e1"] },
    { source: "c", target: "a", type: "related" },
    { source: "a", target: "missing", type: "related" },
  ],
};

describe("force graph data boundaries", () => {
  test("force endpoint and position mutation cannot change canonical data", () => {
    const before = JSON.stringify(graph);
    const force = simulationData(graph);
    force.links[0].source = force.nodes[0];
    force.nodes[0].x = 40;
    force.links[0].evidence_ids?.push("mutated");
    expect(JSON.stringify(graph)).toBe(before);
    expect(force.links).toHaveLength(2);
    expect(force.nodes).toHaveLength(4);
  });

  test("typed filtering retains isolated nodes and limits both directions of neighbors", () => {
    expect(simulationData(graph, "inspired_by").links).toHaveLength(1);
    expect(simulationData(graph, "inspired_by").nodes).toHaveLength(4);
    expect([...neighborhood(graph, "a", "inspired_by")]).toEqual(["a", "b"]);
    expect(neighborhood(graph, "c").has("a")).toBe(true);
  });
});

describe("complete catalog metadata", () => {
  test("navigation domains filter real edges without inventing relationships", () => {
    const payload: GraphPayload = {
      nodes: ["react", "vue", "temporal", "unknown"].map((id) => ({
        id,
        name: id,
        type: "system",
      })),
      edges: [
        { source: "react", target: "vue", type: "related" },
        { source: "react", target: "temporal", type: "uses" },
      ],
    };
    const filtered = filterGraph(payload, "web");
    expect(filtered.nodes.map((node) => node.id)).toEqual(["react", "vue"]);
    expect(filtered.edges).toHaveLength(1);
    expect([...neighborhood(filtered, "react")]).toEqual(["react", "vue"]);
    expect(domainFor("unknown").id).toBe("others");
    expect(filterGraph(payload, "web", "uses").edges).toHaveLength(0);
    expect(payload.edges).toHaveLength(2);
  });
  test("loads and searches all 154 systems including metadata beyond the first 100", async () => {
    const systems: SystemSummary[] = Array.from({ length: 154 }, (_, index) => ({
      id: `system-${index}`,
      name: index === 153 ? "Temporal" : `System ${index}`,
      version_context: null,
      summary: "Reviewed system",
      scope: index === 153 ? ["Durable execution"] : ["Storage"],
      related_systems: [],
    }));
    const urls: string[] = [];
    const request = (async (url: string) => {
      urls.push(url);
      const offset = Number(new URL(url, "https://mathen.test").searchParams.get("offset"));
      return Response.json({ data: systems.slice(offset, offset + 100) });
    }) as (input: string) => Promise<Response>;
    const loaded = await loadAllSystems(request);
    expect(loaded).toHaveLength(154);
    expect(urls).toEqual(["/api/systems?limit=100&offset=0", "/api/systems?limit=100&offset=100"]);
    const nodes = systems.map(({ id, name }) => ({ id, name, type: "system" as const }));
    expect(searchSystems(nodes, loaded, "durable execution").map((node) => node.name)).toEqual([
      "Temporal",
    ]);
    expect(searchSystems(nodes, [], "Temporal")).toHaveLength(1);
  });

  test("rejects ignored pagination instead of silently publishing incomplete metadata", async () => {
    const page = Array.from({ length: 100 }, (_, index) => ({ id: `system-${index}` }));
    await expect(
      loadAllSystems((async () => Response.json({ data: page })) as (
        input: string,
      ) => Promise<Response>),
    ).rejects.toThrow("did not advance pagination");
  });
});

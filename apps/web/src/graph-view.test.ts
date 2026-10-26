import { expect, test } from "bun:test";
import { applyView, expandOneHop, applyPin, shortestPath } from "./graph-view";
import type { ExplorerPayload } from "./model-data";

const source: ExplorerPayload = {
  nodes: ["a", "b", "c", "d"].map((id) => ({ id, name: id, type: "system" })),
  edges: [
    { source: "a", target: "b", type: "uses" },
    { source: "b", target: "c", type: "related" },
  ],
};
test("expansion adds exactly one actual hop outside domain; hidden nodes and relation filters win", () => {
  const expanded = new Set<string>();
  expandOneHop(source, "a", expanded, "all");
  const base = { nodes: [source.nodes[0]], edges: [] };
  const result = applyView(source, base, expanded, new Set(), "all");
  expect(result.nodes.map((node) => node.id)).toEqual(["a", "b"]);
  expect(result.edges).toEqual([source.edges[0]]);
  expect(applyView(source, base, expanded, new Set(["b"]), "all").edges).toEqual([]);
  const restricted = new Set<string>();
  expandOneHop(source, "a", restricted, "related");
  expect([...restricted]).toEqual(["a"]);
  expect(source.nodes).toHaveLength(4);
});
test("pins survive flattened 2D without losing their stored 3D depth", () => {
  const pin = { x: 1, y: 2, z: 35 };
  const node = {
    id: "a",
    x: 0,
    y: 0,
    z: 0,
    fx: undefined as number | undefined,
    fy: undefined as number | undefined,
    fz: undefined as number | undefined,
  };
  applyPin(node, pin, 2);
  expect([node.fx, node.fy, node.fz, node.z]).toEqual([1, 2, 0, 0]);
  applyPin(node, pin, 3);
  expect([node.fx, node.fy, node.fz, node.z]).toEqual([1, 2, 35, 35]);
  applyPin(node, undefined, 3);
  expect(node.fx).toBeUndefined();
  expect(pin.z).toBe(35);
});

test("shortest path explores relations in either direction with deterministic BFS", () => {
  const result = shortestPath(source, "a", "c");
  expect(result?.nodes).toEqual(["a", "b", "c"]);
  expect(result?.edges).toEqual(new Set(['edge-["a","b","uses"]', 'edge-["b","c","related"]']));
  expect(shortestPath(source, "a", "d")).toBeUndefined();
});

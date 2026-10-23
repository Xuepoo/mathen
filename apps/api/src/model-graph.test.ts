import assert from "node:assert/strict";
import { test } from "node:test";
import { buildModelGraph, type ModelViewRow } from "./model-graph.js";

function row(overrides: Partial<ModelViewRow> = {}): ModelViewRow {
  return {
    system_id: "alpha",
    system_name: "Alpha",
    view_id: 1,
    model: "State machine",
    question: "How does it transition?",
    assumptions_json: '["finite states"]',
    claim_type: "inference",
    evidence_ids_json: '["architecture"]',
    ...overrides,
  };
}

test("groups views by curated mathematical family, not broad vocabulary", () => {
  const graph = buildModelGraph([
    row({ view_id: 1, model: "M/M/1 queueing cost model" }),
    row({ view_id: 2, model: "Commutative algebra of query operators" }),
    row({ view_id: 3, model: "Capability-preserving protocol refinement" }),
    row({ view_id: 4, model: "Equality boundary graph" }),
    row({ view_id: 5, model: "Relational algebra operator pipeline" }),
  ]);

  assert.deepEqual(
    graph.nodes.filter((node) => node.type === "model"),
    [
      {
        id: "model:algebra-relational-algebra",
        name: "Algebra and relational algebra",
        type: "model",
      },
      { id: "model:equality-boundary-graph", name: "Equality boundary graph", type: "model" },
      {
        id: "model:queueing-cost-resource",
        name: "Queueing, cost, and resource models",
        type: "model",
      },
      {
        id: "model:simulation-refinement",
        name: "Simulation and refinement",
        type: "model",
      },
    ],
  );
  assert.equal(
    graph.edges.find((edge) => edge.metadata[0]?.model.includes("queueing"))?.target,
    "model:queueing-cost-resource",
  );
  assert.equal(
    graph.edges.find((edge) => edge.metadata[0]?.model.includes("refinement"))?.target,
    "model:simulation-refinement",
  );
  assert.equal(
    graph.edges.find((edge) => edge.metadata[0]?.model.startsWith("Equality"))?.target,
    "model:equality-boundary-graph",
  );
  assert.equal(
    graph.edges.find((edge) => edge.metadata.some((view) => view.model.startsWith("Relational")))
      ?.target,
    "model:algebra-relational-algebra",
  );
});

test("aggregates shared hubs while preserving view metadata and source evidence", () => {
  const graph = buildModelGraph([
    row({ system_id: "beta", system_name: "Beta", view_id: "b", model: "State machine" }),
    row({
      system_id: "alpha",
      view_id: "a",
      model: "Transition system",
      assumptions_json: '["one"]',
      evidence_ids_json: '["alpha-source"]',
      claim_type: "hypothesis",
    }),
    row({
      system_id: "alpha",
      view_id: "a2",
      model: "State machine",
      assumptions_json: '["two"]',
      evidence_ids_json: '["alpha-second"]',
    }),
  ]);

  const stateEdges = graph.edges.filter((edge) => edge.target === "model:state-transition-systems");
  assert.equal(stateEdges.length, 2);
  assert.deepEqual(stateEdges[0]?.metadata, [
    {
      id: "a",
      model: "Transition system",
      question: "How does it transition?",
      assumptions: ["one"],
      claim_type: "hypothesis",
      evidence_ids: ["alpha-source"],
    },
    {
      id: "a2",
      model: "State machine",
      question: "How does it transition?",
      assumptions: ["two"],
      claim_type: "inference",
      evidence_ids: ["alpha-second"],
    },
  ]);
  assert.equal(stateEdges[0]?.claim_type, "inference");
  assert.equal(stateEdges[0]?.type, "modeled-by");
});

test("malformed JSON and non-array values are safe, and inputs are not mutated", () => {
  const input = [
    row({
      assumptions_json: '{"not":"an array"}',
      evidence_ids_json: '["kept", 42, null]',
    }),
  ];
  const snapshot = structuredClone(input);
  const graph = buildModelGraph(input);

  assert.deepEqual(input, snapshot);
  assert.deepEqual(graph.edges[0]?.metadata[0], {
    id: 1,
    model: "State machine",
    question: "How does it transition?",
    assumptions: [],
    claim_type: "inference",
    evidence_ids: ["kept"],
  });
});

test("unknown model names remain distinct with deterministic collision-safe IDs", () => {
  const rows = [
    row({ view_id: 1, model: "Novel / Model" }),
    row({ view_id: 2, model: "Novel Model" }),
  ];
  const first = buildModelGraph(rows);
  const second = buildModelGraph([...rows].reverse());
  const firstUnknowns = first.nodes.filter((node) => node.type === "model");
  const secondUnknowns = second.nodes.filter((node) => node.type === "model");

  assert.equal(firstUnknowns.length, 2);
  assert.deepEqual(firstUnknowns, secondUnknowns);
  assert.equal(new Set(firstUnknowns.map((node) => node.id)).size, 2);
  assert.deepEqual(first.edges.flatMap((edge) => edge.metadata.map((view) => view.model)).sort(), [
    "Novel / Model",
    "Novel Model",
  ]);
});

test("system names and arbitrary unknown fields do not create unsupported edges", () => {
  const graph = buildModelGraph([
    { ...row(), extra: "ignored" } as ModelViewRow,
    row({ system_id: "beta", system_name: "Beta", model: "Unrelated model" }),
  ]);

  assert.deepEqual(
    graph.nodes.filter((node) => node.type === "system"),
    [
      { id: "alpha", name: "Alpha", type: "system" },
      { id: "beta", name: "Beta", type: "system" },
    ],
  );
  assert.equal(
    graph.edges.some((edge) => edge.source === "alpha" && edge.target === "beta"),
    false,
  );
});

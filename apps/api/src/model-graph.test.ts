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

test("groups views by explicit navigation wording and retains all matches", () => {
  const graph = buildModelGraph([
    row({ view_id: 1, model: "M/M/1 queueing cost model" }),
    row({ view_id: 2, model: "Commutative algebra of query operators" }),
    row({ view_id: 3, model: "Capability-preserving protocol refinement" }),
    row({ view_id: 4, model: "Equality boundary graph" }),
    row({ view_id: 5, model: "Relational algebra operator pipeline" }),
  ]);

  for (const node of graph.nodes.filter((node) => node.type === "model")) {
    assert.match(node.name, /^(Navigation family:|Same title:)/);
    assert.match(node.description ?? "", /not establish formal equivalence/);
  }
  assert.equal(
    graph.edges.find((edge) => edge.metadata[0]?.model.includes("queueing"))?.target,
    "model:cost-resource",
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
  assert.ok(graph.edges.some((edge) => edge.target === "model:queueing-theory"));
  assert.ok(graph.edges.some((edge) => edge.target === "model:dataflow-pipelines"));
});

test("aggregates shared hubs while preserving view metadata and source evidence", () => {
  const graph = buildModelGraph([
    row({
      system_id: "beta",
      system_name: "Beta",
      view_id: "b",
      model: "State machine",
    }),
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
  assert.deepEqual(
    stateEdges[0]?.metadata
      .map(({ key: _key, ...view }) => view)
      .sort((left, right) => String(left.id).localeCompare(String(right.id))),
    [
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
    ],
  );
  assert.equal(stateEdges[0]?.claim_type, "mixed");
  assert.equal(stateEdges[1]?.claim_type, "inference");
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
  const { key: _key, ...metadata } = graph.edges[0]!.metadata[0]!;
  assert.deepEqual(metadata, {
    id: 1,
    model: "State machine",
    question: "How does it transition?",
    assumptions: [],
    claim_type: "inference",
    evidence_ids: ["kept"],
  });
});

test("single-claim aggregates preserve analogy and hypothesis claims", () => {
  for (const claim_type of ["analogy", "hypothesis", "fact"]) {
    const graph = buildModelGraph([row({ claim_type }), row({ view_id: 2, claim_type })]);
    assert.equal(graph.edges[0]?.claim_type, claim_type);
    assert.ok(graph.edges[0]?.metadata.every((view) => view.claim_type === claim_type));
    assert.equal(graph.edges[0]?.metadata.length, 2);
    assert.equal(graph.edges[0]?.metadata[0]?.key, graph.edges[0]?.metadata[1]?.key);
  }
});

test("ambiguous real titles expose conservative, multiple navigation families", () => {
  const cases: Array<[string, string[]]> = [
    ["Event queue transition system", ["state-transition-systems"]],
    ["Device-peer work-queue graph", []],
    ["Parallel producer/single-consumer resource model", ["cost-resource"]],
    ["Capability and path policy lattice", ["lattices-orders"]],
    ["Inclusion fixed-point process", ["fixed-points-convergence"]],
    ["Eventually convergent gateway configuration", ["fixed-points-convergence"]],
    [
      "Eventually convergent placement state machine",
      ["fixed-points-convergence", "state-transition-systems"],
    ],
    ["Process group model", []],
    ["Relational algebra operator pipeline", ["algebra-relational-algebra", "dataflow-pipelines"]],
    ["Checkpointed dataflow transition system", ["dataflow-pipelines", "state-transition-systems"]],
    ["Analysis-transform refinement pipeline", ["dataflow-pipelines", "simulation-refinement"]],
    [
      "Relational algebra to bytecode operational semantics",
      ["algebra-relational-algebra", "state-transition-systems"],
    ],
    ["Queue-mediated open-system state machine", ["state-transition-systems"]],
  ];
  for (const [model, expected] of cases) {
    const graph = buildModelGraph([row({ model })]);
    const families = graph.nodes.filter((node) => node.name.startsWith("Navigation family:"));
    assert.deepEqual(families.map((node) => node.id.replace("model:", "")).sort(), expected, model);
  }
});

test("view keys survive database reseeding, normalize wording, and avoid slug/delimiter collisions", () => {
  const rows = [
    row({ model: "Novel / Model", question: "a:b" }),
    row({ model: "Novel Model", question: "a:b" }),
    row({ model: "Novel", question: "Model:a:b" }),
    row({ system_id: "beta", model: "Novel / Model", question: "a:b" }),
    row({ model: "Novel\u0000Model", question: "a:b" }),
    row({ model: "Novel", question: "Model\u0000a:b" }),
  ];
  const first = buildModelGraph(rows).edges.flatMap((edge) =>
    edge.metadata.map((view) => view.key),
  );
  const second = buildModelGraph(
    rows
      .map((view, index) => ({
        ...view,
        view_id: 900 - index,
        model: `  ${view.model.toUpperCase()}  `,
        question: ` ${view.question} `,
      }))
      .reverse(),
  ).edges.flatMap((edge) => edge.metadata.map((view) => view.key));
  assert.equal(new Set(first).size, rows.length);
  assert.deepEqual(first.sort(), second.sort());
});

test("unknown shared titles are explicitly same-title navigation", () => {
  const graph = buildModelGraph([
    row({ model: "Snapshot visibility relation" }),
    row({
      system_id: "beta",
      model: "Snapshot visibility relation",
      question: "Which snapshots?",
    }),
  ]);
  const model = graph.nodes.find((node) => node.type === "model");
  assert.equal(model?.name, "Same title: Snapshot visibility relation");
  assert.match(model?.description ?? "", /not establish formal equivalence/);
  assert.equal(graph.edges.length, 2);
  assert.notEqual(graph.edges[0]?.metadata[0]?.key, graph.edges[1]?.metadata[0]?.key);
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

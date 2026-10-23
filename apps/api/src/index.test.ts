import assert from "node:assert/strict";
import { test } from "node:test";
import {
  app,
  buildCompositions,
  buildGraph,
  serializeFeature,
  serializeMathematicalView,
} from "./index.js";

test("GET /api/systems defaults to the first page with deterministic ordering", async () => {
  const rows = Array.from({ length: 101 }, (_, index) => systemRow(index));
  const calls: { sql: string; bindings: unknown[] }[] = [];
  const db = mockSystemsDatabase(rows, calls);

  const response = await app.request(
    "/api/systems",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );

  assert.equal(response.status, 200);
  const body = (await response.json()) as { data: Array<{ id: string }> };
  assert.equal(body.data.length, 50);
  assert.equal(body.data[0]?.id, "system-000");
  assert.equal(body.data.at(-1)?.id, "system-049");
  assert.deepEqual(calls[0]?.bindings, ["", "%%", 50, 0]);
  assert.match(calls[0]?.sql ?? "", /ORDER BY name, id/);
  assert.match(calls[0]?.sql ?? "", /LIMIT \?3 OFFSET \?4/);
});

test("GET /api/systems clamps limit and supports offsets beyond the maximum page size", async () => {
  const rows = Array.from({ length: 101 }, (_, index) => systemRow(index));
  const calls: { sql: string; bindings: unknown[] }[] = [];
  const db = mockSystemsDatabase(rows, calls);

  const response = await app.request(
    "/api/systems?limit=999&offset=100",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );

  assert.equal(response.status, 200);
  const body = (await response.json()) as { data: Array<{ id: string }> };
  assert.deepEqual(
    body.data.map((system) => system.id),
    ["system-100"],
  );
  assert.deepEqual(calls[0]?.bindings, ["", "%%", 100, 100]);
});

test("GET /api/systems clamps negative pagination values", async () => {
  const calls: { sql: string; bindings: unknown[] }[] = [];
  const db = mockSystemsDatabase([systemRow(0)], calls);

  const response = await app.request(
    "/api/systems?limit=-10&offset=-20",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );

  assert.equal(response.status, 200);
  assert.deepEqual(calls[0]?.bindings, ["", "%%", 1, 0]);
});

test("serializes feature and mathematical-view evidence references", () => {
  assert.deepEqual(
    serializeFeature({
      id: "embedded",
      name: "Embedded execution",
      category: "execution-model",
      claim_type: "fact",
      description: "Runs in-process.",
      benefits_json: '["low deployment overhead"]',
      costs_json: "[]",
      evidence_ids_json: '["architecture", "source"]',
    }),
    {
      id: "embedded",
      name: "Embedded execution",
      category: "execution-model",
      claim_type: "fact",
      description: "Runs in-process.",
      benefits: ["low deployment overhead"],
      costs: [],
      evidence_ids: ["architecture", "source"],
    },
  );

  assert.deepEqual(
    serializeMathematicalView({
      id: 1,
      model: "state machine",
      question: "How does execution transition?",
      assumptions_json: '["single process"]',
      claim_type: "inference",
      evidence_ids_json: '["architecture"]',
    }),
    {
      id: 1,
      model: "state machine",
      question: "How does execution transition?",
      assumptions: ["single process"],
      claim_type: "inference",
      evidence_ids: ["architecture"],
    },
  );
});

test("buildCompositions filters valid proposals by input and status", () => {
  const result = buildCompositions(
    [
      {
        id: "candidate",
        name: "Candidate",
        version_context: "v1",
        composition_json: JSON.stringify({
          inputs: [{ system_id: "alpha", role: "storage" }],
          constraints: [],
          preserved_properties: [],
          conflicts: [],
          claim_status: "under-review",
          evidence_ids: ["architecture-doc"],
        }),
      },
      {
        id: "malformed",
        name: "Malformed",
        version_context: null,
        composition_json: JSON.stringify({
          inputs: [],
          claim_status: "accepted",
        }),
      },
      {
        id: "invalid-json",
        name: "Invalid JSON",
        version_context: null,
        composition_json: "not-json",
      },
    ],
    "alpha",
    "under-review",
  );

  assert.deepEqual(result, [
    {
      system_id: "candidate",
      system_name: "Candidate",
      version_context: "v1",
      composition: {
        inputs: [{ system_id: "alpha", role: "storage" }],
        constraints: [],
        preserved_properties: [],
        conflicts: [],
        claim_status: "under-review",
        evidence_ids: ["architecture-doc"],
      },
      evidence: [],
    },
  ]);
});

test("buildCompositions resolves only cited evidence metadata", () => {
  const evidence = {
    id: "architecture-doc",
    kind: "official-doc",
    title: "Architecture documentation",
    uri: "https://example.test/architecture",
    accessed: "2026-01-01",
    notes: "Relevant boundary.",
  };
  const result = buildCompositions([
    {
      id: "candidate",
      name: "Candidate",
      version_context: null,
      composition_json: JSON.stringify({
        inputs: [{ system_id: "alpha" }],
        constraints: [],
        preserved_properties: [],
        conflicts: [],
        claim_status: "accepted",
        evidence_ids: ["architecture-doc", "missing"],
      }),
      evidence_json: JSON.stringify([evidence]),
    },
  ]);

  assert.deepEqual(result[0]?.evidence, [evidence]);
});

test("buildGraph exposes typed relations and preserves legacy related-system edges", () => {
  const graph = buildGraph([
    {
      id: "alpha",
      name: "Alpha",
      related_systems_json: JSON.stringify(["beta", "missing"]),
      relations_json: JSON.stringify([
        {
          type: "extends",
          target: "beta",
          claim_type: "inference",
          claim_status: "under-review",
          evidence_ids: ["architecture-doc"],
          notes: "The extension boundary is still being reviewed.",
        },
        { type: "uses", target: "missing", claim_type: "fact" },
      ]),
    },
    {
      id: "beta",
      name: "Beta",
      related_systems_json: "[]",
      relations_json: "[]",
    },
  ]);

  assert.deepEqual(graph.nodes, [
    { id: "alpha", name: "Alpha", type: "system" },
    { id: "beta", name: "Beta", type: "system" },
  ]);
  assert.deepEqual(graph.edges, [
    {
      source: "alpha",
      target: "beta",
      type: "extends",
      claim_type: "inference",
      claim_status: "under-review",
      evidence_ids: ["architecture-doc"],
      notes: "The extension boundary is still being reviewed.",
    },
    { source: "alpha", target: "beta", type: "related" },
  ]);
});

test("buildGraph ignores malformed and unknown graph targets", () => {
  const graph = buildGraph([
    {
      id: "alpha",
      name: "Alpha",
      related_systems_json: JSON.stringify(["beta", 42]),
      relations_json: JSON.stringify([
        { type: "uses", target: "beta" },
        { type: "uses", target: "missing" },
        { type: "uses" },
        null,
      ]),
    },
    {
      id: "beta",
      name: "Beta",
      related_systems_json: "invalid json",
      relations_json: "{}",
    },
  ]);

  assert.deepEqual(graph.edges, [
    { source: "alpha", target: "beta", type: "uses" },
    { source: "alpha", target: "beta", type: "related" },
  ]);
});

function systemRow(index: number) {
  const id = `system-${String(index).padStart(3, "0")}`;
  return {
    id,
    name: `System ${String(index).padStart(3, "0")}`,
    version_context: null,
    temporal_context_json: null,
    relations_json: "[]",
    composition_json: null,
    summary: `Summary for ${id}`,
    scope_json: "[]",
    related_systems_json: "[]",
    source_path: `data/systems/${id}.json`,
  };
}

function mockSystemsDatabase(
  rows: ReturnType<typeof systemRow>[],
  calls: { sql: string; bindings: unknown[] }[],
) {
  return {
    prepare(sql: string) {
      return {
        bind(...bindings: unknown[]) {
          calls.push({ sql, bindings });
          return {
            all<T>() {
              const limit = Number(bindings[2]);
              const offset = Number(bindings[3]);
              return Promise.resolve({
                results: rows.slice(offset, offset + limit) as T[],
                success: true,
                meta: {},
              });
            },
          };
        },
      };
    },
  } as unknown as D1Database;
}

import assert from "node:assert/strict";
import { test } from "node:test";
import { type ModelGraph, modelViewKey } from "./model-graph.js";
import {
  app,
  artifactKey,
  buildCompositions,
  buildGraph,
  serializeFeature,
  serializeFeatureRelation,
  serializeMathematicalView,
} from "./index.js";

test("D1-backed routes require Turnstile access when protection is configured", async () => {
  const response = await app.request(
    "/api/systems",
    {},
    {
      DB: {} as D1Database,
      APP_ENV: "production",
      ASSETS: {} as Fetcher,
      TURNSTILE_SECRET_KEY: "secret",
      TURNSTILE_SITE_KEY: "site",
    },
  );

  assert.equal(response.status, 403);
  assert.deepEqual(await response.json(), {
    error: "Turnstile access verification required",
    code: "access_required",
  });
});

test("configured API service token bypasses browser access sessions", async () => {
  const calls: { sql: string; bindings: unknown[] }[] = [];
  const response = await app.request(
    "/api/systems?limit=1",
    { headers: { Authorization: "Bearer service-token" } },
    {
      DB: mockSystemsDatabase([systemRow(0)], calls),
      APP_ENV: "production",
      ASSETS: {} as Fetcher,
      TURNSTILE_SECRET_KEY: "secret",
      TURNSTILE_SITE_KEY: "site",
      API_ACCESS_TOKEN: "service-token",
    },
  );

  assert.equal(response.status, 200);
  assert.equal(calls.length, 1);
});

test("service-token auth normalizes surrounding header whitespace", async () => {
  const calls: { sql: string; bindings: unknown[] }[] = [];
  const response = await app.request(
    "/api/systems?limit=1",
    { headers: { Authorization: " Bearer service-token " } },
    {
      DB: mockSystemsDatabase([systemRow(0)], calls),
      APP_ENV: "production",
      ASSETS: {} as Fetcher,
      TURNSTILE_SECRET_KEY: "secret",
      TURNSTILE_SITE_KEY: "site",
      API_ACCESS_TOKEN: "service-token",
    },
  );

  assert.equal(response.status, 200);
  assert.equal(calls.length, 1);
});

test("hosted MCP requires its bearer token and stays read-only", async () => {
  const env = {
    DB: {} as D1Database,
    APP_ENV: "production",
    ASSETS: {} as Fetcher,
    API_ACCESS_TOKEN: "service-token",
  };

  const unauthorized = await app.request(
    "/api/mcp",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
    },
    env,
  );
  assert.equal(unauthorized.status, 401);

  const wrongMethod = await app.request(
    "/api/mcp",
    { method: "GET", headers: { Authorization: "Bearer service-token" } },
    env,
  );
  assert.equal(wrongMethod.status, 405);
  assert.equal(wrongMethod.headers.get("allow"), "POST");

  const authorized = await app.request(
    "/api/mcp",
    {
      method: "POST",
      headers: {
        Authorization: " Bearer service-token ",
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
    },
    env,
  );
  assert.equal(authorized.status, 200);
  const body = (await authorized.json()) as { jsonrpc: string };
  assert.equal(body.jsonrpc, "2.0");
});

test("artifact route rejects traversal before accessing R2", async () => {
  assert.equal(artifactKey("/api/artifacts/%2e%2e/secret.json"), undefined);
  assert.equal(artifactKey("/api/artifacts/%5c/secret.json"), undefined);
  assert.equal(artifactKey("/api/artifacts/reports/v1.json"), "reports/v1.json");

  let requestedKey: string | undefined;
  const env = {
    DB: {} as D1Database,
    APP_ENV: "test",
    ASSETS: {} as Fetcher,
    ARTIFACTS: {
      get() {
        requestedKey = arguments[0] as string;
        return Promise.resolve(null);
      },
    } as unknown as R2Bucket,
  };

  const response = await app.request("/api/artifacts/reports/v1.json", {}, env);
  assert.equal(response.status, 404);
  assert.equal(requestedKey, "reports/v1.json");
});

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

test("serializes feature relation evidence and optional notes", () => {
  assert.deepEqual(
    serializeFeatureRelation({
      id: 1,
      source_system_id: "alpha",
      source_feature_id: "embedded",
      target_system_id: "beta",
      target_feature_id: "embedded",
      type: "resembles",
      claim_type: "analogy",
      claim_status: "proposed",
      notes: "Bounded comparison.",
      evidence_ids_json: '["architecture"]',
    }),
    {
      source_feature_id: "embedded",
      target_system_id: "beta",
      target_feature_id: "embedded",
      type: "resembles",
      claim_type: "analogy",
      claim_status: "proposed",
      evidence_ids: ["architecture"],
      notes: "Bounded comparison.",
    },
  );
});

test("GET /api/feature-relations returns bounded, filtered relation rows", async () => {
  const calls: { sql: string; bindings: unknown[] }[] = [];
  const db = {
    prepare(sql: string) {
      return {
        bind(...bindings: unknown[]) {
          calls.push({ sql, bindings });
          return {
            all<T>() {
              return Promise.resolve({
                results: [
                  {
                    id: 1,
                    source_system_id: "alpha",
                    source_feature_id: "embedded",
                    target_system_id: "beta",
                    target_feature_id: "embedded",
                    type: "resembles",
                    claim_type: "analogy",
                    claim_status: "proposed",
                    notes: null,
                    evidence_ids_json: '["architecture"]',
                  },
                ] as T[],
              });
            },
          };
        },
      };
    },
  } as unknown as D1Database;

  const response = await app.request(
    "/api/feature-relations?system_id=alpha&type=resembles&limit=999",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );

  assert.equal(response.status, 200);
  assert.deepEqual(await response.json(), {
    data: [
      {
        source_system_id: "alpha",
        source_feature_id: "embedded",
        target_system_id: "beta",
        target_feature_id: "embedded",
        type: "resembles",
        claim_type: "analogy",
        claim_status: "proposed",
        evidence_ids: ["architecture"],
      },
    ],
  });
  assert.deepEqual(calls[0]?.bindings, ["alpha", "resembles", 200]);
  assert.match(calls[0]?.sql ?? "", /ORDER BY fr\.source_system_id/);
  assert.match(calls[0]?.sql ?? "", /LIMIT \?3/);
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

test("GET /api/graph/models projects reviewed mathematical views", async () => {
  const queries: string[] = [];
  const db = {
    prepare(sql: string) {
      queries.push(sql);
      return {
        all<T>() {
          return Promise.resolve({
            results: [
              {
                system_id: "temporal",
                system_name: "Temporal",
                view_id: 7,
                model: "Queue-mediated workflow state machine",
                question: "How does work move?",
                assumptions_json: '["workers poll"]',
                claim_type: "inference",
                evidence_ids_json: '["temporal-task-queues"]',
              },
              {
                system_id: "other",
                system_name: "Other",
                view_id: 8,
                model: "Queue-mediated workflow state machine",
                question: "How does work move elsewhere?",
                assumptions_json: "[]",
                claim_type: "hypothesis",
                evidence_ids_json: '["other-source"]',
              },
              {
                system_id: "temporal",
                system_name: "Temporal",
                view_id: 9,
                model: "Replay state machine",
                question: "Does replay preserve state?",
                assumptions_json: "[]",
                claim_type: "analogy",
                evidence_ids_json: '["temporal-replay"]',
              },
            ] as T[],
            success: true,
            meta: {},
          });
        },
      };
    },
  } as unknown as D1Database;

  const response = await app.request(
    "/api/graph/models",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );

  assert.equal(response.status, 200);
  const body = (await response.json()) as { data: ModelGraph };
  assert.deepEqual(Object.keys(body), ["data"]);
  assert.match(
    queries[0]!,
    /substr\(mve\.evidence_id, length\(mathematical_views\.system_id\) \+ 2\)/,
  );
  assert.match(queries[0]!, /WHERE mve\.view_id = mathematical_views\.id/);
  assert.equal(
    body.data.nodes.some((node) => node.id === "model:state-transition-systems"),
    true,
  );
  assert.equal(body.data.edges.length, 2);
  const temporalEdge = body.data.edges.find((edge) => edge.metadata.some((view) => view.id === 7));
  assert.equal(temporalEdge?.claim_type, "mixed");
  assert.equal(body.data.edges.find((edge) => edge.source === "other")?.claim_type, "hypothesis");
  assert.deepEqual(
    temporalEdge?.metadata.find((view) => view.id === 7),
    {
      id: 7,
      key: modelViewKey("temporal", "Queue-mediated workflow state machine", "How does work move?"),
      model: "Queue-mediated workflow state machine",
      question: "How does work move?",
      assumptions: ["workers poll"],
      claim_type: "inference",
      evidence_ids: ["temporal-task-queues"],
    },
  );
});

test("system detail view keys match graph identity across database ids", async () => {
  const view = {
    id: 42,
    model: "Snapshot visibility relation",
    question: "Which snapshots are visible?",
    assumptions_json: '["committed writes"]',
    claim_type: "hypothesis",
    evidence_ids_json: '["architecture"]',
  };
  const system = systemRow(0);
  const db = {
    prepare(sql: string) {
      return {
        bind() {
          return {
            first() {
              return Promise.resolve(system);
            },
            all() {
              return Promise.resolve({
                results: sql.includes("FROM mathematical_views WHERE") ? [view] : [],
              });
            },
          };
        },
      };
    },
  } as unknown as D1Database;
  const response = await app.request(
    `/api/systems/${system.id}`,
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );
  assert.equal(response.status, 200);
  const body = (await response.json()) as {
    data: {
      mathematical_views: Array<{
        id: number;
        key: string;
        claim_type: string;
        evidence_ids: string[];
      }>;
      feature_relations: unknown[];
    };
  };
  assert.equal(body.data.mathematical_views[0]?.id, 42);
  assert.equal(
    body.data.mathematical_views[0]?.key,
    modelViewKey(system.id, view.model, view.question),
  );
  assert.equal(body.data.mathematical_views[0]?.claim_type, "hypothesis");
  assert.deepEqual(body.data.mathematical_views[0]?.evidence_ids, ["architecture"]);
  assert.deepEqual(body.data.feature_relations, []);
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

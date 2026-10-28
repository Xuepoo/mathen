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
  serializeEvidence,
} from "./index.js";
import { verifyOidcAccessToken } from "./access.js";

function base64Url(value: string | Uint8Array) {
  const bytes = typeof value === "string" ? new TextEncoder().encode(value) : value;
  let binary = "";
  for (const byte of bytes) binary += String.fromCharCode(byte);
  return btoa(binary).replaceAll("+", "-").replaceAll("/", "_").replace(/=+$/, "");
}

async function syntheticOidcToken() {
  const pair = await crypto.subtle.generateKey(
    {
      name: "RSASSA-PKCS1-v1_5",
      modulusLength: 2048,
      publicExponent: new Uint8Array([1, 0, 1]),
      hash: "SHA-256",
    },
    true,
    ["sign", "verify"],
  );
  const jwk = await crypto.subtle.exportKey("jwk", pair.publicKey);
  jwk.kid = "ordinary-route-regression";
  jwk.alg = "RS256";
  jwk.use = "sig";
  const claims = {
    iss: "https://tenant.example.test/",
    aud: "https://mathen.example.test/api",
    exp: 1_800_000_100,
    nbf: 1_700_000_000,
    scope: "read:cards",
  };
  const header = base64Url(JSON.stringify({ alg: "RS256", typ: "JWT", kid: jwk.kid }));
  const payload = base64Url(JSON.stringify(claims));
  const input = `${header}.${payload}`;
  const signature = await crypto.subtle.sign(
    "RSASSA-PKCS1-v1_5",
    pair.privateKey,
    new TextEncoder().encode(input),
  );
  return {
    token: `${input}.${base64Url(new Uint8Array(signature))}`,
    fetcher: async () => Response.json({ keys: [jwk] }),
  };
}

test("hosted MCP uses the /api prefix on any deployment origin", async () => {
  for (const origin of ["https://preview.example.test", "http://localhost:8787"]) {
    const response = await app.request(
      `${origin}/api/mcp`,
      { method: "POST" },
      {
        DB: {} as D1Database,
        APP_ENV: "test",
        ASSETS: {} as Fetcher,
        API_ACCESS_TOKEN: "test-token",
      },
    );
    assert.equal(response.status, 401);
    assert.deepEqual(await response.json(), {
      error: "MCP bearer authentication required",
      code: "unauthorized",
    });
  }
});

test("hosted MCP exposes OAuth protected-resource metadata and a standard challenge", async () => {
  const env = {
    DB: {} as D1Database,
    APP_ENV: "production",
    ASSETS: {} as Fetcher,
    AUTH0_ISSUER: "https://tenant.example.test/",
    AUTH0_AUDIENCE: "https://mathen.example.test/api",
    AUTH0_JWKS_URI: "https://tenant.example.test/.well-known/jwks.json",
    AUTH0_REQUIRED_SCOPE: "read:cards",
    TURNSTILE_SECRET_KEY: "secret",
    TURNSTILE_SITE_KEY: "site",
  };
  const metadata = await app.request(
    "https://example.test/api/.well-known/oauth-protected-resource",
    {},
    env,
  );
  assert.equal(metadata.status, 200);
  assert.deepEqual(await metadata.json(), {
    resource: "https://example.test/api/mcp",
    bearer_methods_supported: ["header"],
    authorization_servers: ["https://tenant.example.test/"],
    scopes_supported: ["read:cards"],
  });
  const metadataAlias = await app.request(
    "https://example.test/api/.well-known/oauth-protected-resource/mcp",
    {},
    env,
  );
  assert.equal(metadataAlias.status, 200);
  assert.deepEqual(await metadataAlias.json(), {
    resource: "https://example.test/api/mcp",
    bearer_methods_supported: ["header"],
    authorization_servers: ["https://tenant.example.test/"],
    scopes_supported: ["read:cards"],
  });
  const unauthorized = await app.request(
    "https://example.test/api/mcp",
    { method: "POST", headers: { Authorization: "Bearer malformed" } },
    env,
  );
  assert.equal(unauthorized.status, 401);
  assert.equal(
    unauthorized.headers.get("www-authenticate"),
    'Bearer realm="mathen-mcp", resource_metadata="https://example.test/api/.well-known/oauth-protected-resource", error="invalid_token", scope="read:cards"',
  );
});

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

test("a valid MCP OIDC token cannot bypass Turnstile on ordinary API routes", async () => {
  const fixture = await syntheticOidcToken();
  const env = {
    DB: {} as D1Database,
    APP_ENV: "production",
    ASSETS: {} as Fetcher,
    TURNSTILE_SECRET_KEY: "secret",
    TURNSTILE_SITE_KEY: "site",
    AUTH0_ISSUER: "https://tenant.example.test/",
    AUTH0_AUDIENCE: "https://mathen.example.test/api",
    AUTH0_JWKS_URI: "https://tenant.example.test/.well-known/jwks.json",
    AUTH0_REQUIRED_SCOPE: "read:cards",
  };
  assert.equal(
    await verifyOidcAccessToken(fixture.token, env, fixture.fetcher, 1_700_000_001_000),
    true,
  );
  const response = await app.request(
    "/api/systems",
    { headers: { Authorization: `Bearer ${fixture.token}` } },
    env,
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
  assert.match(authorized.headers.get("x-request-id") ?? "", /^[0-9a-f-]{36}$/);
});

test("hosted MCP applies configured origin and request limits", async () => {
  const env = {
    DB: {} as D1Database,
    APP_ENV: "production",
    ASSETS: {} as Fetcher,
    API_ACCESS_TOKEN: "service-token",
    MCP_ALLOWED_ORIGINS: "https://client.example",
    MCP_RATE_LIMIT_PER_MINUTE: "1",
  };
  const request = (origin: string, ip: string) =>
    app.request(
      "/api/mcp",
      {
        method: "POST",
        headers: {
          Authorization: "Bearer service-token",
          Origin: origin,
          "CF-Connecting-IP": ip,
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ jsonrpc: "2.0", id: 1, method: "tools/list" }),
      },
      env,
    );

  const allowed = await request("https://client.example", "mcp-test-limit");
  assert.equal(allowed.status, 200);
  assert.equal(allowed.headers.get("access-control-allow-origin"), "https://client.example");
  const limited = await request("https://client.example", "mcp-test-limit");
  assert.equal(limited.status, 429);
  assert.equal(limited.headers.get("retry-after"), "60");
  const denied = await request("https://other.example", "mcp-test-origin");
  assert.equal(denied.status, 403);
  assert.deepEqual(await denied.json(), {
    error: "MCP origin is not allowed",
    code: "origin_denied",
  });
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

test("serializes scoped lifecycle, view-contract, and observation evidence metadata", () => {
  const scopeContext = { workload: { status: "specified" } };
  const lifecycle = { status: "observed", evidence_ids: ["architecture"] };
  assert.deepEqual(
    serializeFeature({
      id: "embedded",
      name: "Embedded execution",
      category: "execution-model",
      claim_type: "fact",
      description: "Runs in-process.",
      benefits_json: "[]",
      costs_json: "[]",
      evidence_ids_json: '["architecture"]',
      metadata_json: JSON.stringify({ lifecycle, scope_context: scopeContext }),
    }),
    {
      id: "embedded",
      name: "Embedded execution",
      category: "execution-model",
      claim_type: "fact",
      description: "Runs in-process.",
      benefits: [],
      costs: [],
      evidence_ids: ["architecture"],
      lifecycle,
      scope_context: scopeContext,
      metadata: { lifecycle, scope_context: scopeContext },
    },
  );
  const contract = { validation_records: [{ id: "validation-1" }] };
  assert.deepEqual(
    serializeMathematicalView({
      id: 1,
      model: "state machine",
      question: "How?",
      assumptions_json: "[]",
      claim_type: "inference",
      evidence_ids_json: '["architecture"]',
      metadata_json: JSON.stringify({ lifecycle, scope_context: scopeContext, contract }),
    }),
    {
      id: 1,
      model: "state machine",
      question: "How?",
      assumptions: [],
      claim_type: "inference",
      evidence_ids: ["architecture"],
      metadata: { lifecycle, scope_context: scopeContext, contract },
      lifecycle,
      scope_context: scopeContext,
      contract,
    },
  );
  assert.deepEqual(
    serializeEvidence({
      id: "architecture",
      kind: "benchmark",
      title: "Observed run",
      uri: "https://example.test/run",
      accessed: null,
      notes: null,
      scope_context_json: JSON.stringify(scopeContext),
      metadata_json: JSON.stringify({ observation_version: "1", result: { status: "observed" } }),
    }),
    {
      id: "architecture",
      kind: "benchmark",
      title: "Observed run",
      uri: "https://example.test/run",
      accessed: null,
      notes: null,
      scope_context: scopeContext,
      metadata: { observation_version: "1", result: { status: "observed" } },
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
                metadata_json: JSON.stringify({
                  claim_status: "under-review",
                  validity_scope: { versions: ["1.0"] },
                  contract: { schema_version: "1.0", family: "state_machine" },
                }),
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
      claim_status: "under-review",
      validity_scope: { versions: ["1.0"] },
      contract: { schema_version: "1.0", family: "state_machine" },
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

test("GET /api/graph/layers preserves D1 document and view metadata", async () => {
  const document = {
    id: "loop",
    name: "Loop",
    claim_type: "inference",
    claim_status: "accepted",
    validity_scope: { deployment_origins: ["local"] },
    operations: [{ id: "repeat" }],
  };
  const db = {
    prepare(sql: string) {
      return {
        all<T>() {
          if (sql.includes("FROM graph_documents"))
            return Promise.resolve({
              results: [
                {
                  id: "loop",
                  kind: "microstructure",
                  name: "Loop",
                  document_json: JSON.stringify(document),
                },
              ] as T[],
            });
          return Promise.resolve({
            results: [
              {
                id: "alpha",
                name: "Alpha",
                scope_json: "[]",
                relations_json: JSON.stringify([
                  {
                    target: "beta",
                    type: "uses",
                    claim_type: "fact",
                    claim_status: "proposed",
                    evidence_ids: ["alpha-doc"],
                    notes: "Explicit relation.",
                    validity_scope: { deployment_origins: ["local"] },
                  },
                ]),
                composition_json: null,
                features_json: JSON.stringify([
                  {
                    id: "state",
                    name: "State",
                    category: "behavior",
                    claim_type: "fact",
                    description: "State",
                    evidence_ids: [],
                    metadata_json: JSON.stringify({ claim_status: "accepted" }),
                  },
                ]),
                views_json: JSON.stringify([
                  {
                    id: 1,
                    model: "State machine",
                    question: "How?",
                    assumptions: [],
                    claim_type: "inference",
                    evidence_ids: [],
                    metadata_json: JSON.stringify({
                      id: "stable-view",
                      claim_status: "under-review",
                      contract: { family: "state_machine" },
                    }),
                  },
                ]),
              },
              {
                id: "beta",
                name: "Beta",
                scope_json: "[]",
                relations_json: "[]",
                composition_json: null,
                features_json: "[]",
                views_json: "[]",
              },
            ] as T[],
          });
        },
      };
    },
  } as unknown as D1Database;
  const response = await app.request(
    "/api/graph/layers?origin=local",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );
  assert.equal(response.status, 200);
  const body = (await response.json()) as {
    data: {
      nodes: Array<{ id: string; metadata: Record<string, unknown> }>;
      edges: Array<Record<string, unknown>>;
    };
  };
  assert.deepEqual(Object.keys(body), ["data"]);
  assert.deepEqual(
    body.data.nodes.find((node) => node.id === "microstructure:loop")?.metadata.payload,
    document,
  );
  assert.equal(
    body.data.nodes.find((node) => node.id === "property:alpha:state")?.metadata.claim_status,
    "accepted",
  );
  assert.deepEqual(
    body.data.nodes.find((node) => node.id === "math:alpha:stable-view")?.metadata.contract,
    { family: "state_machine" },
  );
  assert.deepEqual(
    body.data.edges.find((edge) => edge.type === "uses"),
    {
      source: "system:alpha",
      target: "system:beta",
      type: "uses",
      claim_type: "fact",
      claim_status: "proposed",
      evidence_ids: ["alpha-doc"],
      notes: "Explicit relation.",
      metadata: { validity_scope: { deployment_origins: ["local"] } },
    },
  );
});

test("GET /api/retrieval returns a reviewed-only envelope and request ID", async () => {
  const db = {
    prepare(sql: string) {
      return {
        all<T>() {
          let results: unknown[] = [];
          if (sql.includes("FROM systems")) {
            results = [
              {
                id: "alpha",
                name: "Alpha",
                version_context: "1.0",
                summary: "Embedded execution",
                scope_json: '["execution"]',
                temporal_context_json: null,
                relations_json: "[]",
                composition_json: null,
                source_path: "data/systems/alpha.json",
              },
            ];
          } else if (sql.includes("FROM features")) {
            results = [
              {
                id: "embedded",
                system_id: "alpha",
                system_name: "Alpha",
                name: "Embedded execution",
                category: "deployment",
                claim_type: "fact",
                description: "Runs in the host process.",
                benefits_json: "[]",
                costs_json: "[]",
                metadata_json: '{"claim_status":"accepted"}',
                evidence_ids_json: '["architecture"]',
              },
            ];
          } else if (sql.includes("FROM evidence")) {
            results = [
              {
                id: "architecture",
                system_id: "alpha",
                kind: "official-doc",
                title: "Architecture",
                uri: "https://example.test/architecture",
                accessed: null,
                notes: null,
              },
            ];
          }
          return Promise.resolve({ results: results as T[] });
        },
      };
    },
  } as unknown as D1Database;

  const response = await app.request(
    "/api/retrieval?q=embedded+execution&record_kind=feature",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );
  assert.equal(response.status, 200);
  assert.match(response.headers.get("x-request-id") ?? "", /^[0-9a-f-]{36}$/);
  const body = (await response.json()) as {
    data: {
      index: { method: string; corpus: string };
      results: Array<{ document: { id: string } }>;
    };
  };
  assert.deepEqual(Object.keys(body), ["data"]);
  assert.equal(body.data.index.method, "bounded_lexical_baseline");
  assert.equal(body.data.index.corpus, "canonical_cards");
  assert.deepEqual(
    body.data.results.map((result) => result.document.id),
    ["system:alpha:feature:embedded"],
  );
});

test("GET /api/retrieval rejects malformed requests and reports unavailable D1", async () => {
  const invalid = await app.request(
    "/api/retrieval?q=x&limit=0",
    {},
    { DB: {} as D1Database, APP_ENV: "test", ASSETS: {} as Fetcher },
  );
  assert.equal(invalid.status, 400);
  assert.equal(((await invalid.json()) as { code: string }).code, "invalid_request");

  const unavailable = await app.request(
    "/api/retrieval?q=x",
    {},
    {
      DB: {
        prepare() {
          throw new Error("D1 unavailable");
        },
      } as unknown as D1Database,
      APP_ENV: "test",
      ASSETS: {} as Fetcher,
    },
  );
  assert.equal(unavailable.status, 503);
  assert.equal(((await unavailable.json()) as { code: string }).code, "semantic_index_unavailable");
  assert.match(unavailable.headers.get("x-request-id") ?? "", /^[0-9a-f-]{36}$/);
});

test("GET /api/retrieval distinguishes an empty verified corpus", async () => {
  const db = {
    prepare() {
      return {
        all<T>() {
          return Promise.resolve({ results: [] as T[] });
        },
      };
    },
  } as unknown as D1Database;
  const response = await app.request(
    "/api/retrieval?q=anything",
    {},
    { DB: db, APP_ENV: "test", ASSETS: {} as Fetcher },
  );
  assert.equal(response.status, 200);
  const body = (await response.json()) as {
    data: { index: { status: string }; results: unknown[]; warnings: string[] };
  };
  assert.equal(body.data.index.status, "empty");
  assert.deepEqual(body.data.results, []);
  assert.deepEqual(body.data.warnings, ["empty_index"]);
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

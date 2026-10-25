import assert from "node:assert/strict";
import { test } from "node:test";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { ApiBackend, FilesystemBackend } from "./backend";
import { registerRetrievalTool } from "./retrieval-tool";
import { normalizeRetrieval, retrievalParams } from "./retrieval-contract";
import { createMcpApiBackend, handleMcpRequest } from "../../api/src/mcp";

export function retrievalFixture() {
  return {
    schema_version: "1.0",
    query: { q_digest: "sha256:query", filters: { deployment_origin: "local" } },
    index: {
      status: "ready",
      index_id: "canonical-cards-d1-lexical-v1",
      corpus: "canonical_cards",
      representation_version: "canonical-record-v1",
      method: "bounded_lexical_baseline",
      warnings: ["Scores are uncalibrated discovery ranking signals, not semantic proof."],
    },
    results: [
      {
        rank: 1,
        score: 0.75,
        score_kind: "lexical_overlap",
        document: {
          id: "system:alpha:feature:embedded",
          record_kind: "feature",
          system_id: "alpha",
          feature_id: "embedded",
          name: "Embedded execution",
          description: "Runs in process.",
          claim_type: "hypothesis",
          claim_status: "under-review",
          version_context: "1.0",
          evidence_ids: ["architecture"],
          validity_scope: { deployment_origins: ["local"], conditions: ["one process"] },
        },
        evidence: [
          {
            id: "architecture",
            title: "Architecture",
            kind: "doc",
            uri: "https://example.test/doc",
            notes: "Primary source",
          },
        ],
        provenance: {
          source_ref: "data/systems/alpha.json#features/embedded",
          source_digest: "sha256:source",
          retrieval_method: "bounded_lexical_baseline",
        },
      },
    ],
    warnings: ["stale_source_ref"],
  };
}

test("retrieval contract preserves all source metadata without promoting claims", () => {
  const fixture = retrievalFixture();
  assert.deepEqual(normalizeRetrieval(fixture, 10), fixture);
  for (const mutate of [
    (value: ReturnType<typeof retrievalFixture>) => {
      value.index.corpus = "drafts";
    },
    (value: ReturnType<typeof retrievalFixture>) => {
      value.results[0].provenance.source_ref = "data/drafts/alpha.json";
    },
    (value: ReturnType<typeof retrievalFixture>) => {
      value.results[0].evidence = [];
    },
    (value: ReturnType<typeof retrievalFixture>) => {
      value.results[0].score = NaN;
    },
  ]) {
    const invalid = retrievalFixture();
    mutate(invalid);
    assert.throws(() => normalizeRetrieval(invalid, 10), /Invalid retrieval response/);
  }
  assert.throws(() =>
    normalizeRetrieval({ ...fixture, results: Array(11).fill(fixture.results[0]) }, 10),
  );
});

test("retrieval arguments are bounded, allowlisted, encoded, and exclude drafts", () => {
  const params = retrievalParams({
    q: "  state & queues  ",
    limit: 2,
    record_kind: "feature,view",
    system_id: "alpha",
    feature_id: "embedded",
    category: "deployment",
    claim_type: "hypothesis",
    claim_status: "under-review",
    version_context: "1.0",
    deployment_origin: "local",
  });
  assert.equal(params.get("q"), "state & queues");
  assert.equal(params.get("record_kind"), "feature,view");
  for (const args of [
    { q: " " },
    { q: "x", limit: 51 },
    { q: "x", include_drafts: true },
    { q: "x", record_kind: "draft" },
    { q: "x", deployment_origin: "bad value" },
  ]) {
    assert.throws(() => retrievalParams(args));
  }
});

test("normalization preserves all four claim types and deterministic API rank order", () => {
  const value = retrievalFixture();
  value.results = ["fact", "inference", "hypothesis", "analogy"].map((claim_type, index) => ({
    ...value.results[0],
    rank: index + 1,
    document: { ...value.results[0].document, id: `system:alpha:feature:${index}`, claim_type },
  }));
  assert.deepEqual(normalizeRetrieval(value), value);
  value.results[1].rank = 1;
  assert.throws(() => normalizeRetrieval(value), /Invalid retrieval response/);
});

test("API backend forwards every retrieval filter and Bearer token without altering results", async () => {
  let requestUrl = "";
  let authorization = "";
  const backend = new ApiBackend(
    "https://user:password@api.example.test/api",
    async (input, init) => {
      requestUrl = String(input);
      authorization = new Headers(init?.headers).get("authorization") ?? "";
      return Response.json({ data: retrievalFixture() });
    },
    10000,
    "service-secret",
  );
  const args = {
    q: "state & queues",
    limit: 2,
    record_kind: "feature,view",
    system_id: "alpha",
    feature_id: "embedded",
    category: "deployment",
    claim_type: "hypothesis",
    claim_status: "under-review",
    version_context: "1.0",
    deployment_origin: "local",
  };
  assert.deepEqual(await backend.searchRetrieval(args), retrievalFixture());
  assert.equal(new URL(requestUrl).pathname, "/api/retrieval");
  assert.deepEqual([...new URL(requestUrl).searchParams], [...retrievalParams(args)]);
  assert.ok(!requestUrl.includes("password"));
  assert.equal(authorization, "Bearer service-secret");
});

test("ready no-results and empty corpus are successful, filesystem retrieval is explicitly unavailable", async () => {
  for (const status of ["ready", "empty"]) {
    const value = {
      ...retrievalFixture(),
      index: { ...retrievalFixture().index, status },
      results: [],
    };
    assert.deepEqual(
      await new ApiBackend("https://api.example.test", async () =>
        Response.json({ data: value }),
      ).searchRetrieval({ q: "absent" }),
      value,
    );
  }
  await assert.rejects(
    new FilesystemBackend("/not-read").searchRetrieval({ q: "state" }),
    /no verified local retrieval index/,
  );
});

test("retrieval failures never expose query, credentials, or upstream response bodies", async () => {
  for (const fetcher of [
    async () => new Response("provider-secret", { status: 503 }),
    async () => {
      throw new Error("provider-secret");
    },
    async () => Response.json({ error: "provider-secret" }),
  ]) {
    const backend = new ApiBackend(
      "https://user:password@api.example.test",
      fetcher,
      10000,
      "service-secret",
    );
    try {
      await backend.searchRetrieval({ q: "private-query" });
      throw new Error("Expected failure");
    } catch (error) {
      assert.doesNotMatch(String(error), /private-query|password|provider-secret|service-secret/);
      assert.match(String(error), /retrieval|Retrieval/);
    }
  }
});

test("API retrieval timeout omits private queries and configuration credentials", async () => {
  const backend = new ApiBackend(
    "https://user:password@api.example.test",
    async (_input, init) =>
      new Promise<Response>((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("provider-secret", "AbortError")),
        );
      }),
    5,
    "service-secret",
  );
  await assert.rejects(backend.searchRetrieval({ q: "private-query" }), (error) => {
    assert.doesNotMatch(String(error), /private-query|password|provider-secret|service-secret/);
    assert.match(String(error), /Retrieval request failed/);
    return true;
  });
});

test("stdio tool is strict, read-only, and returns the same data as hosted MCP", async () => {
  const fixture = retrievalFixture();
  const backend = new ApiBackend("https://api.example.test", async () =>
    Response.json({ data: fixture }),
  );
  const server = new McpServer({ name: "test", version: "1" });
  registerRetrievalTool(server, backend);
  const client = new Client({ name: "test", version: "1" });
  const [clientTransport, serverTransport] = InMemoryTransport.createLinkedPair();
  await Promise.all([server.connect(serverTransport), client.connect(clientTransport)]);
  try {
    const { tools } = await client.listTools();
    const tool = tools[0];
    assert.equal(tool.name, "search_semantic");
    assert.equal(tool.inputSchema.additionalProperties, false);
    assert.equal(tool.annotations?.readOnlyHint, true);
    assert.match(tool.description ?? "", /bounded lexical baseline/);
    assert.match(tool.description ?? "", /uncalibrated/);
    assert.match(tool.description ?? "", /originality/);
    const hostedTools = await handleMcpRequest(
      new Request("https://example.test/api/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ jsonrpc: "2.0", id: 2, method: "tools/list" }),
      }),
      createMcpApiBackend(async () => fixture),
    );
    const hostedTool = (
      (await hostedTools.json()) as { result: { tools: typeof tools } }
    ).result.tools.find((item) => item.name === "search_semantic");
    assert.equal(hostedTool?.inputSchema.additionalProperties, false);
    assert.deepEqual(
      Object.keys(tool.inputSchema.properties ?? {}).sort(),
      Object.keys(hostedTool?.inputSchema.properties ?? {}).sort(),
    );
    assert.ok(!Object.hasOwn(tool.inputSchema.properties ?? {}, "include_drafts"));
    const args = { q: "embedded", limit: 2, deployment_origin: "local" };
    const stdio = await client.callTool({ name: "search_semantic", arguments: args });
    const hosted = await handleMcpRequest(
      new Request("https://example.test/api/mcp", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          jsonrpc: "2.0",
          id: 1,
          method: "tools/call",
          params: { name: "search_semantic", arguments: args },
        }),
      }),
      createMcpApiBackend(async () => fixture),
    );
    assert.deepEqual(
      stdio.content,
      ((await hosted.json()) as { result: { content: unknown } }).result.content,
    );
    const invalid = await client.callTool({
      name: "search_semantic",
      arguments: { q: "x", include_drafts: true },
    });
    assert.equal(invalid.isError, true);
  } finally {
    await client.close();
    await server.close();
  }
});

test("filesystem tool returns a structured unavailable error, never a hidden lexical fallback", async () => {
  const server = new McpServer({ name: "test", version: "1" });
  registerRetrievalTool(server, new FilesystemBackend("/not-read"));
  const client = new Client({ name: "test", version: "1" });
  const [a, b] = InMemoryTransport.createLinkedPair();
  await Promise.all([client.connect(a), server.connect(b)]);
  try {
    const result = await client.callTool({ name: "search_semantic", arguments: { q: "state" } });
    assert.equal(result.isError, true);
    assert.match(JSON.stringify(result.content), /semantic_index_unavailable/);
    assert.match(JSON.stringify(result.content), /MATHEN_API_URL/);
  } finally {
    await client.close();
    await server.close();
  }
});

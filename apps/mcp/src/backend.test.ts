import assert from "node:assert/strict";
import { test } from "node:test";
import { ApiBackend, UnsupportedBackendError } from "./backend.js";

test("API backend calls the Hono endpoints and preserves MCP result records", async () => {
  const requests: Array<{ url: string; init?: RequestInit }> = [];
  const backend = new ApiBackend("https://api.example.test", async (input, init) => {
    requests.push({ url: String(input), init });
    const url = String(input);
    if (url.includes("/systems/duckdb")) {
      return jsonResponse({
        data: {
          id: "duckdb",
          name: "DuckDB",
          summary: "Analytical database",
          scope: ["analytics"],
          features: [],
          mathematical_views: [],
          trade_offs: [],
          evidence: [],
        },
      });
    }
    if (url.includes("/features?")) {
      return jsonResponse({
        data: [
          {
            system_id: "duckdb",
            system_name: "DuckDB",
            id: "embedded",
            name: "Embedded",
            category: "deployment-model",
            claim_type: "fact",
            description: "Runs in process",
            benefits: [],
            costs: [],
          },
        ],
      });
    }
    return jsonResponse({
      data: [{ id: "duckdb", name: "DuckDB", summary: "Analytical database" }],
    });
  });

  const systems = await backend.listSystems(false);
  const card = await backend.getSystem("duckdb", false);
  const features = await backend.searchFeatures("embedded", "deployment-model", "fact", false, 10);

  assert.equal(systems[0]?.id, "duckdb");
  assert.equal(card?.name, "DuckDB");
  assert.equal(features[0]?.feature.name, "Embedded");
  assert.match(requests[0]?.url ?? "", /\/api\/systems$/);
  assert.match(requests[2]?.url ?? "", /claim_type=fact/);
  assert.equal(
    requests[0]?.init?.headers && new Headers(requests[0].init.headers).get("accept"),
    "application/json",
  );
});

test("API backend reads modeling bundles and rejects drafts explicitly", async () => {
  const backend = new ApiBackend("https://api.example.test", async (input) => {
    assert.match(String(input), /\/api\/modeling\/duckdb$/);
    return jsonResponse({ data: { contract_version: 1, system: { id: "duckdb" } } });
  });

  const bundle = await backend.getModelingBundle("duckdb");
  assert.deepEqual(bundle, { contract_version: 1, system: { id: "duckdb" } });
  await assert.rejects(backend.listSystems(true), /include_drafts is unavailable/);
});

test("API backend reports request timeouts without exposing the URL", async () => {
  const backend = new ApiBackend(
    "https://user:secret@example.test/private",
    async (_input, init) =>
      new Promise((_resolve, reject) => {
        init?.signal?.addEventListener("abort", () =>
          reject(new DOMException("aborted", "AbortError")),
        );
      }),
    1,
  );

  await assert.rejects(backend.listSystems(false), (error: unknown) => {
    return (
      error instanceof Error &&
      error.message === "API request timed out: GET /api/systems" &&
      !error.message.includes("secret")
    );
  });
});

function jsonResponse(value: unknown): Response {
  return new Response(JSON.stringify(value), {
    headers: { "content-type": "application/json" },
    status: 200,
  });
}

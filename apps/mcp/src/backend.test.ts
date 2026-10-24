import assert from "node:assert/strict";
import { test } from "node:test";
import { ApiBackend } from "./backend.js";

test("API backend calls the Hono endpoints and preserves MCP result records", async () => {
  const requests: Array<{ url: string; init?: RequestInit }> = [];
  const backend = new ApiBackend(
    "https://api.example.test",
    async (input, init) => {
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
            temporal_context: { version: "2.0", claim_status: "accepted" },
            relations: [{ type: "extends", target: "base-system" }],
            feature_relations: [
              {
                source_feature_id: "embedded",
                target_system_id: "base-system",
                target_feature_id: "embedded",
                type: "resembles",
                claim_type: "analogy",
                claim_status: "proposed",
                evidence_ids: ["architecture"],
              },
            ],
            composition: { inputs: [{ system_id: "base-system" }] },
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
        data: [
          { id: "duckdb", name: "DuckDB", summary: "Analytical database" },
        ],
      });
    },
  );

  const systems = await backend.listSystems(false);
  const card = await backend.getSystem("duckdb", false);
  const features = await backend.searchFeatures(
    "embedded",
    "deployment-model",
    "fact",
    false,
    10,
  );

  assert.equal(systems[0]?.id, "duckdb");
  assert.equal(card?.name, "DuckDB");
  assert.equal(card?.temporal_context?.version, "2.0");
  assert.equal(card?.relations?.[0]?.type, "extends");
  assert.equal(card?.feature_relations?.[0]?.target_system_id, "base-system");
  assert.equal(
    (card?.composition?.inputs as Array<{ system_id: string }> | undefined)?.[0]
      ?.system_id,
    "base-system",
  );
  assert.equal(features[0]?.feature.name, "Embedded");
  assert.match(requests[0]?.url ?? "", /\/api\/systems$/);
  assert.match(requests[2]?.url ?? "", /claim_type=fact/);
  assert.equal(
    requests[0]?.init?.headers &&
      new Headers(requests[0].init.headers).get("accept"),
    "application/json",
  );
});

test("API backend sends the optional service token", async () => {
  let authorization = "";
  const backend = new ApiBackend(
    "https://api.example.test",
    async (_input, init) => {
      authorization = new Headers(init?.headers).get("authorization") ?? "";
      return jsonResponse({ data: [] });
    },
    10_000,
    "service-token",
  );
  await backend.listSystems(false);
  assert.equal(authorization, "Bearer service-token");
});

test("API backend lists bounded feature relations and preserves empty data", async () => {
  const requests: string[] = [];
  const backend = new ApiBackend("https://api.example.test", async (input) => {
    requests.push(String(input));
    return jsonResponse({
      data: [
        {
          source_system_id: "duckdb",
          source_feature_id: "embedded",
          target_system_id: "base-system",
          target_feature_id: "embedded",
          type: "resembles",
          claim_type: "analogy",
          claim_status: "proposed",
          evidence_ids: ["architecture"],
          notes: "Bounded comparison.",
        },
      ],
    });
  });
  const relations = await backend.listFeatureRelations(
    "duckdb",
    "embedded",
    "base-system",
    "resembles",
    false,
    10,
  );
  assert.deepEqual(relations, [
    {
      source_system_id: "duckdb",
      source_feature_id: "embedded",
      target_system_id: "base-system",
      target_feature_id: "embedded",
      type: "resembles",
      claim_type: "analogy",
      claim_status: "proposed",
      evidence_ids: ["architecture"],
      notes: "Bounded comparison.",
    },
  ]);
  const requestUrl = new URL(requests[0] ?? "https://invalid.test");
  assert.deepEqual(
    [...requestUrl.searchParams.entries()],
    [
      ["limit", "10"],
      ["system_id", "duckdb"],
      ["feature_id", "embedded"],
      ["target_system_id", "base-system"],
      ["type", "resembles"],
    ],
  );

  const emptyBackend = new ApiBackend("https://api.example.test", async () =>
    jsonResponse({ data: [] }),
  );
  assert.deepEqual(
    await emptyBackend.listFeatureRelations(
      undefined,
      undefined,
      undefined,
      undefined,
      false,
      20,
    ),
    [],
  );
});

test("API backend reads modeling bundles and rejects drafts explicitly", async () => {
  const backend = new ApiBackend("https://api.example.test", async (input) => {
    assert.match(String(input), /\/api\/modeling\/duckdb$/);
    return jsonResponse({
      data: { contract_version: 1, system: { id: "duckdb" } },
    });
  });

  const bundle = await backend.getModelingBundle("duckdb");
  assert.deepEqual(bundle, { contract_version: 1, system: { id: "duckdb" } });
  await assert.rejects(
    backend.listSystems(true),
    /include_drafts is unavailable/,
  );
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

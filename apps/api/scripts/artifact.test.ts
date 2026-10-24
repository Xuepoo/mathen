import assert from "node:assert/strict";
import { test } from "node:test";
import {
  artifactBucket,
  listArtifacts,
  normalizeArtifactPrefix,
  normalizeArtifactKey,
  normalizeRelease,
  pruneArtifacts,
  uploadArtifact,
} from "./artifact.js";

const fixture = new URL(
  "../../../data/experiments/g5-minimal.json",
  import.meta.url,
);

test("normalizes release-keyed artifact paths and rejects traversal", () => {
  assert.equal(
    normalizeArtifactKey("v1.2.3", "reports/summary.json"),
    "releases/v1.2.3/reports/summary.json",
  );
  assert.throws(() => normalizeRelease("release/unsafe"));
  assert.throws(() => normalizeArtifactKey("v1", "../secret.json"));
  assert.throws(() => normalizeArtifactKey("v1", "reports/%2e%2e/secret.json"));
  assert.equal(normalizeArtifactPrefix("releases/v1/"), "releases/v1/");
  assert.throws(() => normalizeArtifactPrefix("other/"));
  assert.throws(() => normalizeArtifactPrefix("releases/v1/../"));
});

test("selects explicit, preview, and production artifact buckets", () => {
  assert.equal(
    artifactBucket({ APP_ENV: "preview" }),
    "mathen-artifacts-preview",
  );
  assert.equal(
    artifactBucket({ APP_ENV: "production" }),
    "mathen-artifacts-production",
  );
  assert.equal(
    artifactBucket({ APP_ENV: "preview", R2_ARTIFACT_BUCKET: "mock-bucket" }),
    "mock-bucket",
  );
});

test("upload uses a release key and verifies injected readback", async () => {
  const uploaded: string[][] = [];
  const content = new Uint8Array(await (await fetch(fixture)).arrayBuffer());
  const result = await uploadArtifact({
    bucket: "mock-bucket",
    release: "v1",
    key: "results.json",
    file: fixture.pathname,
    verify: true,
    runner: async (args) => {
      uploaded.push(args);
    },
    readback: async () => content,
  });
  assert.equal(result.key, "releases/v1/results.json");
  assert.equal(result.bytes, content.byteLength);
  assert.deepEqual(uploaded[0]?.slice(0, 4), [
    "r2",
    "object",
    "put",
    "mock-bucket/releases/v1/results.json",
  ]);
});

test("list paginates and prune dry-run never sends deletes", async () => {
  const requests: Array<{ url: string; method: string }> = [];
  const fetcher = async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input);
    const method = init?.method ?? "GET";
    requests.push({ url, method });
    const page = new URL(url).searchParams.has("cursor")
      ? {
          success: true,
          result: [
            {
              key: "releases/v1/old.json",
              last_modified: "2020-01-01T00:00:00Z",
            },
          ],
          result_info: {},
        }
      : {
          success: true,
          result: [
            {
              key: "releases/v1/old.json",
              last_modified: "2020-01-01T00:00:00Z",
            },
          ],
          result_info: { cursor: "next", is_truncated: true },
        };
    return new Response(JSON.stringify(page), { status: 200 });
  };
  const listed = await listArtifacts(
    {
      accountId: "mock-account",
      token: "mock-token",
      bucket: "mock-bucket",
      prefix: "releases/v1/",
    },
    fetcher,
  );
  assert.equal(listed.length, 2);
  const stale = await pruneArtifacts(
    {
      accountId: "mock-account",
      token: "mock-token",
      bucket: "mock-bucket",
      release: "v1",
      retentionDays: 1,
      dryRun: true,
    },
    fetcher,
  );
  assert.equal(stale.length, 2);
  assert.equal(
    requests.some((request) => request.method === "DELETE"),
    false,
  );
});

test("prune refuses destructive mode without explicit confirmation", async () => {
  await assert.rejects(
    pruneArtifacts(
      {
        accountId: "mock-account",
        token: "mock-token",
        bucket: "mock-bucket",
        release: "v1",
        retentionDays: 30,
      },
      async () => new Response("{}"),
    ),
    /--dry-run or --yes/,
  );
});

test("prune refuses a list response outside the selected release namespace", async () => {
  await assert.rejects(
    pruneArtifacts(
      {
        accountId: "mock-account",
        token: "mock-token",
        bucket: "mock-bucket",
        release: "v1",
        retentionDays: 1,
        yes: true,
      },
      async () =>
        new Response(
          JSON.stringify({
            success: true,
            result: [
              {
                key: "releases/v2/old.json",
                last_modified: "2020-01-01T00:00:00Z",
              },
            ],
            result_info: {},
          }),
          { status: 200 },
        ),
    ),
    /outside releases\/v1\//,
  );
});

import { mkdtemp, mkdir, rm, writeFile } from "node:fs/promises";
import assert from "node:assert/strict";
import { tmpdir } from "node:os";
import { resolve } from "node:path";
import { test } from "node:test";
import { ApiBackend, FilesystemBackend } from "./backend.js";

test("filesystem backend filters reviewed and draft composition proposals", async () => {
  const root = await mkdtemp(resolve(tmpdir(), "mathen-compositions-"));
  try {
    await mkdir(resolve(root, "data/systems"), { recursive: true });
    await mkdir(resolve(root, "data/drafts"), { recursive: true });
    const composition = {
      inputs: [{ system_id: "alpha", role: "storage" }],
      constraints: [],
      preserved_properties: [],
      conflicts: [],
      claim_status: "accepted",
      evidence_ids: ["architecture-doc"],
    };
    await writeFile(
      resolve(root, "data/systems/zeta.json"),
      JSON.stringify({ id: "zeta", name: "Zeta", composition }),
    );
    await writeFile(
      resolve(root, "data/drafts/alpha.json"),
      JSON.stringify({
        id: "alpha",
        name: "Alpha",
        composition: { ...composition, claim_status: "proposed" },
      }),
    );

    const backend = new FilesystemBackend(root);
    assert.deepEqual(
      await backend.listCompositions("alpha", "accepted", false, 10),
      [
        {
          system_id: "zeta",
          system_name: "Zeta",
          version_context: null,
          composition,
        },
      ],
    );
    assert.equal(
      (await backend.listCompositions(undefined, "proposed", false, 10)).length,
      0,
    );
    assert.equal(
      (await backend.listCompositions(undefined, "proposed", true, 10))[0]
        ?.system_id,
      "alpha",
    );
  } finally {
    await rm(root, { recursive: true, force: true });
  }
});

test("API backend normalizes composition query results and preserves draft boundary", async () => {
  const requests: string[] = [];
  const backend = new ApiBackend("https://api.example.test", async (input) => {
    requests.push(String(input));
    return new Response(
      JSON.stringify({
        data: [
          {
            system_id: "candidate",
            system_name: "Candidate",
            version_context: "v1",
            composition: {
              inputs: [{ system_id: "duckdb", role: "storage" }],
              claim_status: "under-review",
            },
          },
        ],
      }),
      { headers: { "content-type": "application/json" } },
    );
  });

  const result = await backend.listCompositions(
    "duckdb",
    "under-review",
    false,
    10,
  );
  assert.equal(result[0]?.system_id, "candidate");
  assert.equal(result[0]?.composition.claim_status, "under-review");
  assert.match(requests[0] ?? "", /input_system=duckdb/);
  assert.match(requests[0] ?? "", /claim_status=under-review/);
  await assert.rejects(
    backend.listCompositions(undefined, undefined, true, 10),
    /include_drafts is unavailable/,
  );
});

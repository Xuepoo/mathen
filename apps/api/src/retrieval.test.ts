import assert from "node:assert/strict";
import { test } from "node:test";
import {
  buildRetrievalDocuments,
  parseRetrievalQuery,
  rankRetrievalDocuments,
  type RetrievalDocument,
} from "./retrieval.js";

test("retrieval query is bounded and rejects unknown or malformed filters", () => {
  const parsed = parseRetrievalQuery(
    new URLSearchParams(
      "q=embedded+execution&limit=2&record_kind=feature,view&deployment_origin=local",
    ),
  );
  assert.deepEqual(parsed, {
    query: "embedded execution",
    limit: 2,
    filters: { record_kind: ["feature", "view"], deployment_origin: "local" },
  });
  assert.throws(() => parseRetrievalQuery(new URLSearchParams("q=x&unknown=y")), /Unknown/);
  assert.throws(() => parseRetrievalQuery(new URLSearchParams("q=x&limit=0")), /between/);
  assert.throws(
    () => parseRetrievalQuery(new URLSearchParams("q=x&deployment_origin=bad value")),
    /malformed/,
  );
});

test("ranking is deterministic and filters scope conservatively", () => {
  const documents: RetrievalDocument[] = [
    documentFixture("system:z", "z", { deployment_origins: ["local"] }),
    documentFixture("system:a", "a", { deployment_origins: ["local"] }),
    documentFixture("system:unscoped", "unscoped"),
  ];
  const results = rankRetrievalDocuments(documents, {
    query: "embedded execution",
    limit: 10,
    filters: { deployment_origin: "local" },
  });
  assert.deepEqual(
    results.map((result) => result.document.id),
    ["system:a", "system:z"],
  );
  assert.equal(results[0]?.score_kind, "lexical_overlap");
  assert.equal(results[0]?.provenance.retrieval_method, "bounded_lexical_baseline");
});

test("corpus builder excludes records without closed evidence and preserves metadata", async () => {
  const documents = await buildRetrievalDocuments({
    systems: [
      {
        id: "alpha",
        name: "Alpha",
        version_context: "1.0",
        summary: "Embedded execution",
        scope_json: '["execution"]',
        temporal_context_json: '{"claim_status":"accepted"}',
        relations_json: "[]",
        composition_json: null,
        source_path: "data/systems/alpha.json",
      },
    ],
    features: [
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
        metadata_json:
          '{"claim_status":"accepted","validity_scope":{"deployment_origins":["local"]}}',
        evidence_ids_json: '["architecture"]',
      },
      {
        id: "unsupported",
        system_id: "alpha",
        system_name: "Alpha",
        name: "Missing evidence",
        category: "deployment",
        claim_type: "hypothesis",
        description: "Must not be indexed.",
        benefits_json: "[]",
        costs_json: "[]",
        metadata_json: "{}",
        evidence_ids_json: '["missing"]',
      },
    ],
    views: [],
    tradeOffs: [],
    relations: [],
    compositions: [],
    evidence: [
      {
        id: "architecture",
        system_id: "alpha",
        kind: "official-doc",
        title: "Architecture",
        uri: "https://example.test/architecture",
        accessed: null,
        notes: null,
      },
    ],
  });
  assert.deepEqual(
    documents.map((document) => document.id),
    ["system:alpha:feature:embedded", "system:alpha:summary"],
  );
  const feature = documents.find((document) => document.record_kind === "feature");
  assert.deepEqual(feature?.evidence_ids, ["architecture"]);
  assert.deepEqual(feature?.validity_scope, { deployment_origins: ["local"] });
  assert.match(feature?.source_digest ?? "", /^sha256:[0-9a-f]{64}$/);
});

function documentFixture(
  id: string,
  name: string,
  validityScope?: Record<string, unknown>,
): RetrievalDocument {
  return {
    id,
    record_kind: "feature",
    system_id: id,
    feature_id: name,
    category: "deployment",
    name,
    description: "Embedded execution",
    text: `${name} embedded execution`,
    claim_type: "fact",
    claim_status: "accepted",
    version_context: "1.0",
    validity_scope: validityScope,
    evidence_ids: ["evidence"],
    evidence: [{ id: "evidence", kind: "doc", title: "Doc", uri: "https://example.test" }],
    source_ref: `data/systems/${id}.json#feature`,
    source_digest: "sha256:test",
    document: { id, name },
  };
}

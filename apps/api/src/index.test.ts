import assert from "node:assert/strict";
import { test } from "node:test";
import { buildCompositions, buildGraph } from "./index.js";

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
    },
  ]);
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

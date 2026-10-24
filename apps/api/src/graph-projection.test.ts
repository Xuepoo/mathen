import assert from "node:assert/strict";
import { test } from "node:test";
import { buildLayeredGraphProjection } from "./graph-projection.js";

test("projects independent layers and only explicit typed composition edges", () => {
  const graph = buildLayeredGraphProjection(
    {
      systems: [
        {
          id: "alpha",
          name: "Alpha",
          scope: ["local"],
          features: [
            {
              id: "state",
              name: "State property",
              category: "behavior",
              claim_type: "fact",
              description: "State property",
              evidence_ids: ["architecture"],
            },
          ],
          mathematical_views: [
            {
              id: 4,
              model: "Transition system",
              question: "What transitions are valid?",
              assumptions: ["finite state"],
              claim_type: "inference",
              evidence_ids: ["architecture"],
            },
          ],
          composition: {
            typed_semantics: {
              claim_type: "hypothesis",
              claim_status: "proposed",
              evidence_ids: ["architecture"],
              proven: false,
              discovery: {
                method: "review",
                provenance: ["source"],
                source_community: "systems",
                target_community: "formal-methods",
                path: ["source", "review"],
                candidate_status: "candidate",
              },
              validity_scope: {
                systems: ["alpha"],
                versions: [],
                deployment_origins: ["local-analysis"],
                conditions: [],
                exclusions: [],
              },
              components: [
                {
                  id: "producer",
                  role: "producer",
                  claim_type: "fact",
                  claim_status: "accepted",
                  evidence_ids: ["architecture"],
                },
                {
                  id: "consumer",
                  role: "consumer",
                  claim_type: "fact",
                  claim_status: "accepted",
                  evidence_ids: ["architecture"],
                },
              ],
              adapters: [
                {
                  id: "adapter",
                  source: "producer",
                  target: "consumer",
                  description: "explicit adapter",
                  claim_type: "hypothesis",
                  claim_status: "proposed",
                  evidence_ids: ["architecture"],
                },
              ],
              boundaries: [],
              property_effects: [
                {
                  id: "effect",
                  property: "ordering",
                  relation: "unverified",
                  claim_type: "hypothesis",
                  claim_status: "proposed",
                  evidence_ids: ["architecture"],
                },
              ],
              preconditions: [],
              postconditions: [],
              resource_effects: [],
              failure_modes: [],
              examples: [],
              counterexamples: [],
              uncertainties: [
                {
                  id: "uncertain",
                  description: "needs validation",
                  claim_type: "hypothesis",
                  claim_status: "proposed",
                  evidence_ids: ["architecture"],
                },
              ],
              disagreements: [],
            },
          },
        },
      ],
      microstructures: [
        {
          id: "bounded-loop",
          name: "Bounded loop",
          document: {
            claim_type: "inference",
            claim_status: "under-review",
            evidence_ids: ["micro-doc"],
            validity_scope: { deployment_origins: ["local-analysis"] },
            scale: { level: "mechanism" },
            role: { description: "bounded repetition" },
            summary: "A bounded loop.",
          },
        },
      ],
    },
    "local-analysis",
  );

  assert.deepEqual(
    graph.nodes.map((node) => node.id),
    [
      "composition:alpha",
      "composition:alpha:component:consumer",
      "composition:alpha:component:producer",
      "composition:alpha:property-effect:effect",
      "composition:alpha:relation:adapter:adapter",
      "math:alpha:4",
      "microstructure:bounded-loop",
      "property:alpha:state",
      "system:alpha",
    ],
  );
  assert.ok(graph.edges.some((edge) => edge.type === "adapter"));
  assert.ok(graph.edges.some((edge) => edge.type === "has-typed-relation"));
  assert.ok(
    graph.edges.some((edge) => edge.type === "declares-property-effect"),
  );
  assert.equal(
    graph.edges.some(
      (edge) =>
        edge.source === "system:alpha" && edge.target === "system:missing",
    ),
    false,
  );
  const composition = graph.nodes.find(
    (node) => node.id === "composition:alpha",
  );
  assert.equal(composition?.metadata.proven, false);
  assert.deepEqual(composition?.metadata.discovery, {
    method: "review",
    provenance: ["source"],
    source_community: "systems",
    target_community: "formal-methods",
    path: ["source", "review"],
    candidate_status: "candidate",
  });
});

test("origin filtering is configurable and keeps originless documents visible", () => {
  const graph = buildLayeredGraphProjection(
    {
      systems: [],
      microstructures: [
        {
          id: "local",
          name: "Local",
          document: { validity_scope: { deployment_origins: ["local"] } },
        },
        {
          id: "other",
          name: "Other",
          document: { validity_scope: { deployment_origins: ["other"] } },
        },
        { id: "unspecified", name: "Unspecified", document: {} },
      ],
    },
    "local",
  );
  assert.deepEqual(
    graph.nodes.map((node) => node.id),
    ["microstructure:local", "microstructure:unspecified"],
  );
});

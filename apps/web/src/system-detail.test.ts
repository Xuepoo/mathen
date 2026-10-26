import { describe, expect, test } from "bun:test";
import { renderDetail, type SystemDetail } from "./system-detail";
import type { GraphPayload } from "./graph-data";

const graph: GraphPayload = {
  nodes: [
    { id: "source", name: "Source system", type: "system" },
    { id: "target", name: "Target system", type: "system" },
  ],
  edges: [],
};

const system: SystemDetail = {
  id: "source",
  name: "Source system",
  version_context: null,
  summary: "A reviewed system.",
  scope: ["Storage"],
  related_systems: [],
  features: [
    {
      id: "source-feature",
      name: "Source feature",
      category: "Boundary",
      claim_type: "fact",
      description: "A feature.",
      benefits: [],
      costs: [],
      evidence_ids: ["experiment-1"],
    },
  ],
  mathematical_views: [],
  feature_relations: [
    {
      source_feature_id: "source-feature",
      target_system_id: "target",
      target_feature_id: "target-feature",
      type: "resembles",
      claim_type: "analogy",
      claim_status: "proposed",
      evidence_ids: ["experiment-1"],
    },
  ],
  evidence: [
    {
      id: "experiment-1",
      title: "Transaction experiment",
      uri: "https://example.com/experiment",
      kind: "experiment",
    },
  ],
};

describe("renderDetail", () => {
  test("renders feature relation direction, metadata, names, and evidence", () => {
    const html = renderDetail(system, graph);
    expect(html).toContain("Feature relations (1)");
    expect(html).toContain("Source system");
    expect(html).toContain("Source feature");
    expect(html).toContain("Target system");
    expect(html).toContain("target-feature");
    expect(html).toContain("resembles");
    expect(html).toContain("analogy · proposed");
    expect(html).toContain("experiment-1");
    expect(html).toContain("evidence-experiment");
  });

  test("tolerates cards without feature relations", () => {
    const { feature_relations: _, ...withoutRelations } = system;
    expect(renderDetail(withoutRelations, graph)).toContain("No feature relations recorded.");
  });

  test("does not turn credential-bearing evidence URLs into active links", () => {
    const html = renderDetail(
      {
        ...system,
        evidence: [{ ...system.evidence[0], uri: "https://token:secret@example.com/source" }],
      },
      graph,
    );
    expect(html).not.toContain('href="https://token:secret@example.com/source"');
    expect(html).toContain("(non-web source)");
  });

  test("displays propagated scope, lifecycle, validation, and observation metadata", () => {
    const html = renderDetail(
      {
        ...system,
        scope_context: { workload: { status: "specified" } },
        features: [{ ...system.features[0], lifecycle: { status: "observed" } }],
        mathematical_views: [
          {
            model: "State machine",
            question: "How?",
            assumptions: [],
            claim_type: "inference",
            evidence_ids: ["experiment-1"],
            lifecycle: { status: "reviewed" },
            contract: { validation_records: [{ id: "validation-1" }] },
          },
        ],
        evidence: [
          {
            ...system.evidence[0],
            scope_context: { workload: { status: "specified" } },
            metadata: { observation_version: "1" },
          },
        ],
      },
      graph,
    );
    expect(html).toContain("Scope context");
    expect(html).toContain("Lifecycle");
    expect(html).toContain("Validation records: 1");
    expect(html).toContain("observation_version");
  });
});

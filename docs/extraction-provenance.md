# Extraction and graph provenance

This document defines how Mathen records the replaceable model-assisted part of
feature extraction and graph construction. It extends the secret-safe audit
boundary described in [`llm-modeling.md`](llm-modeling.md); it does not change
the Architecture Card schema or promote a new data format. The current CLI
writes protocol sidecars for LLM modeling, while the fields below are the
recommended contract for a complete extraction/graph run record.

## Current model profile

The current profile is recorded exactly as supplied for this run:

```text
provider/model: openai/gpt-6-astra
thinking level: high
role: feature extraction and graph construction/annotation
```

This profile describes an instrument configuration, not an architectural
authority. The model is replaceable: another provider or model may perform the
same role if it receives the same evidence boundary and produces outputs under
the same versioned prompt and output contracts. A profile change is a new
provenance condition, not an overwrite of the prior run.

## Evidence and processing boundaries

Every extracted feature or graph edge should remain traceable to the stage that
introduced it. These stages must not be collapsed into one generic
`provenance` label:

1. **Source evidence** — pinned source files, documentation, commits, archive
   provenance, and evidence IDs. This is what was observed or cited, not what a
   model inferred from it.
2. **Deterministic inspection** — reproducible repository inspection commands,
   tool versions, analysis version, observations, and report digests. Structural
   signals such as paths or manifests are observations; they do not by
   themselves establish semantic architecture claims.
3. **Model extraction** — the model profile, prompt and output contract,
   supplied input digest, extracted feature/edge candidates, and output digest.
   Model-generated descriptions remain candidates and retain claim types and
   evidence IDs.
4. **Graph assembly** — the graph/projection algorithm and version, node and
   edge inputs, relation type, graph digest, and the provenance of each edge.
   Assembly can normalize or project candidates, but must not silently turn
   similarity into a typed relation.
5. **Human review** — reviewer, review time, decision, uncertainty,
   disagreement, corrections, and review status. Review evaluates evidence and
   claims; it does not retroactively make an unsupported model output source
   evidence.
6. **Canonical promotion** — a deliberate human-controlled transition from a
   draft or candidate record to `data/systems/`. Promotion status is separate
   from review status and must never be inferred from graph presence or model
   completion.

The resulting chain is:

```text
source evidence
  -> deterministic inspection
  -> model candidates
  -> graph projection/assembly
  -> human review
  -> (optional) canonical promotion
```

The chain is a traceability boundary, not a claim that each later stage is
correct. Source evidence and deterministic observations remain distinct from
model interpretation, graph structure, and reviewer decisions.

## Recommended per-run record

For each extraction or graph run, record these fields in a secret-safe sidecar
or run manifest. Digests should be SHA-256 (or an explicitly named equivalent)
over canonical serialized inputs/outputs; do not store prompts, headers, or
configuration containing secrets merely to make a run reproducible.

<!-- markdownlint-disable MD013 -->

| Field | Requirement and purpose |
| --- | --- |
| `run_id` | Stable unique identifier for this run. |
| `run_time` | UTC timestamp for when the run was executed. |
| `provider` | Provider name; never an API key or authorization value. |
| `base_url` | Effective endpoint without credentials, query secrets, or headers. |
| `exact_model_id` | Exact model identifier, including deployment/version detail when supplied by the provider. |
| `thinking_level` | Effective reasoning/thinking setting, or an explicit `not-recorded` value when unavailable. |
| `role` | The model role, such as feature extraction and graph construction/annotation. |
| `prompt_version` / `prompt_digest` | Version and digest of the rendered prompt or extraction instructions. |
| `schema_version` / `schema_digest` | Version and digest of the output contract used for candidates or graph records. |
| `input_revision` | Fixed source commit/archive revision and evidence-bundle or input digest. |
| `deterministic_inspection` | Inspector name/version, command or analysis version, and report digest. |
| `graph_assembly` | Projection/assembly algorithm version, graph input digest, and graph output digest when a graph is produced. |
| `output_digest` | Digest of the canonical serialized model/graph output. |
| `review_status` | Current review state, including pending, under review, accepted, rejected, or corrected as applicable. |
| `canonical_status` | Explicitly non-canonical, or the reviewed promotion record when promotion has occurred. |

<!-- markdownlint-enable MD013 -->

`input_revision`, evidence IDs, and stage-specific digests provide locality:
an edge should identify the candidate and evidence that caused it to enter the
projection, while a graph digest identifies the assembled result. A later
projection or review must add a new run record rather than mutate the old
record's model provenance.

## Replaceability and run comparison

Model replacement is meaningful only when the comparison boundary is held
constant. To compare two runs, use the same pinned source revision and input
digest, prompt/schema versions and digests, deterministic-inspection result,
role, and graph assembly procedure where possible. Then compare:

- feature and edge additions, removals, and changed claim types;
- evidence locality and unsupported-candidate rates;
- reviewer corrections, disagreements, rejection rates, and review effort;
- graph topology only within the same projection definition; and
- output, graph, and run metadata digests.

If the model, provider, thinking level, prompt, schema, input revision, or
assembly algorithm changes, the result is a distinct run and the changed
condition must be reported. Changes in model can change extracted features and
graph edges even when the source revision is unchanged. A changed edge is not
evidence that the source changed; it may reflect model interpretation or graph
assembly behavior.

## What the output does not establish

Model output is **not** proof, semantic truth, a causal relation,
compatibility, or superiority. In particular:

- a generated feature is not a fact unless its source evidence supports it and
  review accepts the claim;
- a graph edge is not historical influence, dependency, composition,
  substitutability, or compatibility merely because a model proposed it;
- a similarity or graph position is not an architecture quality score; and
- a reviewed candidate still has the scope, assumptions, claim type, and
  evidence limits recorded with it.

LLM-generated records remain under `data/drafts/` or in a research candidate
surface until deliberate human review. Canonical promotion is a separate
operation and never follows automatically from a valid JSON response, a
successful graph build, or a high model confidence expression.

## Relationship to existing contracts

- [`llm-modeling.md`](llm-modeling.md) defines the current evidence-bounded
  modeling workflow and secret-safe protocol sidecar.
- [`extraction-quality.md`](extraction-quality.md) defines deterministic
  inspection limits and independent coverage review dimensions.
- [`research-instrument.md`](research-instrument.md) separates human, model,
  graph, mathematical, and experimental contributions and keeps candidate
  relations distinct from validated relations.
- Architecture Cards continue to require local evidence and claim metadata;
  this document does not authorize changes to canonical cards, drafts,
  relations, APIs, or migrations.

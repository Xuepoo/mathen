# Evidence-bounded feature lifecycle status

**Status:** MTH-0145 contract and audit. This is an additive contract; the
canonical corpus is not backfilled by this task.

## Boundary

`claim_type` describes the epistemic kind of a claim (`fact`, `inference`,
`hypothesis`, or `analogy`). `claim_status` describes review state
(`proposed`, `under-review`, `accepted`, `rejected`, or `deprecated`). Neither
field describes whether the represented feature exists in a product's
timeline. Lifecycle metadata is a third, independent dimension.

The minimum lifecycle envelope is:

```json
{
  "lifecycle": {
    "status": "observed",
    "evidence_ids": ["fixed-commit"],
    "claim_type": "fact",
    "claim_status": "accepted"
  }
}
```

Every status is an explicit assertion and therefore requires one or more
evidence IDs local to the owning card. Missing lifecycle metadata means
**unknown/not recorded**, not proposed, observed, reviewed, current, or absent.
No consumer may synthesize it from claim type, source kind, popularity, graph
degree, version context, name/category, or retrieval similarity.

## Status vocabulary

| Status       | Minimum meaning                                                                                                                    | Evidence boundary                                                                                        |
| ------------ | ---------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------- |
| `proposed`   | A feature is specified or intended, but existence in the referenced implementation is not established.                             | Design/spec/proposal evidence; do not present as observed implementation.                                |
| `observed`   | The feature was directly observed in a named version/revision or controlled observation.                                           | Source, official documentation, or reproducible experiment that identifies the observed boundary.        |
| `reviewed`   | A reviewer accepted the lifecycle assertion for the cited boundary.                                                                | Evidence IDs plus independent review state; this does not mean universal truth or currentness.           |
| `deprecated` | The feature remains historically relevant but is explicitly discouraged, withdrawn, or no longer supported in the stated boundary. | Release/deprecation notice, source removal, or equivalent direct evidence; notes are required.           |
| `superseded` | The feature's role is replaced by one or more explicitly named successors.                                                         | Direct replacement evidence, non-empty `superseded_by`, and notes; this is not inferred from similarity. |

`reviewed` is a lifecycle review decision, not a replacement for
`claim_status=accepted`. `observed` is compatible with any claim type only when
the evidence supports that exact claim: an observed analogy remains an analogy,
and an observed hypothesis remains unvalidated. `analogy` can describe a
bounded comparison but cannot establish that an implementation feature exists,
is deprecated, or superseded. Use `fact` for directly observed lifecycle
assertions; use `inference` or `hypothesis` only when the lifecycle statement
itself is explicitly derived or provisional. Lifecycle status must never
upgrade the owning claim.

## Validation rules

1. `lifecycle` is optional for backward compatibility; when present it has a
   controlled `status`, non-empty local `evidence_ids`, `claim_type`, and
   `claim_status`.
2. `deprecated` and `superseded` require non-empty reviewer-facing `notes`.
3. `superseded` requires a non-empty `superseded_by` list of stable IDs;
   `superseded_by` is forbidden for other statuses. The target's existence and
   compatibility are separate evidence-bounded claims and are not implied.
4. Evidence closure is checked against the owning card. An evidence kind only
   establishes what it directly records: source/docs can establish a declared
   or observable mechanism, while experiments can establish only their stated
   protocol, environment, workload, scale, and outcome.
5. Unknown, missing, conflicting, or stale lifecycle evidence must be exposed
   as unknown/withheld by retrieval and graph consumers, never repaired.

## Compatibility

The schema permits lifecycle metadata on features and mathematical views.
Python validation checks evidence closure and transition-specific fields. D1
seed metadata, API retrieval documents, and graph projections preserve the
object verbatim when present; older rows omit it. MCP normalization should
preserve it in the same way when the API wire type is extended. Lifecycle is
metadata, not a graph edge, ranking signal, or filter that can invent a state.

## Canonical audit at e822d51

The read-only audit covers `data/systems/*.json` and reports:

- 219 cards, 830 features, and 608 mathematical views;
- all 830 features have a claim type and local evidence IDs, with 818 `fact`
  and 12 `inference` claims;
- 604 views have no claim status, while 4 are `proposed`; view claim types are
  1 `fact`, 445 `inference`, 160 `hypothesis`, and 2 `analogy`;
- only 7 features have `claim_status` (`accepted`), and no audited feature or
  view has explicit lifecycle metadata;
- cards have no top-level claim type/status; 14 cards have temporal context,
  which is a separate card/version lifecycle contract and must not be copied
  onto features;
- every feature and view has evidence IDs; no status is inferred from the
  source kind or from the existence of those IDs.

Run the non-mutating report with:

```bash
uv run python scripts/audit_lifecycle_status.py data/systems \
  --output /tmp/opencode/lifecycle-status-mth-0145.json
```

The report keeps claim-type coverage separate from lifecycle coverage and
records the non-inference guardrails. It intentionally emits no proposed
canonical edits. Representative fixtures should use direct evidence and remain
tests or drafts until reviewed; no canonical backfill is justified by this
audit alone.

## Implementation plan

1. Review and author lifecycle metadata only where a reviewer can cite direct,
   local evidence; retain absent fields as unknown/not recorded.
2. Extend D1 migrations, seed, API, graph, and MCP wire types together, with
   round-trip tests and the existing `{"data": ...}` envelope.
3. Add conservative lifecycle filters only after exact semantics and unknown
   behavior are agreed; omitted lifecycle must not match an exact status.
4. Add retrieval/graph UI labels that display lifecycle separately from claim
   type/status and never convert it into an edge, score, or proof.
5. Re-run the audit and report specified, unknown, unspecified, and
   not-applicable denominators by surface, plus evidence locality, status
   agreement, abstention, and false-link rate.

Unresolved boundaries: whether `reviewed` should be retained as a lifecycle
state or represented solely by `claim_status=accepted`; whether successor IDs
are feature-local or system-qualified; and what independent review protocol is
required before a lifecycle assertion is accepted. Those choices require a
separate contract review and must not be guessed from this corpus.

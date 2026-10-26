# MTH-0154 retrieval evaluation

**Status:** research-only offline evaluation; no production retrieval change.

## Protocol

The machine-readable artifact is
`docs/audits/mth-0154-retrieval-evaluation.json`. It freezes the reviewed
`canonical_cards` corpus at the recorded commit and includes 2,481
evidence-closed atomic documents from 219 cards. Document IDs, source
references, source digests, claim types/statuses, validity scope, and the
evidence bundle are included in the digest-checked manifest. No vectors,
model payloads, prompts, secrets, provider bindings, or Vectorize resources are
written.

The query set contains 48 manually authored architecture-discovery questions:
42 reviewer-rubric labels for evaluation and six held-out unknown or
negative-knowledge queries. The evaluation queries are split into explicit
paraphrase, misleading-similarity, claim-type, scope, and freshness slices.
The held-out queries are excluded from candidate generation. Labels are
research judgments about what a reviewer should inspect first; they do not
assert semantic truth, compatibility, causality, historical influence,
substitutability, or production review.

The control uses the deployed bounded lexical rule: normalized unique Unicode
tokens, title matches weighted by one half, a score cap of one, positive-score
results only, deterministic score/ID ordering, and a bounded top ten. The
runner is `scripts/retrieval_evaluation.py`; rerunning it against the same
source revision produces the same JSON after the source commit is recorded.

## Observations

| Control observation | Value |
| --- | ---: |
| Evaluation queries | 42 |
| Held-out queries | 6 |
| Recall@5 | 19/42 = 0.4524 |
| nDCG@5 | 0.3684 |
| Evidence locality | 420/420 = 1.0000 |
| Scope completeness | 0/420 = 0.0000 (scope fields unknown in snapshot) |
| Claim-type accuracy | 25/42 = 0.5952 |
| False-link rate | 6/25 = 0.2400 |
| Abstention rate | 6/48 = 0.1250 (held-out controls) |
| Latency p50/p95 | null; not measured by this offline artifact |
| Provider errors | null/0; not applicable to lexical control |
| Provider calls | 0 |

The slice denominators and null values are retained in the JSON. A null means
that the denominator is empty or an operational observation was not measured;
it is not zero and cannot support a gain claim. Missing freshness/accessed
metadata remains unknown rather than being treated as fresh.

The local `bge-micro-v2` candidate is **prior-pilot-only** here. Its hashed
model/tokenizer/runtime and the 12-query results remain in
`docs/audits/mth-0150-retrieval-embedding-pilot.json`; this task did not rerun
the embedding pass and makes no new vector result. The prior pilot reported
equal recall@5 and lower vector nDCG@5 than lexical, with approximately 280.8
seconds of CPU document embedding time.

## Decision

Retain the bounded lexical baseline. The larger deterministic artifact makes
the missing comparison explicit rather than filling it with invented vector
numbers. Reconsideration requires an independently reviewed, same-snapshot
vector run with the same labels and slices, evidence locality/claim/scope and
false-link gates, explicit abstention behavior, and measurable p50/p95 latency,
provider errors, and cost. This decision changes no production retrieval path
and does not add a model, provider, binding, secret, resource, or vector
payload.

Validate with:

```bash
uv run mathen validate-retrieval-evaluation docs/audits/mth-0154-retrieval-evaluation.json
```

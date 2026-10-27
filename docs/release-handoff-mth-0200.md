# MTH-0200 research wave release handoff

**Status:** release handoff for the verified MTH-0199 integration at
`24e458d4d1bb7227a568728e62a63398d1cf0b27`. This release contains research
artifacts and validation code only. It does not deploy the Worker, change API
or browser production code, change production resources, or modify paper
正文/LaTeX/BibTeX/arXiv files.

## Included research surfaces

### MTH-0193 repeated agent-only observations and MTH-0196 statistics

The repeated pilot records two independent agent-only runs over the frozen
MTH-0185 enriched packet. The artifact preserves `reviewer_kind: "agent"`,
`human_review: false`, `research_only: true`, `non_canonical: true`, and
`promotion_decision: "not-determined"` at the pilot, run, packet, and
observation boundaries. The source timing is a bounded packet-handling
observation; it is not conversational reasoning time, human-review effort, or
model productivity.

The MTH-0196 scoring and statistical artifacts report the observed agent
stratum separately from the explicit empty/not-evaluated human stratum. They
retain the observed rows, error dimensions, task/domain slices, exact
binomial intervals, and repeated-run summaries without computing an aggregate
quality score. MTH-0195 is linked by identity and digest; unobserved benchmark
tasks receive no labels or inferred outcomes.

### MTH-0194 direct-LLM readiness

The readiness artifact is a secret-safe local inspection record with
`status: "not-evaluated"`, `canonical: false`, and a human-promotion gate.
No approved local runtime was available in the recorded inspection. Provider,
exact model, prompt, output, and inference metrics remain absent or `null`.
Cache presence is not treated as runtime approval. The inspector does not load
a model, invoke inference, contact an endpoint, or read secret values.

### MTH-0195 independent benchmark tasks

The benchmark is an authored, research-only set of 24 cross-system tasks over
four domains. It contains task/evidence/source/card digests and an exhaustive,
disjoint train/evaluation/holdout partition, but no model outputs, reviewer
labels, empirical scores, superiority claim, or direct-LLM evaluation.
Composition candidates remain proposed, unproven, non-canonical, and subject
to human review. Protocol capacity and task count are not statistical power.

### MTH-0197 bounded SQLite busy-timeout observation

The observation is detached from the canonical SQLite card and remains
`canonical: false`, under review, and subject to a human-promotion gate. It
records three repetitions of one fixed two-writer local sequence with a zero
busy timeout: bounded lock failures, successful commit after holder release,
reopen, and integrity checks. Timing is explicitly not measured.

The result does **not** establish general SQLite concurrency, timeout or
busy-handler policy, compatibility, performance, durability, crash recovery,
power-loss behavior, checkpoint behavior, causality outside the scripted
sequence, or architecture superiority. It does not test nonzero timeout
values, alternate journal modes, more than two local writers, process crashes,
power loss, or a distributed/deployed environment. The optional finite-state
math view is a candidate consistency record, not a proof or canonical claim.

### MTH-0198 browser and performance audit

The browser audit is bounded to the existing local graph exploration surface.
Headed Chromium verification covered graph load, mode switching, accessible
Math Models labels, search/inspector behavior, exploratory path-panel copy,
hidden-node restore, catalog focus, and card relation metadata. Lighthouse was
run against the local production preview. These are local smoke observations,
not representative mobile-device or network metrics.

Firefox attachment, interactive saved two-endpoint paths, and pointer-targeted
edge selection were not measured; no pass is claimed for them. The 390 x 844
check used desktop Chromium in a small viewport, not a real mobile device.
No narrowly reproduced UI defect was fixed, and no API, relation, canonical
card, or production resource was changed.

## Protected-main and preservation checks

- Source commit: `24e458d4d1bb7227a568728e62a63398d1cf0b27` (`MTH-0199`).
- The release branch is based on `origin/main`; its protected-main diff is
  limited to the research wave artifacts listed above and their validators,
  schemas, tests, and documentation.
- `docs/audits/scope-context-pilot-mth-0151.json` and
  `docs/scope-context-pilot-mth-0151.md` are preserved unchanged.
- No files under `data/systems/`, `data/drafts/`, `apps/api/`, `apps/web/`, or
  `apps/mcp/` are changed by this release.
- No deployment workflow, Worker, D1 database, browser production resource,
  or secret is touched.

## Validation and limitations

The release uses the repository's deterministic validators and test suite.
Validation confirms artifact contracts and boundary fields; it does not turn
research observations into canonical evidence, infer human review, evaluate a
direct LLM, or broaden the bounded SQLite/browser conclusions. The required
CI matrix remains authoritative for cross-platform Python and local web/worker
checks. The release itself performs no deployment.

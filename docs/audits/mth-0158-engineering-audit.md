<!-- markdownlint-disable MD013 -->

# MTH-0158 final engineering audit

## Scope and basis

- Audit worktree: `carryctx/mth-0158-final`
- Audited commit: `3b8c161d1e68d1483b19da7ce823f3a03a27b55d`
- Comparison base: `origin/main` at `3b8c161d1e68d1483b19da7ce823f3a03a27b55d`
- Audit date: 2026-10-27
- No deployment, push, migration against a remote database, canonical-card
  edit, draft edit, or application-code edit was performed.

The worktree was clean at audit start. The audit generated only ignored local
build/database state and this report. The protected surfaces
(`data/systems/`, `data/drafts/`, `apps/api/migrations/`, seed code, and API,
web, and MCP application sources) are unchanged relative to `origin/main`.

## Result summary

| Area | Result | Evidence |
| --- | --- | --- |
| Reviewed-card validation | **PASS** | `uv run mathen validate`; 219 canonical cards validated |
| Python tests | **PASS** | 225 tests, 0 failures |
| Python format/lint | **PASS** | Ruff format check and lint passed |
| Retrieval manifest validation | **PASS** | MTH-0154 artifact and valid fixture validated |
| Retrieval evaluation rerun | **PASS with limitation** | Same 2,481-document corpus digest and metrics; generated artifact differs only in recorded `source_revision.commit` because the runner records `git rev-parse HEAD` |
| Lifecycle audit | **PASS** | Read-only audit over 219 cards, 830 features, and 608 views; no inferred lifecycle or promotion |
| Relation audit | **PASS** | Read-only audit; 46 typed relations, 0 closure issues, no proposal conflict, no mutation |
| Relation candidate generation | **PASS** | Read-only report: 219 cards, 398 candidates, 46 existing relations |
| Mathematical-view validation | **PASS** | 2 standalone SQLite contracts validated |
| TypeScript checks | **PASS** | API, web, and MCP `tsc --noEmit` passed after locked dependency install |
| API tests | **PASS** | 59 tests, 0 failures |
| Web tests | **PASS** | 46 tests, 0 failures |
| MCP tests | **PASS** | 23 tests, 0 failures |
| Web build | **PASS with warning** | Vite build passed; existing 3D graph chunk exceeds 500 kB |
| Local D1 migrations and seed | **PASS** | `bun run db:reset:local` passed; local D1 contains 219 systems and 1,531 evidence records |
| Actionlint | **PASS** | `actionlint .github/workflows/*.yml` produced no diagnostics |
| Gitleaks | **PASS** | 447 commits / ~23.68 MB scanned; no leaks found |
| Git diff check | **PASS** | `git diff --check origin/main...HEAD` passed |
| YAML lint | **PASS with warnings** | Existing line-length warnings only; exit status 0 |
| Production deployment | **UNKNOWN / not exercised** | Remote D1, Cloudflare Worker, R2, Turnstile, and hosted API/MCP were intentionally not contacted |

## Boundary and safety audit

### Canonical versus drafts

**PASS.** The audit found 219 tracked canonical cards and 45 tracked draft
cards. The MTH-0154 changes add research artifacts and evaluation code only;
they do not add or alter either card corpus. The retrieval validator requires
`canonical_cards`, `reviewed_only: true`, and `data/systems/...` source
references. API and MCP retrieval tests reject draft provenance and keep
retrieval results read-only. Modeling code continues to target
`data/drafts/<system-id>.json` and explicitly requires human review before
promotion.

### No automatic relation inference or promotion

**PASS.** The relation audit reports typed coverage and closure; it does not
write edges. Relation-candidate generation reports candidates separately from
existing relations. The audit found 46 existing typed relations in the
canonical corpus and 0 `feature_relations` rows in the freshly seeded local
D1, which is consistent with the current cards rather than an inferred graph
write. Retrieval warnings and tests state that scores do not add graph edges.
The retrieval result boundary requires `canonical: false`,
`promotion_requires_human_review: true`, and `storage_scope: research-only`.

### Evidence, metadata, and scope propagation

**PASS.** Retrieval documents carry source references, source digests, claim
metadata, validity/scope metadata, and evidence IDs. The manifest validator
checks evidence locality, digest linkage, split/holdout separation, bounded
results, and null semantics. API, web, and MCP checks passed, including
metadata propagation and retrieval-contract tests. Relation closure found all
relation evidence source-local and all relation targets reviewed. No relation
scope context was silently invented; the audit reports that relation schema
support is not present and typed relations have zero scope-context records.

### Migrations, seed safety, and deployment documentation

**PASS for local/static checks; UNKNOWN for remote operation.** All seven D1
migrations applied during `bun run db:reset:local`, followed by deterministic
seed validation. The seed reads only `data/systems`, modeling bundles, and
validated graph documents; it does not read `data/drafts`. Local D1 schema
inspection found the expected tables and feature-relation evidence-integrity
triggers. Deployment workflow and `docs/hosting.md` keep migrations, Worker
deployment, public variables, and Wrangler secrets as separate steps. No
remote migration or deployment was run.

### Secret, path, and artifact leakage

**PASS for new audit/retrieval work; limitation recorded.** Gitleaks found no
secret. Retrieval/MCP tests cover omission of private queries, credentials,
upstream bodies, and URL passwords. The new evaluation artifact contains no
provider/model payload, vector, secret, or production binding. Existing
canonical records contain historical `/tmp/opencode/...` checkout paths in
evidence notes (`authentik`, `oauth2-proxy`, `pytorch`, and `tensorflow`), and
the repository already contains historical audit paths. These paths are
unchanged from `origin/main` and are not introduced by MTH-0158; they remain a
pre-existing portability/privacy limitation rather than an audit regression.

## Retrieval reproducibility note

Running `scripts/retrieval_evaluation.py` at this audit commit produced the
same 2,481 documents and corpus digest (`sha256:f29de96a7fee3706c9b5d1d0623b84a17e3d852caf337d47cd9f1f1beb5eff5a`) as the committed
MTH-0154 artifact. The JSON differed only at:

```text
/corpus_snapshot/source_revision/commit
```

The committed artifact records `c0a34014...`; a fresh run records the current
`a70c3794...`. This is expected from the runner's explicit current-`HEAD`
provenance, but it means a byte-for-byte rerun requires running at the recorded
source revision (or supplying a fixed revision to the runner). It is not a
corpus or metric mismatch. The committed artifact itself validates.

## Limitations and unresolved items

1. This audit did not contact remote Cloudflare/D1/R2/Turnstile or hosted
   API/MCP. A separate commander-controlled MTH-0157 read-back verified the
   deployed metadata propagation and recorded its production results.
2. The two standalone mathematical-view contracts are bounded SQLite
   observations; they do not establish crash durability, universal recovery,
   theorem, or proof claims.
3. Retrieval operational metrics such as latency, provider errors, provider
   calls, and cost are intentionally null/not applicable for the offline
   lexical evaluation.
4. The web build emits the existing large-chunk warning. It does not fail the
   build and is unrelated to the MTH-0154 research artifact.
5. YAML lint emits existing line-length warnings. Actionlint and the workflow
   parser pass.
6. Existing canonical evidence notes contain absolute temporary checkout paths
   as described above; this audit did not rewrite canonical cards.

## Final disposition

**Audit outcome: PASS with the explicit limitations above.** No concrete
blocking defect in the audited MTH-0154 changes was found. No canonical card,
draft, migration, production resource, or application source was changed.

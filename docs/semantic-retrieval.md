# Evidence-bounded semantic retrieval

**Status:** implementation-ready design; the first public MVP is implemented as
a provider-neutral bounded lexical baseline over hydrated D1 records. It is not
an embedding or ANN implementation.

**Scope:** reviewed-card discovery for the API, browser, and read-only MCP
surfaces. This design does not add a dependency, create a Cloudflare resource,
change the card schema, index drafts, or promote generated output.

## 1. Boundary and vocabulary

Semantic retrieval answers **"which reviewed records should a reviewer inspect
first?"** It does not answer **"is this claim true?"** or **"can these systems
compose?"**. An embedding score is a discovery/ranking signal only. It is never
evidence of truth, compatibility, causality, originality, substitutability,
implementation dependency, or historical influence. A nearest neighbour is not
an implicit graph edge.

The retrieval service must preserve the distinctions already used by Mathen:

- `fact` — directly supported by cited evidence;
- `inference` — an abstraction derived from facts;
- `hypothesis` — a model requiring validation; and
- `analogy` — a bounded comparison, not a formal equivalence.

Every returned claim-bearing item retains its `claim_type`, review status,
source-local `evidence_ids`, validity scope, deployment-origin scope, and
provenance. A result may be useful even when it is `under-review` or a
`hypothesis`; the response must make that status visible and must not upgrade
it.

## 2. Facts from the current repository

These are observations, not proposed changes:

1. `data/systems/` is the reviewed canonical card tree. Drafts are in separate
   locations and the hosted API/MCP surfaces deliberately do not expose them
   (`AGENTS.md`, `docs/hosting.md`, `docs/mcp.md`).
2. D1 stores normalized systems, features, evidence, views, relations, and
   composition data. The seed script reads reviewed cards and uses a destructive
   replacement of the target database (`apps/api/migrations/0001_initial.sql`,
   `apps/api/scripts/seed.ts`).
3. The API is rooted at `/api`, returns successful reads in a `{ "data": ... }`
   envelope, and currently exposes lexical/system, feature, relation,
   composition, modeling, and graph reads (`apps/api/src/index.ts`).
4. Browser code uses same-origin `/api/*` requests. It must not receive a
   deployment-specific API URL (`docs/hosting.md`, `apps/web/src/main.ts`).
5. Hosted MCP is stateless, read-only, protected by exact Bearer matching, and
   emits CORS headers only for origins in the exact `MCP_ALLOWED_ORIGINS`
   allowlist. The stdio client can use `MATHEN_API_URL` and sends
   `MATHEN_API_TOKEN` as a Bearer credential (`apps/api/src/mcp.ts`,
   `apps/mcp/src/backend.ts`).
6. Graph projection copies claim metadata, evidence IDs, provenance, and
   deployment validity scope; it does not infer relations from names, vectors,
   categories, or layout (`docs/graph-layer-projection.md`).
7. MTH-0118 already defines lexical, vector, graph, and combined baselines.
   Retrieval metrics must report evidence locality, claim discipline,
   scope/provenance completeness, abstention, and false-link outcomes rather
   than treating retrieval recall as truth (`docs/mth-0118-benchmark-harness.md`,
   `docs/mth-0118-synthesis-validation-benchmark.md`).
8. The current Wrangler configuration has D1 and R2 bindings but no Vectorize
   binding. Hosting documentation describes Vectorize as optional and planned,
   not as an existing integration (`apps/api/wrangler.jsonc`,
   `docs/hosting.md`).

## 3. Design decisions

### 3.1 Corpus and eligibility

The default corpus is a **snapshot of reviewed canonical content only**:

- include cards loaded from `data/systems/` and the corresponding reviewed D1
  rows;
- include only records that pass the existing schema and semantic validation;
- include card summaries, scopes, features, mathematical views, trade-offs,
  explicitly declared relations, compositions, and reviewed standalone
  microstructure/analogy documents when a later corpus configuration opts into
  those document kinds;
- exclude `data/drafts/**`, `data/drafts/llm/**`, analyses, benchmark manifests,
  prompts, private operator artifacts, and unreviewed graph candidates;
- do not use a draft to fill a missing canonical record;
- do not modify or overwrite `data/systems/` while building or rebuilding.

The initial implementation should ship with `canonical_cards` as the only
enabled corpus. Additional reviewed document kinds require an explicit corpus
configuration and the same review/evidence checks. A query cannot request
drafts through an API or MCP argument.

### 3.2 Stable document identity and source closure

The vector ID is a stable logical identity, not a hash of an embedding. Use
ASCII-safe IDs with a bounded length, for example:

- Card summary: ID `system:<system_id>:summary`; hydrate from `systems` and the
  full card.
- Feature: ID `system:<system_id>:feature:<feature_id>`; hydrate from
  `features`.
- Mathematical view: ID `system:<system_id>:view:<stable_view_id>`; hydrate
  from `mathematical_views`.
- Trade-off: ID `system:<system_id>:tradeoff:<feature_id>`; hydrate from
  `trade_offs`.
- Explicit system relation: ID
  `system:<system_id>:relation:<ordinal-or-digest>`; hydrate from the owning
  card relation.
- Composition: ID `system:<system_id>:composition`; hydrate from the owning
  card composition.
- Reviewed standalone document: ID `<kind>:<document_id>`; hydrate from its
  reviewed document table.

`stable_view_id` is the D1 ID where available, otherwise the existing
deterministic projection key. An ordinal is valid only if the source serializer
has a stable ordering; a canonical digest-based suffix is preferred when a
relation can be reordered. IDs are unique within one index and are not reused
for a different record kind.

Each document stores a `source_ref` (`system_id`, `record_kind`, optional
`record_id`) and a `source_digest` computed from canonical normalized source
fields. The source digest is separate from the index/build digest. Search
results are hydrated by `source_ref` from D1 before being returned; the index
never becomes a second card store. If hydration fails, omit the result and emit
an observable `stale_source_ref` warning rather than returning unsupported
prose.

### 3.3 Representation and chunking

Use **atomic, claim-bearing records**, not arbitrary token windows. One card
summary, feature, view, relation, trade-off, or composition is one retrieval
document. A large feature description may be split only at a semantic boundary;
all child chunks share a `parent_ref`, carry a `chunk_ordinal`, and repeat the
parent's metadata and evidence closure. Do not split an evidence citation away
from the claim it supports.

The embedded text is a deterministic template, for example:

```text
system: duckdb
record: feature embedded-execution
name: Embedded execution
category: deployment
summary: <canonical description>
benefits: <canonical benefits>
costs: <canonical costs>
scope: <card scope>
version_context: <version context>
claim_type: fact
claim_status: accepted
validity_scope: <canonical scope, when present>
evidence_ids: <sorted local IDs>
```

The template must not invent synonyms, conclusions, relation types, or
evidence. Keep human-readable text separate from metadata. Store enough
metadata to filter before ANN search and enough source references to hydrate
the complete canonical record after ANN search.

Required metadata (names are an implementation contract, not a D1 schema
change) is:

```json
{
  "corpus": "canonical_cards",
  "document_id": "system:duckdb:feature:embedded-execution",
  "record_kind": "feature",
  "system_id": "duckdb",
  "feature_id": "embedded-execution",
  "claim_type": "fact",
  "claim_status": "accepted",
  "version_context": "1.4",
  "deployment_origins": ["local", "cloud"],
  "source_digest": "sha256:...",
  "source_ref": "data/systems/duckdb.json#features/embedded-execution",
  "evidence_ids": ["duckdb-why"]
}
```

`evidence_ids` is metadata for closure checking and display, not a substitute
for the evidence records. Evidence records are resolved from the owning card
and returned with the result where the existing API contract does so.

### 3.4 Filters and scope semantics

Filters are applied before or during vector search, never after silently
changing the meaning of the result. The initial allowlist is:

- `record_kind`: `system`, `feature`, `view`, `trade_off`, `relation`, or
  `composition`;
- `system_id`, `feature_id`, and `category`;
- `claim_type` and `claim_status`;
- `version_context` (exact value or configured version family);
- `deployment_origin` (membership in the record's declared
  `validity_scope.deployment_origins`); and
- `corpus` (server-forced to `canonical_cards` for public reads).

An absent deployment-origin scope remains visible to an origin-filtered query,
matching graph behavior: an unscoped record is not falsely assigned to an
origin. A scoped record is eligible only when the requested origin is listed.
Version and condition filters are conservative: unknown/missing values do not
match an exact filter. Filters must be reported in the response so a reviewer
can distinguish "no candidate" from "not in scope".

Do not expose arbitrary provider filter expressions. Parse the allowlisted
fields, reject unknown fields, cap list lengths, and use an explicit
`deployment_origin` rather than trusting a client-supplied deployment name.

### 3.5 Embedding and index lifecycle

An index build is a deterministic, replaceable publication produced from a
canonical snapshot:

1. export normalized eligible records from D1 (or the reviewed card tree for a
   local/offline build);
2. validate every source card and verify every local evidence ID;
3. render deterministic text and metadata;
4. compute `source_digest` values and a sorted corpus manifest digest;
5. embed with one declared provider/model, dimensions, distance metric,
   normalization rule, and template version;
6. upsert into a new versioned index/namespace, never into the active index;
7. sample IDs and hydrate them from D1; verify counts, dimensions, metadata,
   evidence closure, and absence of draft paths;
8. atomically switch an active-index pointer only after verification; and
9. retain the previous verified version until the new version has passed a
   read smoke test and a configured retention window.

The build manifest must include:

```json
{
  "manifest_version": "1.0",
  "index_id": "canonical-cards-2026-10-25T...",
  "corpus": "canonical_cards",
  "corpus_digest": "sha256:...",
  "source_snapshot": { "d1_export_digest": "sha256:..." },
  "schema_version": "architecture-card@current",
  "representation_version": "canonical-record-v1",
  "embedding": {
    "provider": "declared-provider",
    "model_id": "declared-model",
    "dimensions": 768,
    "metric": "cosine",
    "normalized": true
  },
  "counts": { "documents": 0, "chunks": 0 },
  "created_at": "RFC3339",
  "status": "verified"
}
```

The actual provider/model remains an unresolved deployment choice. The source
and representation digests, not a provider default, determine whether a
rebuild is required. Any change to card content, eligibility, template,
embedding model, dimensions, distance metric, or metadata schema creates a new
index version. A failed build does not change the active pointer.

Prefer full rebuilds for the first implementation. Incremental upserts are an
optimization only when deletion, stale-record detection, and manifest
verification are equivalent to a full rebuild.

### 3.6 Query and response contract

The recommended read route is `GET /api/retrieval`, chosen to avoid changing
the meaning of existing lexical `/systems` and `/features` routes. It is
read-only and has no draft argument. Query parameters:

- `q`: required UTF-8 query, trimmed, 1–1,000 characters; never logged in full.
- `limit`: optional integer, default 10, maximum 50.
- `record_kind`: optional repeated/CSV allowlisted value.
- `system_id`, `feature_id`, `category`: optional exact values.
- `claim_type`, `claim_status`: optional controlled values.
- `version_context`: optional exact value.
- `deployment_origin`: optional exact origin filter.

Successful responses preserve the API envelope:

```json
{
  "data": {
    "schema_version": "1.0",
    "query": { "q_digest": "sha256:...", "filters": {} },
    "index": {
      "status": "ready",
      "index_id": "canonical-cards-...",
      "corpus": "canonical_cards",
      "representation_version": "canonical-record-v1"
    },
    "results": [
      {
        "rank": 1,
        "score": 0.81,
        "score_kind": "embedding_similarity",
        "document": {
          "id": "system:duckdb:feature:embedded-execution",
          "record_kind": "feature",
          "system_id": "duckdb",
          "feature_id": "embedded-execution",
          "name": "Embedded execution",
          "description": "...",
          "claim_type": "fact",
          "claim_status": "accepted",
          "evidence_ids": ["duckdb-why"],
          "validity_scope": { "deployment_origins": ["local"] }
        },
        "evidence": [{ "id": "duckdb-why", "kind": "...",
          "title": "...", "uri": "..." }],
        "provenance": {
          "source_ref": "data/systems/duckdb.json#features/embedded-execution",
          "source_digest": "sha256:...",
          "retrieval_method": "vector"
        }
      }
    ],
    "warnings": []
  }
}
```

The service must not return generated summaries in place of the hydrated
canonical document. `score` is uncalibrated ranking output and must be labeled
as such in API types, MCP tool descriptions, and Web UI copy. Ties are sorted
deterministically by `document.id` after score ordering. A result with missing
or invalid evidence closure is excluded, not repaired by retrieval.

The equivalent hosted MCP read tool is `search_semantic`. Its arguments mirror
the allowlisted query parameters and it returns the same `data` object as JSON
text inside the normal MCP `tools/call` result. It is available only in the
existing reviewed, stateless, exact-Bearer MCP boundary. The stdio filesystem
backend may implement it later against a local verified index, but it must
retain the same corpus and result contract.

### 3.7 Readiness, failures, and empty indexes

Use distinct states:

- **ready:** active verified index and D1 are reachable; return results or an
  empty result set;
- **empty:** verified index has zero eligible documents; return HTTP 200 with
  `index.status = "empty"`, `results = []`, and a warning. Do not claim that
  no relevant architecture exists;
- **unavailable:** no active pointer, index query failure, provider timeout, or
  D1 hydration failure above the configured threshold. Return HTTP 503 with
  `{ "error": "Semantic retrieval is unavailable", "code":
  "semantic_index_unavailable", "request_id": "..." }` and do not silently
  fall back to an unbounded or draft corpus;
- **invalid request:** malformed query/filter/limit, HTTP 400; and
- **not authorized:** use the existing API access protection and MCP 401/403
  behavior, without a retrieval-specific credential in browser code.

Clients should display an unavailable/empty state and retain lexical browsing as
an explicit separate action. A hidden lexical fallback would make evaluation
and provenance ambiguous. Every response/error gets the existing request ID
observability treatment; query text and bearer credentials must not be put in
that ID or logs.

## 4. Cloudflare-compatible deployment options

These are options for a later implementation, not resources to create in this
task:

1. **Cloudflare Vectorize (recommended first managed adapter).** A Worker
   binding can query a versioned index and use metadata filters. Keep one
   active version per environment, or use a namespace when the provider's
   limits and isolation model are verified. Current Cloudflare documentation
   describes metadata filtering, namespace limits, a 1,536-dimension maximum,
   10 KiB metadata per vector, and a maximum `topK` of 50 when returning
   metadata/values. The adapter must enforce the lower Mathen limits above and
   never put the whole card/evidence text into metadata.
2. **External managed vector service.** A Worker adapter can call a provider
   over HTTPS, but provider credentials stay in Worker secrets and the service
   contract must still return only D1-hydrated reviewed records. Provider
   outages have the same unavailable behavior; no provider-specific response
   format leaks into API/MCP.
3. **Cloudflare Workers AI embeddings plus Vectorize.** Embedding generation
   can happen in a controlled rebuild job or Worker workflow if model
   availability, dimensions, limits, and data handling are verified. Do not
   run unbounded corpus generation in a request handler.
4. **Offline/CI generation plus R2 artifact delivery.** Generate and verify
   vectors outside the request path, store the manifest/build artifact in the
   existing release-scoped artifact boundary, then publish to a managed index.
   R2 is not the query source of truth and must not replace D1.
5. **D1 lexical fallback.** Existing SQL search remains a useful explicit
   baseline and availability fallback for a UI action, but it is not semantic
   retrieval and must be labeled/metered separately.

Cloudflare Workers request handlers should perform bounded query embedding and a
single bounded ANN request only. Rebuilds belong to CI/operator workflows or a
durable job mechanism selected later; this task creates no binding, index,
secret, queue, or remote resource.

## 5. Privacy, secrets, cost, and limits

- Canonical cards and their evidence URIs are the only default indexed content.
  Do not index credentials, local paths containing secrets, prompts, drafts,
  private analysis, or raw request headers.
- A query can contain sensitive research text. Do not persist it by default;
  log only a short digest, request ID, bounded timing, status, and index ID.
  Document any provider's retention/training policy before sending query text or
  card content outside the deployment.
- Browser requests remain same-origin. Do not expose `API_ACCESS_TOKEN`, an
  embedding-provider key, or a provider endpoint in Vite code. Hosted MCP uses
  the existing exact Bearer token and exact CORS allowlist.
- Build-time embedding credentials, if needed, are CI/Worker secrets and never
  enter manifests, cards, vectors' metadata, logs, or MCP output. Rotate them
  using the existing deployment secret process.
- Enforce the query, limit, metadata, and timeout bounds in Section 3.6. Add
  per-IP/API rate limiting using the existing defense-in-depth controls and
  Cloudflare WAF for distributed protection.
- Cache embeddings by `(query_digest, embedding_model_id, dimensions)` only in
  an approved private cache; cache result envelopes by index ID plus normalized
  query/filter digest if caching is enabled. Never cache across corpus or
  deployment-origin scopes.
- Track build document count, embedding calls/tokens (provider-specific),
  index storage, query count, p50/p95 latency, error rate, empty rate, and
  hydration drops. Budget and alert before enabling automatic rebuilds.

## 6. Versioning, rollback, and invalidation

The active pointer is an operational publication record, not canonical domain
data. It must point to a manifest whose corpus digest matches the verified
source snapshot. Pointer updates are atomic and auditable. A rollback selects a
previous verified pointer; it does not rewrite cards or D1.

Invalidate/rebuild on any of:

- reviewed card add, removal, or content change;
- evidence ID, claim type/status, scope, version, or deployment-origin change;
- representation/chunking/template change;
- embedding model, dimensions, metric, normalization, or provider change; or
- index metadata/filter schema change.

A source digest mismatch during query hydration is a stale index condition.
Return the healthy results that can be hydrated only if the response includes a
`stale_index` warning and the deployment policy permits it; the conservative
default is to mark the index unavailable and rebuild. Never silently present a
stale claim as current.

## 7. Evaluation and acceptance criteria

### Backend acceptance

- [ ] The builder can prove that every indexed ID belongs to the reviewed
  canonical corpus and that no draft/analysis/prompt path was included.
- [ ] Rebuilding the same canonical snapshot with the same representation and
  embedding configuration produces the same manifest, IDs, text, and metadata
  (apart from explicitly documented timestamps).
- [ ] Every vector result has a valid source reference, source digest, claim
  metadata, evidence IDs, and a successful D1/card hydration check.
- [ ] Unknown filters, out-of-range limits, overlong queries, and malformed
  origin values are rejected deterministically.
- [ ] Active-index publication is atomic; failed or partial rebuilds cannot
  become active; rollback is possible without changing D1.
- [ ] Empty, unavailable, stale, and unauthorized states are distinguishable
  and covered by tests.
- [ ] The adapter enforces provider top-K/metadata/dimension limits rather than
  relying on provider errors.

### API/Web acceptance

- [ ] `GET /api/retrieval` preserves the `{data: ...}` success envelope and the
  response contract in Section 3.6.
- [ ] Browser use is same-origin and no new public API URL or secret is needed.
- [ ] UI labels scores as ranking signals and exposes claim type, status,
  evidence, scope, source, and warnings; it does not render similarity as a
  relation, compatibility, or proof.
- [ ] Existing lexical routes and mobile/graph behavior are unchanged.

### MCP acceptance

- [ ] `search_semantic` is read-only, reviewed-only, stateless, and unavailable
  without the existing exact Bearer token on hosted MCP.
- [ ] Exact configured CORS behavior is retained; no wildcard is introduced
  for browser origins.
- [ ] MCP normalization preserves the same IDs, scores, claim metadata,
  evidence records, validity scope, and warnings as the API.
- [ ] Draft arguments are rejected or absent in tool definitions.

### Release acceptance

- [ ] No dependency or Cloudflare resource is added by the design/backend
  change without a separately approved implementation task.
- [ ] Manifest, index, and deployment environment are recorded without
  credentials; release readback verifies the active pointer and a sample query.
- [ ] D1 remains the source of truth and a rebuild can recreate the index from
  reviewed data after deleting the semantic index.

## 8. Minimal implementation and evaluation plan

1. **Contract tests first:** define fixture cards containing all four claim
   types, evidence references, temporal/version data, deployment origins, one
   explicit analogy, and one rejected/draft decoy. Assert eligibility,
   identity, deterministic text, metadata closure, and draft exclusion.
2. **Fake-index adapter tests:** use an in-memory adapter to test pre-filtering,
   deterministic tie ordering, source hydration, stale/missing evidence
   handling, bounded limits, and empty/unavailable states without a provider.
3. **API tests:** add route tests for the success envelope, all filters, 400/401/
   403/503 cases, request IDs, no query logging, and unchanged existing routes.
4. **MCP tests:** extend the existing JSON-RPC fixture backend and assert the
   tool schema, exact argument forwarding, reviewed-only output, Bearer auth,
   CORS allowlist, and unavailable/empty tool errors.
5. **Web tests:** test only the retrieval result/state component and warning
   copy; verify no graph edge, mobile layout, or navigation behavior changes.
6. **Benchmark harness:** add a retrieval protocol manifest or adapter to the
   MTH-0118 harness. Compare lexical, vector-only, graph, and vector-plus-graph
   discovery under identical evidence/scope partitions. Report per-query
   recall@k and nDCG only as discovery metrics, alongside evidence locality,
   citation precision, claim-type accuracy, scope completeness, false-link
   rate, abstention/unknown recall, and graph/vector complementarity. Keep
   negative-knowledge and holdout records out of candidate generation.
7. **Release smoke test:** build a disposable index from the reviewed fixture,
   verify the manifest and active pointer, query through API and MCP, delete the
   disposable index, and rebuild it from D1 without changing D1 rows.

## 9. Hypotheses to test

- Atomic claim-bearing records will improve evidence locality and reviewer
  usefulness over arbitrary text windows, at the cost of less lexical context.
- Metadata pre-filtering for claim type, version, and deployment origin will
  reduce false candidates more effectively than score thresholds alone.
- Vector and typed-graph discovery will be complementary across terminology
  variants, but vector candidates will also increase unsupported analogy/bridge
  proposals unless evidence review remains mandatory.
- Full canonical-card hydration will make results more trustworthy to reviewers
  than returning snippets, without turning retrieval into a proof mechanism.
- A versioned replace-and-switch index will be simpler and safer than
  in-place incremental mutation at the current catalogue size.

These are research hypotheses, not guarantees. MTH-0118 metrics and reviewer
adjudication must test them by task and scope, not by a single aggregate score.

## 10. Unresolved choices

1. Which embedding provider/model meets Mathen's privacy, language, dimension,
   cost, and latency requirements? The provider must be declared in every build
   manifest and cannot be selected implicitly by a Worker default.
2. Whether Vectorize, an external service, or a self-hosted adapter is the
   first production index. The API/MCP contract must stay provider-neutral.
3. Whether source/build manifests live only in release artifacts or receive a
   small D1 operational metadata table. Either option must keep the active
   pointer out of canonical card semantics and remain rebuildable.
4. Whether standalone reviewed microstructures and analogies join the initial
   corpus. The safe default is cards/features/views only until their review and
   scope UX is agreed.
5. Whether a later API should add cursor pagination or a POST query for richer
   filters. The first route remains bounded GET for cacheability and consistency
   with current read routes.
6. The exact stale-index policy: fail closed on any source digest mismatch or
   return individually verified results with a warning. Fail closed is the
   recommended initial policy.
7. The rebuild trigger and operator ownership (release workflow, scheduled job,
   or explicit command). No automatic trigger should be enabled before cost,
   rollback, and observability gates are accepted.

## 11. First-public-MVP implementation note

The initial `GET /api/retrieval` implementation deliberately does not select an
embedding provider, create a Vectorize binding, add a secret, or add a remote
index. It builds a bounded deterministic `canonical_cards` document snapshot
from the reviewed D1 tables for each request, applies allowlisted filters before
ranking, and uses token-overlap ranking with deterministic ID tie-breaking. The
response labels this as `bounded_lexical_baseline`; its scores are discovery
signals only and are not `embedding_similarity`.

The implementation is usable for public reviewed-card discovery while the D1
binding is reachable. It fails closed on missing evidence closure by omitting
the document and reporting `stale_source_ref`, and returns `503
semantic_index_unavailable` when D1 access fails. A later embedding adapter must
replace the ranking/index layer without changing the D1 hydration, corpus,
filter, evidence, scope, provenance, or API envelope contracts. True semantic
retrieval still requires a separately approved provider/model, privacy and
retention review, versioned rebuild workflow, active-index publication, and
deployment configuration.

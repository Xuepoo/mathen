<!-- markdownlint-disable MD013 -->

# Mathen MCP Server

Mathen includes a local stdio MCP server for reading the architecture knowledge
base from an agent host. It is intentionally read-only: generated drafts must
pass the Python validation and human review workflow before they become
canonical system cards.

## Hosted endpoint direction

The hosted MCP endpoint is a remote HTTPS service:

```text
https://mathen.xuepoo.xyz/api/mcp
```

The route is `/api/mcp`, under the same `/api` prefix as the read API. Python
CLI users can set `mcp.url` in TOML or override it with `MATHEN_MCP_URL`.

The endpoint is stateless and reviewed-only. It accepts the legacy
`API_ACCESS_TOKEN` Bearer credential and can additionally accept an Auth0
access token when `AUTH0_ISSUER` and `AUTH0_AUDIENCE` are configured. Auth0
acceptance is limited to this hosted MCP endpoint; it does not bypass
Turnstile or the signed access cookie on ordinary `/api/*` routes. The
endpoint supports JSON Streamable HTTP requests for `initialize`, `tools/list`,
and `tools/call`. It does not expose filesystem-only drafts. Use the stdio
server below for offline filesystem access.

For hosted requests, the exact authentication header is:

```http
Authorization: Bearer <API_ACCESS_TOKEN>
```

The value must match the configured Worker secret exactly. For Auth0, configure
`AUTH0_ISSUER`, `AUTH0_AUDIENCE`, and optionally `AUTH0_JWKS_URI` and
`AUTH0_REQUIRED_SCOPE` as Worker variables. The JWKS endpoint must be HTTPS; if
`AUTH0_JWKS_URI` is omitted, the issuer's `/.well-known/jwks.json` endpoint is
used. Protected-resource metadata is public at:

```text
GET https://mathen.xuepoo.xyz/api/.well-known/oauth-protected-resource
```

An unauthenticated or invalid-token MCP response advertises that exact URL in
`WWW-Authenticate`. Do not put a real token in a URL, source file, browser
bundle, card, issue, or log. The hosted endpoint is read-only and this
repository does not claim that production MCP authentication has been
verified; operators must provision credentials and run their own deployment
smoke test.

If a request includes `Origin`, it must exactly match one of the comma-separated
`MCP_ALLOWED_ORIGINS` values. The current implementation also accepts an
explicit `*` entry. With an empty allowlist, no-`Origin` requests are allowed,
while browser-origin requests are rejected. CORS response headers are emitted
only for an allowed origin, and `OPTIONS` uses the same rule.

## Start

From the repository root:

```bash
bun install
bun run mcp
```

The server communicates through stdin/stdout using MCP JSON-RPC. Configure an
MCP client to launch `bun run mcp` with the repository as its working
directory. `MATHEN_ROOT` can override repository discovery when the command is
launched from another directory.

To use the deployed Hono API instead of local files, set `MATHEN_API_URL` to
the API origin or `/api` base URL before starting the server:

```bash
MATHEN_API_URL=https://mathen.xuepoo.xyz/api bun run mcp
```

API mode uses `GET /api/systems`, `GET /api/systems/:id`, `GET /api/features`,
`GET /api/feature-relations`, `GET /api/compositions`, `GET /api/graph/layers`,
`GET /api/modeling/:id`, and `GET /api/retrieval`. Requests have a
10-second timeout and API
failures are returned as concise JSON tool errors. Draft cards are
filesystem-only and are not exposed by the MCP tools or graph projection.

The source registers `search_semantic` on hosted and stdio MCP. The legacy
tool name does **not** imply semantic similarity: the first MVP is a **bounded
lexical baseline**, not embeddings or vector search. Availability on a deployed
endpoint requires an operator deployment and readback; source implementation
alone is not a production deployment claim.

In API mode the stdio tool forwards `q` (trimmed, 1–1,000 characters), `limit`
(default 10, maximum 50), and the allowlisted `record_kind` (CSV), `system_id`,
`feature_id`, `category`, `claim_type`, `claim_status`, `version_context`, and
`deployment_origin` filters to same-contract `GET /api/retrieval`. Unknown or
draft arguments are rejected; the tool schema has `additionalProperties: false`.
Its JSON text is the API envelope's `data` object, matching hosted MCP. IDs,
rank order, scores, `score_kind: lexical_overlap`, hydrated documents, claim
types/statuses, evidence, validity/deployment scope, source references/digests,
`bounded_lexical_baseline` provenance, index metadata, and warnings are retained.
Absent claim metadata stays absent; retrieval does not promote a claim.

Scores are **uncalibrated discovery ranking signals**, not semantic proof,
compatibility, relation, causality, originality, or historical influence. No graph
edge is inferred. Ready queries with no matches and an empty reviewed corpus are
successful responses with distinct index states. API failures return sanitized
tool errors without query text, credentials, URLs, or upstream error bodies.

Filesystem mode exposes the same tool/arguments but returns an explicit
`semantic_index_unavailable` tool error: no verified local retrieval index is
implemented. It does not read drafts or silently fabricate a local index or run a
fallback. Configure `MATHEN_API_URL` for retrieval, or explicitly use the separate
`list_systems` / `search_features` tools for offline browsing.

If the deployed API has Turnstile protection enabled, configure the matching
read-only service token with `MATHEN_API_TOKEN`. The token is sent as a Bearer
credential and is never stored in cards or MCP output. Browser Turnstile
cookies are intentionally not used by the stdio client.

The Hono API also exposes `GET /api/feature-relations` for focused relation
queries; system detail responses include the source card's relation array.

## Tools

- `list_systems`: list reviewed cards;
- `get_layered_graph`: retrieve the deterministic reviewed-only layered graph;
- `get_system`: retrieve one reviewed card;
- `search_features`: find reusable features by text and optional category;
- `search_semantic`: bounded lexical discovery over reviewed canonical records
  in API mode; explicitly unavailable in filesystem mode (see above);
- `list_feature_relations`: list source-card-owned feature relations with optional
  system, feature, target-system, and relation-type filters. Results preserve
  source-card claim metadata and source-local evidence IDs;
- `list_compositions`: find reviewed composition proposals by input system or claim status;
  each result includes the cited `evidence` records resolved from the owning card;
- `get_modeling_bundle`: retrieve a fixed-commit evidence bundle for semantic
  modeling.

Tool errors are returned as JSON text so an agent can inspect missing IDs or
files without receiving an unstructured process failure. Drafts are never
included in MCP output.

`list_feature_relations` is a read-only query. It does not infer a relation,
select its type, change claim status, or write to a card. The same
source-card-owned relation array is included by `get_system` when present.

## Boundary

The MCP process reads the repository filesystem when `MATHEN_API_URL` is unset.
When it is set, reviewed system, feature, and modeling-bundle reads use the
Hono/D1 API. Write and promotion operations are deliberately absent until an
authenticated review workflow exists.

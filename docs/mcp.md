# Mathen MCP Server

Mathen includes a local stdio MCP server for reading the architecture knowledge
base from an agent host. It is intentionally read-only: generated drafts must
pass the Python validation and human review workflow before they become
canonical system cards.

## Hosted endpoint direction

The hosted MCP endpoint is a remote HTTPS service:

```text
https://mathen.example.com/api/mcp
```

Replace the example origin with your deployment. The route is `/api/mcp`, under
the same `/api` prefix as the read API. Python CLI users can set `mcp.url` in
TOML or override it with `MATHEN_MCP_URL`; no hosted origin is built in.

The endpoint is stateless and reviewed-only. It requires the `API_ACCESS_TOKEN`
Bearer credential and supports JSON Streamable HTTP requests for `initialize`,
`tools/list`, and `tools/call`. It does not expose filesystem-only drafts. Use
the stdio server below for offline filesystem access.

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
MATHEN_API_URL=https://mathen.example.com/api bun run mcp
```

API mode uses `GET /api/systems`, `GET /api/systems/:id`, `GET /api/features`,
`GET /api/feature-relations`, `GET /api/compositions`, and `GET /api/modeling/:id`. Requests have a
10-second timeout and API
failures are returned as concise JSON tool errors. Draft cards are
filesystem-only, so `include_drafts: true` returns an explicit
unsupported-backend error when `MATHEN_API_URL` is set.

If the deployed API has Turnstile protection enabled, configure the matching
read-only service token with `MATHEN_API_TOKEN`. The token is sent as a Bearer
credential and is never stored in cards or MCP output. Browser Turnstile
cookies are intentionally not used by the stdio client.

The Hono API also exposes `GET /api/feature-relations` for focused relation
queries; system detail responses include the source card's relation array.

## Tools

- `list_systems`: list reviewed cards, or include drafts explicitly;
- `get_system`: retrieve one reviewed card or explicitly requested draft;
- `search_features`: find reusable features by text and optional category;
- `list_feature_relations`: list source-card-owned feature relations with optional
  system, feature, target-system, and relation-type filters. Results preserve
  source-card claim metadata and source-local evidence IDs;
- `list_compositions`: find reviewed composition proposals by input system or claim status;
  each result includes the cited `evidence` records resolved from the owning card;
- `get_modeling_bundle`: retrieve a fixed-commit evidence bundle for semantic
  modeling.

Tool errors are returned as JSON text so an agent can inspect missing IDs or
files without receiving an unstructured process failure. Drafts are never
included unless the caller sets `include_drafts: true`.

`list_feature_relations` is a read-only query. It does not infer a relation,
select its type, change claim status, or write to a card. The same
source-card-owned relation array is included by `get_system` when present.

## Boundary

The MCP process reads the repository filesystem when `MATHEN_API_URL` is unset.
When it is set, reviewed system, feature, and modeling-bundle reads use the
Hono/D1 API. Write and promotion operations are deliberately absent until an
authenticated review workflow exists.

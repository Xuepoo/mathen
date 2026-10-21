# Mathen MCP Server

Mathen includes a local stdio MCP server for reading the architecture knowledge
base from an agent host. It is intentionally read-only: generated drafts must
pass the Python validation and human review workflow before they become
canonical system cards.

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
the API origin before starting the server:

```bash
MATHEN_API_URL=https://api.example.com bun run mcp
```

API mode uses `GET /api/systems`, `GET /api/systems/:id`, and
`GET /api/features`. Requests have a 10-second timeout and API failures are
returned as concise JSON tool errors. Drafts are filesystem-only, so
`include_drafts: true` returns an explicit unsupported-backend error when
`MATHEN_API_URL` is set. Modeling bundles are also filesystem-only until the
API provides `GET /api/modeling/:id`; API mode reports that limitation rather
than reading local files silently.

## Tools

- `list_systems`: list reviewed cards, or include drafts explicitly;
- `get_system`: retrieve one reviewed card or explicitly requested draft;
- `search_features`: find reusable features by text and optional category;
- `get_modeling_bundle`: retrieve a fixed-commit evidence bundle for semantic
  modeling.

Tool errors are returned as JSON text so an agent can inspect missing IDs or
files without receiving an unstructured process failure. Drafts are never
included unless the caller sets `include_drafts: true`.

## Boundary

The MCP process reads the repository filesystem when `MATHEN_API_URL` is unset.
When it is set, system and feature reads use the Hono/D1 API. Write and
promotion operations are deliberately absent until an authenticated review
workflow exists.

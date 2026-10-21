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

The MCP process reads the repository filesystem directly today. The same tool
contract can later use the Hono/D1 API without changing the agent-facing
operations. Write and promotion operations are deliberately absent until an
authenticated review workflow exists.

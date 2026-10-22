# Mathen Agent Guide

## Project scope

Mathen is an evidence-backed, temporal architecture knowledge base for
software systems. It has four cooperating surfaces:

- `src/mathen/`: Python CLI and deterministic analysis pipeline.
- `apps/api/`: Hono Cloudflare Worker backed by D1.
- `apps/web/`: Vite browser client for reviewed cards.
- `apps/mcp/`: read-only stdio MCP server.

## Data boundaries

- `data/systems/` contains reviewed canonical Architecture Cards.
- `data/drafts/` contains unreviewed generated cards.
- `data/drafts/llm/` contains LLM-generated drafts awaiting review.
- `data/analyses/` contains deterministic repository reports.
- `data/modeling/` contains fixed-commit evidence bundles and prompts.
- Never promote or overwrite canonical cards as part of an automated analysis.
- Every feature and mathematical view must reference evidence in the same card.
- Preserve the distinction between `fact`, `inference`, `hypothesis`, and
  `analogy`; structural resemblance is not historical influence.

## Repository conventions

- Python uses `uv`, requires Python 3.12+, and follows Ruff configuration in
  `pyproject.toml`.
- JavaScript/TypeScript uses Bun workspaces. Do not add dependencies unless the
  change requires them.
- API changes must preserve the `{"data": ...}` success envelope and update
  D1 migrations, seed logic, MCP normalization, and documentation when the
  stored contract changes.
- Treat `data/drafts/*.json` modifications already present in the worktree as
  user work. Inspect and preserve them unless explicitly asked to regenerate or
  revert them.
- Use English for source code, comments, documentation, and identifiers.
- Keep changes focused; avoid unrelated refactors and generated build output.

## Common commands

The root `Justfile` provides the preferred grouped command interface. The
underlying `uv` and `bun` commands remain useful for focused debugging.

```bash
# Preferred grouped checks
just check
just db-reset
just dev

# Python cards and tests
uv run mathen validate
uv run python -m unittest discover -s tests -v
uv run ruff format --check .
uv run ruff check .

# TypeScript, browser build, and MCP tests
bun run check
bun run build
bun test apps/mcp/src/backend.test.ts

# Local D1 and application
bun run db:reset:local
bun run dev
```

The Python package uses a `src/` layout. If running pytest directly, use
`PYTHONPATH=src`; the CI-equivalent command is the unittest command above.

## Change workflow

1. Read the relevant schema, source, tests, and documentation before editing.
2. Add or update tests for behavior changes.
3. Run the checks relevant to the changed surface, then run the broader checks
   before declaring the work complete.
4. For card or modeling changes, run validation and inspect evidence IDs,
   provenance, claim types, and draft/canonical boundaries.
5. For API or D1 changes, run local migrations and seed verification.
6. Use Conventional Commits, following `CONTRIBUTING.md`.

## Architecture guardrails

- D1 is the canonical structured store; semantic indexes are rebuildable
  optimizations.
- The API and MCP interfaces are read-only unless an authenticated review flow
  is explicitly introduced.
- Mathematical labels are candidate views with stated questions and
  assumptions, not automatic formal proofs.
- Composition records describe hypotheses, constraints, preserved properties,
  conflicts, and evidence; they do not prove that a composed system works.

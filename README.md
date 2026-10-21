# Mathen

Mathen is an experimental knowledge base for translating software systems
into reusable architecture models. The initial application target is
Cloudflare: D1 stores canonical structured data, Vectorize provides optional
semantic retrieval, Hono exposes the API from Workers, and a small Vite client
supports browsing and search.

The project treats a software system as a collection of:

- abstractions and data structures;
- states and state transitions;
- invariants and consistency conditions;
- composition patterns;
- mathematical views;
- operational trade-offs;
- evidence-backed claims.

The first milestone is deliberately small: define a stable **Architecture
Card** format, seed it with representative systems, and provide validation
and inspection tools. LLM-assisted extraction will be added only after the
representation and evidence rules are stable.

## Project status

This repository is a research prototype. The cards are structured hypotheses
with evidence, not formal proofs of the corresponding implementations.

## Quick start: Python card tooling

```bash
uv run mathen validate
uv run mathen list
uv run mathen show git
```

## Quick start: Cloudflare application

Prerequisites: Bun and Wrangler.

```bash
bun install
bun run db:migrate:local
bun run db:seed:local
bun run dev
```

The local API runs at `http://localhost:8787` and the Vite client runs at
`http://localhost:5173`. The Vite development server proxies `/api` requests
to the Worker.

The application deliberately uses D1 as the source of truth. Vectorize is an
optional search index and is not required for local structured browsing. A
future MCP server can call the same API and submit reviewed Architecture Cards
generated from a local repository.

Run the standard checks:

```bash
ruff format --check .
ruff check .
uv run python -m unittest discover -s tests -v
```

## Repository layout

```text
docs/                       Research and modeling documentation
schemas/                    JSON Schema for architecture cards
data/systems/               Evidence-backed system cards
src/mathen/                 Validation and inspection CLI
tests/                      Unit tests
apps/api/                   Hono Worker and D1 migrations
apps/web/                   Bun/Vite browser client
packages/                   Shared TypeScript contracts
```

## Design principles

1. **Evidence before abstraction**: every non-trivial claim should link to a
   primary source or be explicitly marked as an inference.
2. **Views rather than one essence**: a system may have several valid
   mathematical views, each tied to a question and assumptions.
3. **Claims have boundaries**: benefits, costs, preconditions, and counter-
   examples are stored together.
4. **Structure is reusable**: cards describe transferable features rather than
   only product-specific descriptions.
5. **Validation precedes automation**: LLM output must pass schema and semantic
   checks before entering the knowledge base.

## Roadmap

See [`docs/roadmap.md`](docs/roadmap.md) for the staged implementation plan.

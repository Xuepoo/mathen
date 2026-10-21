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
and inspection tools. LLM-assisted extraction runs only after the
representation and evidence rules are stable, and always produces reviewable
drafts.

## Project status

This repository is a research prototype. The cards are structured hypotheses
with evidence, not formal proofs of the corresponding implementations.

## Quick start: Python card tooling

```bash
uv run mathen validate
uv run mathen list
uv run mathen show git
```

Analyze the representative repository catalog into reviewable draft cards:

```bash
uv run mathen analyze data/repositories/representative.json \
  --cache-dir /tmp/mathen/repos \
  --output-dir data/drafts
```

The command uses shallow, blob-filtered Git checkouts and reads tracked tree
metadata without materializing the full worktree. Existing cached checkouts are
reused by default; pass `--refresh` only when a network update is required.
The source cache is not committed. Reports are written to the ignored
`data/analyses/` directory, while draft cards are written to `data/drafts/` and
must be reviewed before promotion to `data/systems/`.

When GitHub's Git transport is unavailable, use the source archive transport:

```bash
uv run mathen analyze data/repositories/representative.json \
  --transport archive \
  --continue-on-error
```

Prepare evidence bundles for LLM-assisted architecture modeling:

```bash
uv run mathen prepare-modeling --write-prompts
```

This writes fixed-commit JSON bundles to `data/modeling/` and portable prompts
to `data/modeling/prompts/`. The bundle is the input to the semantic modeling
step; its output remains a draft until evidence and claims are reviewed.

Run the provider-neutral adapter against those bundles:

```bash
export OPENAI_API_KEY=...
export MATHEN_LLM_MODEL=gpt-4.1-mini
uv run mathen model --system git
```

Generated cards are written under `data/drafts/llm/`. The adapter checks card
semantics and prevents model output from introducing or changing evidence
records. Configure an OpenAI-compatible endpoint with `MATHEN_LLM_BASE_URL`,
or use the explicit `--api-key`, `--model`, and `--base-url` flags. See
[`docs/llm-modeling.md`](docs/llm-modeling.md) for the full workflow.

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

The Python development toolchain, including Ruff, is declared in
`pyproject.toml` and installed by `uv sync --locked`.

## Repository layout

```text
docs/                       Research and modeling documentation
schemas/                    JSON Schema for architecture cards
data/systems/               Evidence-backed system cards
data/repositories/          Representative repository analysis catalog
data/drafts/                Unreviewed generated Architecture Cards
data/analyses/              Ignored deterministic inspection reports
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

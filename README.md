<!-- markdownlint-disable MD013 -->

# Mathen

Mathen is an **evidence-bounded Architecture Exploration Methodology and
research instrument** for studying reusable software architecture. It turns
fixed evidence into reviewable observations, microstructures, contracts, and
bounded composition candidates.

Mathen is not an autonomous architecture generator. Similarity, graph paths,
LLM output, or a contract check never becomes proof, compatibility, causality,
originality, or architectural superiority without evidence, review, and,
where needed, an experiment.

## Current capabilities

- Versioned Architecture Cards with evidence-linked claims, scope, provenance,
  semantic validation, and the `fact`/`inference`/`hypothesis`/`analogy`
  vocabulary.
- Fixed-commit repository analysis, deterministic observations, and portable
  modeling bundles that keep source evidence separate from interpretation.
- A provider-neutral OpenAI-compatible LLM adapter that produces validated
  drafts and protocol sidecars; generated output remains non-canonical until
  human review.
- Scale-aware microstructures, finite mathematical-view checks, typed
  composition candidates, bounded analogy records, and negative-knowledge
  records.
- A D1-backed read-only API, browser atlas, and stdio MCP server, with bounded
  lexical retrieval as the current discovery baseline. Semantic/vector
  retrieval is planned, not implemented.

The detailed methodology, role boundaries, evidence model, and open evaluation
questions are documented in [`docs/research-instrument.md`](docs/research-instrument.md)
and [`docs/research-position-proposal.md`](docs/research-position-proposal.md).

## Quick start

### Python card tooling

```bash
uv sync --locked
uv run mathen validate
uv run mathen list
uv run mathen show git
```

Analyze the representative catalog into reviewable drafts:

```bash
uv run mathen analyze data/repositories/representative.json \
  --cache-dir /tmp/mathen/repos \
  --output-dir data/drafts
```

Prepare a fixed evidence bundle and run constrained modeling. Generated cards
remain under `data/drafts/llm/` until reviewed:

```bash
uv run mathen prepare-modeling --write-prompts
export OPENAI_API_KEY=...
export MATHEN_LLM_MODEL=gpt-4.1-mini
uv run mathen model --system git
```

See [`docs/configuration.md`](docs/configuration.md) and
[`docs/llm-modeling.md`](docs/llm-modeling.md) before configuring an endpoint.

### Browser and API

```bash
bun install
just db-reset
just dev
```

The local API runs at `http://localhost:8787`; the browser runs at
`http://localhost:5173`. Run the repository checks with:

```bash
just check
```

The hosted reviewed atlas is [mathen.xuepoo.xyz](https://mathen.xuepoo.xyz).

### Read-only MCP

Start the local MCP server:

```bash
bun run mcp
```

By default it reads the local filesystem. To read reviewed records through the
local API instead:

```bash
MATHEN_API_URL=http://localhost:8787/api bun run mcp
```

See [`docs/mcp.md`](docs/mcp.md) for the read-only boundary and configuration.

## Evidence and non-proof boundaries

Mathen keeps reviewed cards, drafts, fixed-commit evidence, and deterministic
analysis separate:

```text
data/systems/       reviewed canonical Architecture Cards
data/drafts/        unreviewed generated cards
data/modeling/      fixed-commit evidence bundles and prompts
data/analyses/      ignored deterministic repository reports
```

Every mathematical view states a question, assumptions, checks, and evidence.
A finite `valid` result means that supplied model data passed those checks; it
does not prove that an implementation has the modeled semantics. Composition
candidates remain hypotheses, and structural resemblance does not establish
historical influence. Source review, experiments, and human judgment remain
necessary.

## Documentation

- [`docs/research-instrument.md`](docs/research-instrument.md) — methodology,
  roles, evidence boundaries, pilots, and evaluation questions
- [`docs/research-position-proposal.md`](docs/research-position-proposal.md) —
  public research position and evidence-to-experiment loop
- [`docs/methodology.md`](docs/methodology.md) — evidence and validation rules
- [`docs/user-manual.md`](docs/user-manual.md) — schemas, data flow, and
  operating procedures
- [`docs/vision.md`](docs/vision.md) — motivation and candidate modeling views
- [`docs/roadmap.md`](docs/roadmap.md) — implementation stages and non-goals
- [`docs/microstructure-ontology.md`](docs/microstructure-ontology.md) —
  microstructure contract
- [`docs/mathematical-view-contracts.md`](docs/mathematical-view-contracts.md) —
  finite model checks and limits
- [`docs/temporal-composition-contract.md`](docs/temporal-composition-contract.md) —
  bounded composition semantics
- [`docs/semantic-retrieval.md`](docs/semantic-retrieval.md) — retrieval
  contract and planned semantic index boundary
- [`docs/scope-context-contract.md`](docs/scope-context-contract.md) — scope
  and deployment-context boundary
- [`docs/cross-domain-analogies.md`](docs/cross-domain-analogies.md) — analogy
  and non-equivalence rules
- [`docs/negative-knowledge-contract.md`](docs/negative-knowledge-contract.md) —
  rejected and misleading candidates
- [`docs/extraction-provenance.md`](docs/extraction-provenance.md) — replaceable
  model and graph provenance
- [`docs/mcp.md`](docs/mcp.md) — read-only agent access
- [`docs/auth0-mcp-setup.md`](docs/auth0-mcp-setup.md) — Auth0 OAuth/OIDC setup
  and OpenCode hosted MCP login
- [`docs/configuration.md`](docs/configuration.md) — local configuration
- [`docs/hosting.md`](docs/hosting.md) — deployment boundary
- [`docs/catalog.md`](docs/catalog.md) — catalog backlog

### Supporting research notes

These are supporting research records, not canonical cards or paper-submission
files:

- [`paper/README.md`](paper/README.md) — internal literature map
- [`docs/mth-0159-research-review-queue.md`](docs/mth-0159-research-review-queue.md) —
  research review queue audit
- [`docs/mth-0164-sqlite-savepoint-observation.md`](docs/mth-0164-sqlite-savepoint-observation.md) —
  bounded SQLite savepoint observation

## Repository

- [Source code and issues](https://github.com/Xuepoo/mathen)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`LICENSE`](LICENSE)

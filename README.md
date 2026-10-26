<!-- markdownlint-disable MD013 -->

# Mathen

Mathen is an **evidence-bounded Architecture Exploration Methodology and
research instrument** for studying reusable software architecture. It turns
fixed evidence into reviewable observations, microstructures, contracts, and
bounded composition candidates. It is not an autonomous architecture
generator: similarity, graph paths, LLM output, or a contract check never
becomes proof, compatibility, causality, originality, or architectural
superiority without evidence, review, and (where needed) an experiment.

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
- Research-only retrieval, scope/lifecycle, provenance, and SQLite observation
  artifacts that record what was measured and what remains unknown.

The detailed position, role boundaries, current evidence, and open evaluation
questions are in [`docs/research-instrument.md`](docs/research-instrument.md)
and [`docs/research-position-proposal.md`](docs/research-position-proposal.md).

## Quick start

### Python card tooling

```bash
uv tool install mathen
mathen version
mathen config init
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

Prepare a fixed evidence bundle and run the constrained modeling adapter:

```bash
uv run mathen prepare-modeling --write-prompts
export OPENAI_API_KEY=...
export MATHEN_LLM_MODEL=gpt-4.1-mini
uv run mathen model --system git
```

Generated cards remain under `data/drafts/llm/` for review. See
[`docs/configuration.md`](docs/configuration.md) and
[`docs/llm-modeling.md`](docs/llm-modeling.md) before configuring an endpoint.

### Browser, API, and MCP

```bash
bun install
just db-reset
just dev
```

The local API runs at `http://localhost:8787` and the browser at
`http://localhost:5173`. Start the read-only MCP server with:

```bash
bun run mcp
```

Use `MATHEN_API_URL=http://localhost:8787/api bun run mcp` for API mode. The
hosted reviewed atlas is [mathen.xuepoo.xyz](https://mathen.xuepoo.xyz).

Run the repository checks with:

```bash
just check
```

## Documentation

- [`docs/research-instrument.md`](docs/research-instrument.md) — methodology,
  roles, evidence boundaries, pilots, and evaluation questions
- [`docs/research-position-proposal.md`](docs/research-position-proposal.md) —
  public research position and evidence-to-experiment loop
- [`docs/methodology.md`](docs/methodology.md) — evidence and validation rules
- [`docs/user-manual.md`](docs/user-manual.md) — schemas, data flow, and
  operating procedures
- [`docs/catalog.md`](docs/catalog.md) — long-term Mathen catalog backlog
- [`docs/vision.md`](docs/vision.md) — project motivation and modeling views
- [`docs/repository-catalog.md`](docs/repository-catalog.md) — repository
  analysis policy and catalog
- [`docs/llm-modeling.md`](docs/llm-modeling.md) — constrained LLM modeling
- [`docs/extraction-provenance.md`](docs/extraction-provenance.md) — replaceable model and graph provenance
- [`docs/roadmap.md`](docs/roadmap.md) — implementation stages and non-goals
- [`docs/microstructure-ontology.md`](docs/microstructure-ontology.md) —
  microstructure contract
- [`docs/mathematical-view-contracts.md`](docs/mathematical-view-contracts.md) —
  finite model checks and limits
- [`docs/temporal-composition-contract.md`](docs/temporal-composition-contract.md) —
  bounded composition semantics
- [`docs/semantic-retrieval.md`](docs/semantic-retrieval.md) — retrieval
  contract and planned semantic index boundary
- [`docs/retrieval-extension-decision-mth-0147.md`](docs/retrieval-extension-decision-mth-0147.md) —
  lexical baseline decision and embedding gate
- [`docs/scope-context-contract.md`](docs/scope-context-contract.md) — scope
  and deployment-context boundary
- [`docs/cross-domain-analogies.md`](docs/cross-domain-analogies.md) — analogy
  and non-equivalence rules
- [`docs/negative-knowledge-contract.md`](docs/negative-knowledge-contract.md) —
  rejected and misleading candidates
- [`docs/mcp.md`](docs/mcp.md) — read-only agent access
- [`docs/configuration.md`](docs/configuration.md) — local configuration
- [`docs/hosting.md`](docs/hosting.md) — deployment boundary
- [`docs/catalog.md`](docs/catalog.md) — catalog backlog

### Supporting research notes

These linked notes are supporting research records, not canonical cards or
paper submission files. The internal literature map, replaceable extraction
provenance profile, review-queue audit, and newer SQLite observation note are
maintained alongside the documentation and are referenced from the detailed
research narrative:

- [`docs/mth-0150-retrieval-embedding-pilot.md`](docs/mth-0150-retrieval-embedding-pilot.md) —
  lexical versus local embedding pilot
- [`docs/mth-0154-retrieval-evaluation.md`](docs/mth-0154-retrieval-evaluation.md) —
  deterministic retrieval evaluation
- [`docs/g5-sqlite-transaction-experiment.md`](docs/g5-sqlite-transaction-experiment.md) —
  bounded SQLite transaction observation
- [`docs/review-extraction-pipeline.md`](docs/review-extraction-pipeline.md) —
  extraction and review boundary
- [Internal literature map](paper/README.md)
- [Extraction provenance profile](docs/extraction-provenance.md)
- [Research review queue audit](docs/mth-0159-research-review-queue.md)
- [SQLite savepoint observation](docs/mth-0164-sqlite-savepoint-observation.md)

## Repository

- [Source code and issues](https://github.com/Xuepoo/mathen)
- [`CONTRIBUTING.md`](CONTRIBUTING.md)
- [`LICENSE`](LICENSE)

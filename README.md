<!-- markdownlint-disable MD013 -->

# Mathen

Mathen is an evidence-backed, temporal knowledge graph for software
architecture.

It studies software systems from two complementary directions:

1. **Analysis:** translate systems into reusable architectural features,
   state models, invariants, trade-offs, and mathematical views.
2. **Synthesis:** compose those features under explicit requirements and
   constraints to explore candidate architectures for new systems.

Mathen treats architecture as an evolving network rather than a static list of
products. Systems acquire new features, dependencies, relationships, and
community memberships over time. New systems are often formed by recombining
existing ideas under a new workload, deployment boundary, hardware context, or
set of operational constraints.

> **Mathen turns software architecture into a time-aware, evidence-backed,
> mathematically informed intermediate representation that can be compared,
> composed, and validated.**

## Why Mathen exists

Architecture knowledge is scattered across source code, design documents,
papers, benchmarks, protocol specifications, and operational experience. This
makes it difficult to answer questions such as:

- Which design properties do SQLite and DuckDB share, and where do they
  diverge?
- How does PostgreSQL connect relational databases, extensibility, indexing,
  replication, and domain-specific extensions?
- Which existing structures are composed by Supabase or Firecracker?
- Which properties are preserved when two architectural patterns are combined?
- What new conflicts, assumptions, and costs appear in the combination?
- How did a system's architecture and relationships change between versions?

Mathen makes these questions machine-readable without reducing architecture to
ungrounded labels or a single oversimplified definition.

## The research position

Mathen investigates whether a reviewed bridge between evidence, architectural
microstructure, and checkable contracts can make cross-domain comparison and
architecture synthesis more useful and more falsifiable. It is an
evidence-backed intermediate representation for studying reusable software
architecture—not a system that reduces a product to one essence, asks an LLM to
invent a final architecture, or treats similarity as proof.

The intended workflow is a loop, not an `LLM in → architecture out` pipeline:

```text
evidence
  → deterministic observation
  → reviewed architectural microstructure
  → mathematical or interface contract
  → bounded composition candidate
  → candidate macro-architecture
  → prototype, benchmark, or failure experiment
  → new evidence, counterexample, or negative knowledge
  ↺ human review and question reformulation
```

Each step has a bounded meaning:

1. **Evidence** starts with source code, fixed revisions, design documents,
   papers, benchmarks, protocol specifications, or reproducible operational
   observations. Provenance, version, and deployment origin remain visible.
2. **Deterministic observation** records reproducible signals such as tracked
   paths, language counts, build markers, and navigation hints. These guide
   review; they do not establish semantic architecture facts by themselves.
3. **Microstructure** is a reusable unit at an explicit scale—primitive,
   mechanism, subsystem, system, or ecosystem—with possible states, events,
   boundaries, resources, and failures. It is an evidence-linked candidate,
   not an automatic promotion to a reviewed card.
4. **Contract** makes carriers, operations, interfaces, assumptions, checks,
   and failure modes explicit where the data permits. A finite `valid` result
   means that the supplied model data passed the check; it does not prove that
   the implementation has the modeled semantics. Missing data remains
   `undetermined`.
5. **Composition** records inputs, roles, constraints, preserved or weakened
   properties, conflicts, assumptions, and validation gaps. Composition
   candidates remain `proven: false`; names, vector similarity, graph
   position, or LLM prose cannot silently create compatibility claims.
6. **Macro-architecture** is a design hypothesis assembled under a workload,
   deployment boundary, and constraints. It is not canonical merely because
   its parts are documented.
7. **Experiment** means a bounded prototype, benchmark, property test, fault
   injection, or failure test with its protocol and scope retained. Results
   can strengthen, narrow, reject, or leave a candidate undetermined.

### Who does what

These participants and mechanisms are complementary, not interchangeable:

| Role | Contribution | Boundary |
| --- | --- | --- |
| Human researcher | Reframes questions and reviews claims | Judgment is not automatically reproducible |
| Deterministic tooling | Records fixed-revision observations | Signals guide review; they are not semantic claims |
| LLM | Explains evidence and drafts abstractions | It is not proof or an architecture authority |
| Graph analysis | Exposes typed paths and neighborhoods | Position is not truth, causality, or compatibility |
| Vector retrieval | Recovers terminology variants | Similarity is not a typed relation |
| Contracts and microstructures | Make scope and checks explicit | Contracts cannot validate omitted behavior |
| Experiments and failure tests | Measure behavior and counterexamples | Results are deployment-scoped |

```text
vector similarity ≠ graph position ≠ LLM interpretation
                ≠ contract classification ≠ runtime compatibility
                ≠ historical influence
```

### Reading cross-domain comparisons

Mathen uses `fact`, `inference`, `hypothesis`, and `analogy` to keep evidence
and interpretation separate. Chemistry and biology can provide a bounded
analogy: a reaction network and a gene-regulation network may share a
qualitative directed-motif question, but they do not thereby share parameters,
substrates, governing laws, units, causal semantics, or historical influence.
**A representation can transfer a question about connectivity without
transferring the mechanism that produces the behavior.**

Materials science is an analogy for the explanatory term *microstructure*:
phases, defects, interfaces, and conditions can illustrate why bounded
structures and properties matter. Software does not thereby acquire crystal
structure, thermodynamic laws, constitutive equations, scale invariance, or
material-property predictions. Taxonomy is likewise a controlled vocabulary
for retrieval and review, not a discovery of natural kinds or complete,
mutually exclusive classes. A taxonomic resemblance does not establish
dependency, lineage, compatibility, or historical influence. Every published
analogy should state its scale, shared and non-preserved properties, exclusions,
evidence, and at least one counterexample.

### Discovery, novelty, and current limits

Here, **discovery** initially means that a search or researcher surfaced a
candidate path, mapping, counterexample, or question not previously recorded
in the current dataset. It does not mean that Mathen created a new fact,
established historical influence, or generated a useful architecture. Novelty
must be scoped to topology, a composition boundary, constraints, behavior,
trade-offs, deployment context, or merely wording. A cross-community path,
larger graph, vector neighbor, or fluent LLM proposal is not evidence of
architectural originality. A stronger claim needs a defined reference set,
source review, explicit scope, and—when usefulness or behavior is claimed—a
prototype or experiment. See the open evaluation questions in
[`docs/research-instrument.md`](docs/research-instrument.md).

The current implementation provides reviewed, evidence-linked cards; fixed-
commit analysis and modeling bundles; deterministic repository observations;
an evidence-bounded OpenAI-compatible LLM adapter that writes drafts and
protocol sidecars; scale-aware microstructure documents; finite mathematical
view classifications; bounded composition candidates; analogy and negative-
knowledge records; D1-backed API/browser/MCP boundaries; and optional,
rebuildable semantic retrieval. It does **not** automatically prove
implementation semantics, produce theorems, promote LLM output or analogies,
guarantee graph/vector recall or compatibility, assign calibrated originality
or quality scores, infer historical influence, replace source review and
experiments, or demonstrate that the full loop improves architecture quality.
The graph projection and novelty benchmark work remain future research; see
the planning references for [MTH-0117](https://github.com/Xuepoo/mathen/issues/47)
and [MTH-0118](https://github.com/Xuepoo/mathen/issues/48).

### Deployment and provenance boundary

A deployment hostname is not part of Mathen's research identity. Validity
scope should record versions, conditions, exclusions, and applicable
`deployment_origins`; an origin says where a claim was evaluated or accessed,
not that it is true. D1 remains the structured source of truth while semantic
indexes are rebuildable. Browser requests use the deployment's same-origin
`/api` boundary, while MCP and synchronization origins are configured through
`MATHEN_API_URL`, `MATHEN_MCP_URL`, `MATHEN_SYNC_SOURCE`, and related settings
described in [`docs/configuration.md`](docs/configuration.md). OpenAI-compatible
LLM endpoints are also explicit configuration, and secrets stay outside URLs
and checked-in research records.

The detailed contracts and boundaries are documented in the
[`research position proposal`](docs/research-position-proposal.md),
[`microstructure ontology`](docs/microstructure-ontology.md),
[`mathematical-view contracts`](docs/mathematical-view-contracts.md),
[`temporal composition contract`](docs/temporal-composition-contract.md),
[`cross-domain analogies`](docs/cross-domain-analogies.md), and
[`negative-knowledge contract`](docs/negative-knowledge-contract.md).

## Project status

This repository is a research prototype. Architecture Cards are structured,
evidence-backed models, not automatic formal proofs of the corresponding
implementations.

Source code and the browser client are available in the
[Mathen GitHub repository](https://github.com/Xuepoo/mathen).

## The core model

Mathen represents a system through several complementary views:

```text
System and version
├── data model and types
├── state space and transitions
├── operations and composition laws
├── dependency and causality graph
├── consistency and convergence model
├── storage and execution model
├── isolation and security boundary
├── failure and recovery model
├── resource, performance, and cost model
└── evolution, migration, and composition history
```

No single mathematical structure is expected to explain an entire system. A
mathematical view is useful only when it answers a concrete question and states
its assumptions. Depending on the question, a view may use:

| Architecture question           | Candidate mathematical view                |
| ------------------------------- | ------------------------------------------ |
| What are the data and objects?  | Sets, types, algebraic data types          |
| How are objects related?        | Graphs, DAGs, partial orders               |
| How does the system evolve?     | State machines, transition systems         |
| Which operations compose?       | Monoids, algebras, compositional semantics |
| Does state converge?            | Semilattices, monotone systems             |
| Is an optimization transparent? | Refinement, simulation, bisimulation       |
| How do failures affect service? | Probability, queueing, reliability models  |
| How are resources bounded?      | Complexity and cost models                 |

These are candidate abstractions, not automatic proofs. Each claim is labeled
as a `fact`, `inference`, `hypothesis`, or `analogy`, and remains connected to
its evidence and scope.

## A temporal, multi-layer architecture graph

The long-term knowledge graph contains more than software names. It can include
systems, versions, features, primitives, mathematical models, programming
languages, operating systems, protocols, organizations, evidence, and candidate
architectures.

Relationships are typed rather than collapsed into a generic similarity edge:

```text
implements       uses              extends
composes         resembles         influenced-by
depends-on       conflicts-with    optimizes-for
evolves-to       verified-by       constrained-by
```

This distinction matters. Historical influence needs historical evidence;
structural similarity can be inferred from architecture analysis; a dependency
should be supported by implementation or documentation evidence.

The graph is temporal:

```text
version A ──evolves-to──> version B ──adds──> feature C
       │                         └──uses──> primitive D
       └──belongs-to──> community E
```

It can represent the first appearance of a feature, version-specific changes,
new dependencies, community membership, composition lineage, and candidate
architectures that have not yet been implemented. Systems can belong to many
overlapping communities: PostgreSQL can connect relational databases, MVCC,
database extensibility, geospatial data, vector search, replication, and
backend platforms at the same time.

## From analysis to synthesis

Mathen uses a staged workflow:

```text
source code / documents / papers / experiments
                         ↓
                 fixed evidence and provenance
                         ↓
             deterministic repository observations
                         ↓
       semantic features, mathematical views, trade-offs
                         ↓
             reviewed temporal architecture graph
                         ↓
        constraint-based comparison and composition
                         ↓
             prototype, benchmark, and failure tests
```

When exploring a new architecture, Mathen records more than its input
features:

```text
inputs
new constraints
target workload
preserved properties
introduced conflicts
new trade-offs
unverified assumptions
validation plan
```

Architecture synthesis is not feature shopping. For example, combining
embedded execution, columnar vectorization, append-only recovery, and
content-addressed snapshots requires checking the write model, transaction
boundary, recovery protocol, update pattern, and storage costs.

## Representative examples

The current cards and repository analyses use systems that expose different
architectural patterns:

| System      | Reusable structure being studied                                        |
| ----------- | ----------------------------------------------------------------------- |
| Git         | Immutable content-addressed objects, mutable references, causal history |
| SQLite      | Embedded execution, layered storage, atomic commit, WAL snapshots       |
| DuckDB      | Embedded analytical execution, columnar data, vectorized operators      |
| PostgreSQL  | Extensible relational engine, MVCC, process isolation, extensions       |
| Kafka       | Durable append-only logs, ordered offsets, replay-oriented consumption  |
| Kubernetes  | Declarative state, reconciliation loops, control-plane convergence      |
| Firecracker | Minimal virtual machine model, KVM isolation, event-driven VMM          |
| Supabase    | Database-centered platform composition, API, auth, and data policy      |

These are starting points for extracting structures that can be compared across
databases, distributed systems, operating systems, runtimes, network protocols,
compilers, media systems, and programming languages. They are not claimed to
be complete formal models or evidence of historical influence.

## Evidence and review boundary

Mathen separates observations, interpretations, and reviewed knowledge:

```text
data/systems/       reviewed canonical Architecture Cards
data/drafts/        unreviewed generated cards
data/modeling/      fixed-commit evidence bundles and prompts
data/analyses/      ignored deterministic repository reports
```

The project follows these rules:

1. Extract observable facts before assigning mathematical terminology.
2. Cite primary evidence wherever possible.
3. Give every mathematical view a question and assumptions.
4. Record benefits, costs, preconditions, failure modes, and counterexamples.
5. Keep structural similarity separate from historical influence.
6. Never let LLM output overwrite reviewed cards.
7. Treat candidate compositions as hypotheses until implemented or validated.

An LLM proposes abstractions and comparisons; deterministic tools provide
provenance and observations; schema and semantic validation constrain output;
human review decides what becomes canonical.

Mathen also studies this as a human–LLM research instrument: LLMs provide broad
cross-domain retrieval and candidate explanations, while humans provide
problem reformulation, curiosity-driven exploration, and final review. Graphs,
vectors, mathematical contracts, and experiments have separate roles in the
loop. This is an open research direction, not a claim that direct LLM output
is architectural novelty or proof. See
[`docs/research-instrument.md`](docs/research-instrument.md).

## Current implementation

The repository currently provides:

- a versioned Architecture Card schema and semantic validator;
- a representative repository catalog across databases, logs,
  orchestration, isolation, virtualization, networking, compilers, media, and
  backend platforms;
- fixed-commit repository analysis with Git and GitHub archive transports;
- deterministic repository observations for source structure, build surfaces,
  and navigation signals without assigning semantic facts;
- portable modeling bundles and a provider-neutral OpenAI-compatible LLM
  adapter;
- a bounded composition candidate explorer whose results remain
  `proven: false`;
- a Cloudflare-first Hono Worker API backed by D1;
- a Vite browser client for browsing reviewed architecture cards;
- read-only API queries for source-card-owned feature relations and composition
  proposals;
- a read-only stdio MCP server with filesystem and API backends;
- optional Cloudflare Turnstile protection, signed browser access sessions,
  service-token API access, and per-IP limits;
- explicit separation between reviewed cards, drafts, and modeling evidence.

The canonical tree currently contains 219 reviewed cards. The representative
repository manifest contains 62 entries, all with matching canonical cards.

The current knowledge graph is intentionally relational and small. D1 is the
canonical structured store. Vectorize is an optional rebuildable semantic
index, and a dedicated graph database remains a future adapter rather than a
first-milestone dependency.

## Quick start: Python card tooling

```bash
uv tool install mathen
mathen version
mathen config init
uv run mathen validate
uv run mathen list
uv run mathen show git
```

The CLI supports a cross-platform TOML configuration under the user's standard
configuration directory. Configure paths and an OpenAI-compatible LLM endpoint
with `mathen config set`; see [`docs/configuration.md`](docs/configuration.md).
The current package release is `v0.0.2`. Pushing a matching version tag builds
and publishes the Python distributions to PyPI through the
`PYPI_API_TOKEN` GitHub Actions secret.

For an installed CLI, download the reviewed cards before browsing them:

```bash
mathen data sync
mathen data status
mathen doctor
mathen mcp path
mathen mcp check
mathen list
mathen show git
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

The repository also provides a `just` command layer for the common local
workflows below. The existing `bun` and `uv` commands remain the underlying
implementation commands.

```bash
bun install
just db-reset
just dev
```

The local API runs at `http://localhost:8787` and the Vite client runs at
`http://localhost:5173`. The Vite development server proxies `/api` requests
to the Worker.

The application deliberately uses D1 as the source of truth. Vectorize is an
optional search index and is not required for local structured browsing. A
local MCP server exposes read-only system, feature, and modeling-bundle tools;
see [`docs/mcp.md`](docs/mcp.md). Set `MATHEN_API_URL=http://localhost:8787/api`
to make it read reviewed data and modeling bundles through the Hono/D1 API;
without that variable it uses the local filesystem. A future hosted MCP server
can call the same API and submit reviewed Architecture Cards generated from a
local repository.

Run the standard checks:

```bash
just check
```

Run `just` or `just --list` from the repository root to see all available
recipes. Useful focused commands include `just python-check`, `just api-test`,
`just typescript-check`, `just build`, and `just mcp`.

The Python development toolchain, including Ruff, is declared in
`pyproject.toml` and installed by `uv sync --locked`.

## Quick start: MCP

Start the local read-only MCP server from the repository root:

```bash
bun run mcp
```

By default it reads the local filesystem. To read reviewed systems and fixed
modeling bundles through the Hono/D1 API instead:

```bash
MATHEN_API_URL=http://localhost:8787/api bun run mcp
```

The server exposes `list_systems`, `get_system`, `search_features`,
`list_feature_relations`, and `get_modeling_bundle`. API mode does not expose
drafts; filesystem mode exposes them only when explicitly requested. See
[`docs/mcp.md`](docs/mcp.md).

## Repository layout

```text
docs/                       Research and modeling documentation
schemas/                    JSON Schema for architecture cards
data/systems/               Evidence-backed system cards
data/repositories/          Representative repository analysis catalog
data/drafts/                Unreviewed generated Architecture Cards
data/modeling/              Fixed-commit modeling bundles
data/analyses/              Ignored deterministic inspection reports
src/mathen/                 Validation, analysis, and LLM tooling
tests/                      Unit tests
apps/api/                   Hono Worker and D1 migrations
apps/web/                   Bun/Vite browser client
apps/mcp/                   Read-only stdio MCP server
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

The project is developed in stages:

1. **Representation and evidence:** stabilize Architecture Cards and review
   rules.
2. **Assisted extraction:** turn fixed-commit evidence into constrained drafts.
3. **Application and retrieval:** provide D1, API, browser, semantic search,
   and MCP access.
4. **Temporal and relational graph:** model versions, evolution, communities,
   composition, constraints, and evidence lineage.
5. **Architecture synthesis:** query requirements, generate candidate
   compositions, expose conflicts, and validate candidates with prototypes,
   benchmarks, and failure tests.

The long-term goal is a disciplined intermediate layer between implementation
and design reasoning:

```text
existing systems → reusable architectural structures → candidate designs
```

## Non-goals

Mathen does not currently aim to:

- automatically prove that an implementation satisfies a mathematical model;
- claim originality from structural similarity alone;
- replace source review, experiments, benchmarks, or human architecture
  judgment;
- treat every mathematical analogy as a formal equivalence;
- operate a general-purpose graph database before relational query patterns
  demonstrate that it is necessary.

## Documentation

- [`docs/user-manual.md`](docs/user-manual.md) — schemas, data flow, and
  operating procedures
- [`docs/catalog.md`](docs/catalog.md) — long-term Mathen catalog backlog
- [`docs/vision.md`](docs/vision.md) — project motivation and modeling views
- [`docs/methodology.md`](docs/methodology.md) — evidence and validation rules
- [`docs/repository-catalog.md`](docs/repository-catalog.md) — repository
  analysis policy and catalog
- [`docs/llm-modeling.md`](docs/llm-modeling.md) — constrained LLM modeling
- [`docs/mcp.md`](docs/mcp.md) — read-only agent access
- [`docs/hosting.md`](docs/hosting.md) — Cloudflare deployment boundary
- [`docs/roadmap.md`](docs/roadmap.md) — staged implementation plan

## License

See [`LICENSE`](LICENSE).

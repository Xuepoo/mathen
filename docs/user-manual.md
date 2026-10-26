<!-- markdownlint-disable MD013 -->

# Mathen User Manual

This manual explains the data contracts, storage layers, commands, and
end-to-end workflow currently implemented by Mathen.

Mathen has two related goals:

1. Translate software systems into evidence-backed architecture models.
2. Compare and eventually compose those models under explicit constraints.

The first goal is implemented today. Temporal evolution, communities, and
architecture synthesis remain planned extensions. Current contracts also provide
typed feature relations, composition proposals, and bounded candidate
exploration while preserving evidence, version context, and draft boundaries.

## 1. Concepts and status boundaries

| Concept           | Meaning                                             |
| ----------------- | --------------------------------------------------- |
| System            | A product or project such as Git, SQLite, or DuckDB |
| Architecture Card | A structured model of one system and its evidence   |
| Draft             | An automatically generated or not-yet-reviewed card |
| Reviewed card     | A card accepted into the canonical knowledge base   |

The repository currently uses these directories:

```text
data/systems/       reviewed canonical cards
data/drafts/        unreviewed structural or semantic cards
data/drafts/llm/    cards produced by the LLM adapter
data/repositories/  repository analysis manifest
data/analyses/      ignored deterministic reports
data/modeling/      fixed-commit LLM evidence bundles
.cache/mathen/      ignored repository checkout cache
```

Only `data/systems/` is canonical. LLM output must remain under a draft
directory and cannot overwrite reviewed cards.

### 1.1 Public MVP orientation

The public starting point is [mathen.xuepoo.xyz](https://mathen.xuepoo.xyz).
The browser opens a reviewed systems graph and lets you search the card
catalog, inspect a system, switch to mathematical model neighborhoods, and
follow explicit relations. The current UI uses `/api/graph` and
`/api/graph/models` for the graph and loads card details from
`/api/systems/:id`; it does not expose drafts.

Use these terms while exploring:

- **System:** a product or project represented by one reviewed card at a stated
  version or context.
- **Layer:** a typed projection of records, for example `system`, `property`,
  `mathematical-contract`, `composition`, `microstructure`, or `analogy`.
  Layers separate record kinds; they do not assert that every visible node is
  equivalent or connected by an inferred relation.
- **Property:** a reusable feature attached to a system, with a category,
  claim type, description, and evidence IDs. A property is not a promise that
  another system can provide it under the same conditions.
- **Mathematical contract/view:** a candidate model tied to a question and
  assumptions. It preserves claim type and evidence so a reader can inspect
  the boundary. It is not an automatic formal proof of implementation
  behavior.

For a quick first visit: open the site, use **Browse systems** to find a
familiar card, inspect one feature and its source evidence, switch to **Math
models** and read a model's question and assumptions, then follow one typed
relation to another card. Graph position, navigation groups, and edge layout
are for exploration; they do not add evidence.

### 1.2 Evidence, claims, and discovery signals

Read the cited evidence first, then the claim label. `fact` means directly
supported by the cited source; `inference` means an abstraction derived from
facts; `hypothesis` means a proposal requiring validation; and `analogy` means
a bounded comparison rather than formal equivalence. A composition record or
mathematical view can be useful while still remaining a hypothesis.

Search and graph navigation are discovery aids. The first retrieval
implementation is a bounded lexical baseline over reviewed records; it is not
embedding or semantic/vector search. Its score is an uncalibrated
review-priority signal only. It does not establish truth, evidence,
compatibility, causality, originality, substitutability, or historical
influence. `GET /api/retrieval` and the `search_semantic` MCP tool preserve
claim labels, evidence, scope, and provenance, but only become available on a
hosted site after that deployment has been made and read back. If the public
deployment has not announced them, use the lexical system routes and
graph/card UI instead; do not infer hosted availability from source code.

There are no formal mobile performance metrics in this manual. Small-screen
and touch use should be judged from real user feedback and improved as that
feedback arrives.

The checked-in canonical tree contains 219 reviewed cards. The representative
repository manifest contains 62 entries, all of which currently have matching
canonical cards; it is a subset of the canonical tree. MTH-0092 added the
canonical `bun`, `haskell`, `quickjs`, and `tokio` cards, but did not add those
IDs to the representative manifest. These are repository counts, not a
guarantee that a deployed D1 database has been seeded with the same rows.

## 2. Schema inventory

| Contract            | File or source                          | Role                                       |
| ------------------- | --------------------------------------- | ------------------------------------------ |
| Architecture Card   | `schemas/architecture-card.schema.json` | Canonical system model                     |
| Repository Manifest | `data/repositories/representative.json` | Analysis input catalog                     |
| Analysis Report     | `data/analyses/<id>.json`               | Deterministic repository observations      |
| Structural Draft    | `data/drafts/<id>.json`                 | Conservative card from observations        |
| Modeling Bundle     | `data/modeling/<id>.json`               | Fixed evidence input for semantic modeling |
| LLM Draft Card      | `data/drafts/llm/<id>.json`             | Validated model output awaiting review     |
| D1 projection       | `apps/api/migrations/`                  | Relational storage for cards and bundles   |
| API envelope        | `apps/api/src/index.ts`                 | Read-only HTTP projection                  |
| MCP contract        | `apps/mcp/src/index.ts`                 | Read-only agent-facing tools               |

The JSON Schema defines the card shape. The Python validator in
`src/mathen/cards.py` adds cross-reference and semantic checks that a JSON
Schema alone cannot express.

## 3. Architecture Card schema

An Architecture Card describes one system at one stated version or revision.
The top-level object has these fields:

| Field                | Required | Type                   | Meaning                                         |
| -------------------- | -------- | ---------------------- | ----------------------------------------------- |
| `id`                 | yes      | lowercase string       | Stable machine identifier, for example `duckdb` |
| `name`               | yes      | string                 | Human-readable system name                      |
| `version_context`    | no       | string                 | Version, release, commit, or analysis context   |
| `summary`            | yes      | string                 | One-paragraph architectural summary             |
| `scope`              | yes      | non-empty string array | Topics and boundaries covered                   |
| `features`           | yes      | non-empty object array | Reusable architecture features                  |
| `mathematical_views` | yes      | object array           | Mathematical or formal views                    |
| `trade_offs`         | yes      | object array           | Benefits and costs of features                  |
| `evidence`           | yes      | non-empty object array | Sources supporting the card                     |
| `related_systems`    | no       | string array           | IDs of related cards                            |
| `temporal_context`   | no       | object                 | Version lifecycle and temporal claims           |
| `relations`          | no       | object array           | Typed, directed architecture relations          |
| `feature_relations`  | no       | object array           | Evidence-backed directed feature relations      |
| `composition`        | no       | object                 | Proposed or reviewed system composition         |

### 3.1 Feature fields

Every feature contains:

| Field          | Meaning                                                      |
| -------------- | ------------------------------------------------------------ |
| `id`           | Stable lowercase feature identifier                          |
| `name`         | Human-readable reusable feature name                         |
| `category`     | Feature family, such as `storage-model` or `execution-model` |
| `claim_type`   | `fact`, `inference`, `hypothesis`, or `analogy`              |
| `description`  | Precise claim about the system or transferable structure     |
| `benefits`     | Optional list of positive consequences                       |
| `costs`        | Optional list of limitations                                 |
| `evidence_ids` | Non-empty references to evidence in the same card            |

Describe transferable structure rather than only product details. For example,
`embedded-process-execution` is more reusable than `has a Python package`.

### 3.2 Mathematical view fields

Every mathematical view contains:

| Field          | Meaning                                 |
| -------------- | --------------------------------------- |
| `model`        | Candidate mathematical or formal model  |
| `question`     | Concrete question answered by the model |
| `assumptions`  | Conditions and simplifications required |
| `claim_type`   | Status of the correspondence            |
| `evidence_ids` | Supporting evidence references          |

Candidate views include graphs and partial orders for dependency or causality,
state machines for lifecycle behavior, semilattices for convergence, and
refinement relations for transparent optimizations. A label such as “lattice”
is not a theorem by itself; operations and laws must be stated first.

### 3.3 Trade-off fields

Each trade-off contains `feature_id`, a non-empty `benefits` array, and a
non-empty `costs` array. The feature ID must exist in the same card.

### 3.4 Evidence fields

Each evidence item contains:

| Field      | Required | Meaning                                                              |
| ---------- | -------- | -------------------------------------------------------------------- |
| `id`       | yes      | Stable lowercase evidence identifier                                 |
| `kind`     | yes      | `official-doc`, `paper`, `source-code`, `experiment`, or `secondary` |
| `title`    | yes      | Source title                                                         |
| `uri`      | yes      | Source URL                                                           |
| `accessed` | no       | Retrieval date or timestamp                                          |
| `notes`    | no       | Scope, excerpt, or provenance notes                                  |

Every feature and mathematical view must reference existing evidence IDs.

Standalone mathematical-view contracts can be checked without loading cards:

```bash
uv run mathen validate-mathviews data/mathviews
```

This command validates one JSON file or each top-level JSON file in a
directory using the same mathematical-view loader and validator. An absent or
empty directory succeeds as a no-op. Card-local evidence references remain
bounded by the containing card when a contract is embedded there.

The optional `feature_relations` array is owned by the source card. Each item
references a source feature in that card, a target system and feature, a
feature-relation type, claim metadata, and evidence IDs from the source card.
Target feature existence is checked when validating the reviewed card
collection. Structural comparisons should use `resembles` with a bounded
`analogy` claim; relation records do not add nodes to the system graph.

For `kind: "experiment"`, the evidence item additionally requires `protocol`,
`system_commit`, `environment`, `command`, `dataset`, `repetitions`, `metrics`,
and `artifacts`. `repetitions` is a positive integer, `metrics` is an object
whose values are finite numbers, and `artifacts` is an array of strings or
metadata objects. Environment and dataset can be strings or metadata objects.
These fields describe reproducibility context; they do not by themselves claim
that an experiment produced a particular result.

Experiment evidence is a reproducibility contract, not a general benchmark
contract. The protocol must state what was run, against which system commit,
environment, command, and dataset; the recorded metrics and artifacts may be
empty when the protocol records an observation without a checked-in measurement
or artifact. The contract does not establish causality, production behavior,
durability, performance, or a general theorem. Those claims require the
appropriate source review, repeated measurements, benchmarks, or failure tests.

### 3.5 Claim types

| Claim type   | Use it for                                                     |
| ------------ | -------------------------------------------------------------- |
| `fact`       | Directly supported implementation or documentation observation |
| `inference`  | Reasonable abstraction derived from supported facts            |
| `hypothesis` | Proposed model requiring validation                            |
| `analogy`    | Explanatory comparison that is not formal equivalence          |

Do not use `fact` for an elegant mathematical interpretation unless the source
actually establishes it.

### 3.6 Temporal and composition fields

The optional temporal contract is backward-compatible with existing cards. A
`temporal_context` object can contain `version`, `valid_from`, `valid_to`,
`status`, `supersedes`, `superseded_by`, `claim_status`, and `evidence_ids`.
Lifecycle `status` can be `planned`, `current`, `superseded`, `deprecated`, or
`historical`. Review `claim_status` is separate and can be `proposed`,
`under-review`, `accepted`, `rejected`, or `deprecated`.

The optional `relations` array stores typed directed assertions. Each relation
contains `type`, `target`, `claim_type`, `claim_status`, and `evidence_ids`.
The current relation vocabulary is `uses`, `extends`, `composes`, `resembles`,
and `influenced-by`. Historical influence must have historical evidence;
structural resemblance should normally be an inference or analogy.

The optional `composition` object records `inputs`, `constraints`,
`preserved_properties`, `conflicts`, `claim_status`, and `evidence_ids`.
Each input has a `system_id`, a role, optional version context, review status,
and evidence. Each constraint, preserved property, and conflict is itself an
evidence-backed claim. This contract records a composition proposal; it does
not execute or prove the proposed architecture.

## 3.7 Bounded composition exploration

`mathen.composition_solver` provides a deterministic, library-only bounded
candidate explorer for composition hypotheses. `solve_reviewed_compositions(cards,
capability_specs, required_capabilities, ...)` accepts validated reviewed-card
objects and an explicit capability declaration for each feature being made
available to the solver:

```python
{
    "system_id": "app-system",
    "feature_id": "application-feature",
    "provides": ["application"],
    "requires": ["storage"],
    "conflicts": ["incompatible-capability"],
}
```

Capability declarations are intentionally separate from card feature names,
descriptions, categories, and feature relations. The adapter qualifies feature
IDs as `system_id:feature_id` and evidence IDs as `system_id:evidence_id`, then
passes only those explicit records to the solver. A declaration may select a
subset of the features in the cards; declarations that reference no reviewed
feature are rejected. Callers should load and validate canonical cards with
`mathen.cards.load_card` before adapting them.

`conflicts` is a capability-only namespace: each token is matched against the
capabilities provided by the composed records and is reported as
`feature_id:capability`. Feature IDs are not implicitly conflict tokens.

The solver enumerates non-empty feature subsets up to `max_components`, adds a
deterministic provider closure up to `max_depth`, and returns at most
`max_results` candidates. These positive integer bounds are required. Each
candidate contains selected feature IDs, dependency IDs, provided and required
capabilities, unresolved requirements, conflicts, evidence IDs, explanations,
coverage/evidence/deterministic scores, and `proven: false`. Candidates are
ranked deterministically; unresolved requirements and conflicts remain visible
and are not treated as proof of compatibility or runtime behavior.

The numeric `score` is an uncalibrated deterministic review-priority heuristic,
not a probability, compatibility score, or proof. `coverage_score` measures
coverage of the top-level required capabilities. `evidence_score` is the mean
number of evidence IDs per record in the selected dependency closure. The
formula uses fixed heuristic units: `coverage_score * 100` plus
`evidence_score`, minus 10 per unresolved requirement and 20 per conflict.

The solver is an exploration aid, not an architecture verifier. It does not
execute components, test compatibility, validate runtime behavior, or prove
that a candidate can be implemented. Every returned candidate has
`proven: false`, including candidates with complete capability coverage and no
reported conflicts.

## 4. Repository Manifest schema

The manifest is a JSON array. Each entry describes one repository to inspect:

```json
{
  "id": "sqlite",
  "name": "SQLite",
  "category": "database",
  "repository": "https://github.com/sqlite/sqlite.git",
  "documentation": "https://www.sqlite.org/docs.html",
  "ref": "master",
  "priority": "core"
}
```

Fields are `id`, `name`, `category`, `repository`, `documentation`, `ref`, and
`priority`. IDs must be unique and lowercase. Priority is currently `seed`,
`core`, or `extended`. A catalog entry selects evidence; it does not prove a
feature.

## 5. Deterministic Analysis Report

`mathen analyze` resolves a requested reference to a commit and writes
`data/analyses/<id>.json`. The report records observations without assigning
runtime semantics.

Important fields are `analysis_version`, `system_id`, `system_name`, `category`,
`priority`, `repository`, `documentation`, `requested_ref`, `commit`,
`commit_url`, `provenance`, `analyzed_at`, `file_count`, `top_level_entries`,
`language_counts`, `extension_counts`, `build_markers`, `readme_paths`, and
`path_signals`. Analysis version 3 also includes an `observations` array. Each
observation records a conservative deterministic signal with `kind`, a tracked
source `location` (`path` and, for content signals, `line`), `basis`, `detail`,
the inspector `tool`, and checkout `provenance`. Recognized dependency manifests,
bounded source locations, and test, benchmark, recovery, and configuration
path/content signals are included when present.

Path signals and file counts are navigation evidence only. They help select
source files for deeper review; they are not proof of a concurrency model,
storage engine, or runtime architecture. Content signals are bounded and use
simple text matching; they do not parse source or assert runtime behavior.

G4 analysis output is deliberately limited to deterministic observations:
tracked paths, counts, build markers, bounded source locations, and simple
content signals. These observations are navigation and evidence-selection
signals, not semantic facts about concurrency, storage, recovery, or runtime
architecture. Semantic features and claim types require source or official
documentation review.

## 6. Structural Draft Card

The analyzer converts deterministic observations into a conservative draft at
`data/drafts/<id>.json`. It uses the Architecture Card shape, but its initial
features are intentionally structural:

- observable repository structure;
- architecture-related path signals;
- build and integration surface;
- a finite labeled repository graph view;
- an evidence-prioritization signal view.

This draft is a navigation and evidence-preparation artifact. Semantic features
such as “MVCC” or “vectorized execution” should be added only after source or
official-document review.

## 7. Modeling Bundle schema

`mathen prepare-modeling` joins one deterministic report with one structural
draft at a fixed commit. It writes `data/modeling/<id>.json`:

```json
{
  "contract_version": 1,
  "system": {
    "id": "sqlite",
    "name": "SQLite",
    "category": "database",
    "repository": "...",
    "documentation": "...",
    "requested_ref": "master",
    "commit": "...",
    "commit_url": "...",
    "provenance": "github-archive"
  },
  "deterministic_observations": {},
  "existing_structural_draft": {},
  "modeling_task": {}
}
```

The `modeling_task` contains the modeling objective, questions about
abstractions and invariants, allowed claim types, evidence rules, and the
output schema, destination, and draft status.

The bundle is the boundary between deterministic inspection and semantic LLM
reasoning. It fixes the revision and limits the evidence IDs that the model may
use.

## 8. LLM output contract

The provider-neutral adapter sends a rendered bundle prompt to an
OpenAI-compatible `/chat/completions` endpoint. Configuration can come from:

```text
OPENAI_API_KEY
MATHEN_LLM_MODEL
MATHEN_LLM_BASE_URL
```

The adapter enforces these rules before writing a draft:

1. The response must contain one JSON object.
2. The returned card ID must equal the bundle system ID.
3. Every referenced evidence ID must exist in the structural draft.
4. Returned evidence records must be present and unchanged from the bundle.
5. The card must pass semantic Architecture Card validation.
6. Output must remain under the configured draft directory.
7. Existing draft files are not overwritten unless `--force` is supplied.

The adapter does not add evidence, infer historical influence, or promote a
card to `data/systems/`.

## 9. D1 relational schema

The Cloudflare API stores reviewed cards in normalized tables:

```text
systems
├── evidence
├── features ── feature_evidence ──> evidence
├── feature_relations ── feature_relation_evidence ──> evidence
├── mathematical_views ── mathematical_view_evidence ──> evidence
└── trade_offs ──> features

modeling_bundles
```

### `systems`

Stores `id`, `name`, `version_context`, `summary`, JSON-encoded `scope`, JSON-
encoded `related_systems`, and the source path.

### `evidence`

Stores evidence identity, owning `system_id`, `kind`, `title`, `uri`, and
optional access and notes fields.

### `features`

Stores feature identity within a system, name, category, claim type,
description, and JSON-encoded benefits and costs. The feature search and system
detail projections also return `evidence_ids` resolved from
`feature_evidence`.

### `feature_evidence`

Resolves the many-to-many relationship between features and evidence.

### `feature_relations` and `feature_relation_evidence`

Store source-card-owned directed relations between features, including the
target system and feature, claim metadata, and optional notes. The evidence join
table keeps relation evidence local to the source card and exposes card-local
IDs in API projections. Migration `0005_feature_relation_evidence_integrity.sql`
enforces that ownership in SQLite/D1, and the API omits corrupted rows rather
than serving cross-system evidence. The authoritative importer is
`apps/api/scripts/seed.ts`; it reads reviewed cards from `data/systems/` and
stores relation evidence as `${source_system_id}:${evidence_id}`. These tables
are intentionally separate from the system-only graph tables.

### `mathematical_views`

Stores model, question, JSON-encoded assumptions, claim type, and evidence
references in the system detail projection.

### `mathematical_view_evidence`

Resolves mathematical-view evidence references.

### `trade_offs`

Stores the feature reference and JSON-encoded benefits and costs.

### `modeling_bundles`

Stores the bundle ID, fixed `commit_sha`, `provenance`, complete `bundle_json`,
and source path. `commit_sha` is used instead of `commit` because `commit` is a
SQLite reserved word in the migration context.

The `systems` table also has optional JSON columns for
`temporal_context_json`, `relations_json`, and `composition_json`. Legacy
`version_context` and `related_systems_json` fields remain available to older
consumers.

## 10. HTTP API

The Hono Worker uses the `/api` base path. Successful responses use a
`{"data": ...}` envelope.

| Endpoint                                                                           | Purpose                                                                   |
| ---------------------------------------------------------------------------------- | ------------------------------------------------------------------------- |
| `GET /api/health`                                                                  | Worker health and environment                                             |
| `GET /api/systems?query=&limit=&offset=`                                           | Search reviewed system summaries in stable name/id order                  |
| `GET /api/systems/:id`                                                             | Retrieve one reviewed card projection                                     |
| `GET /api/features?query=&category=&claim_type=&limit=`                            | Search reviewed features                                                  |
| `GET /api/feature-relations?system_id=&feature_id=&target_system_id=&type=&limit=` | Search reviewed feature relations                                         |
| `GET /api/compositions?input_system=&claim_status=&limit=`                         | Search reviewed composition proposals, including cited evidence records   |
| `GET /api/modeling/:id`                                                            | Retrieve one fixed-commit modeling bundle                                 |
| `GET /api/graph`                                                                   | Return current system nodes and valid typed or legacy edges               |
| `GET /api/graph/layers?origin=`                                                    | Return the reviewed layered graph, optionally scoped by deployment origin |
| `GET /api/graph/models`                                                            | Return a navigational system-to-mathematical-model projection             |
| `GET /api/retrieval?q=&limit=&record_kind=...`                                     | Bounded lexical discovery over hydrated reviewed records                  |

The current API is read-only. It does not expose draft cards or provide review,
promotion, or synthesis writes.

All successful API reads use the `{"data": ...}` envelope. Errors are returned
as error objects with an HTTP status. Hosted browser requests use the same
origin; clients must not expose a deployment-specific API URL or secret in
browser code. Retrieval is a bounded lexical baseline, not semantic/vector
search. Its availability is deployment-specific: source implementation and
local tests do not prove that a hosted deployment has received the route.

System searches default to 50 results, with a maximum page size of 100. Use
`offset` (default 0) to read subsequent pages with the same query. Browser
metadata loading must cover every page; an unloaded system does not have zero
domains merely because it is absent from the first page.

The browser opens directly into a force-directed graph. Compact controls expose
search, relation filters, and planar or spatial exploration. Dragging a node
reheats the simulation so that connected nodes can respond. System descriptions,
features, mathematical views, and evidence are available on demand rather than
occupying the main canvas.

Typed edges retain their claim status and evidence IDs. A legacy `related`
edge provides navigation context when an older card has a valid
`related_systems` target without typed relation metadata. Domain browsing groups
are navigation aids; membership does not establish dependency, historical
influence, or architectural equivalence.

The mathematical-model projection is a separate graph. Its model nodes group
explicitly named mathematical views such as state-transition, queueing, or
refinement models. It retains each view's question, assumptions, claim type, and
source-local evidence IDs. A `modeled-by` edge is a navigation link, not
a dependency, equivalence, proof, or composition claim. Its claim label reflects
the attached views, or `mixed` when their claim types differ. Views can appear
in multiple wording-based families. Model search includes view titles,
questions, assumptions, and evidence IDs. A stable view key uses the system,
normalized model title, and question; changing those fields changes the key.

## 11. MCP interface

The stdio MCP server provides the same read boundary to agents:

| Tool                     | Inputs                                                                  | Result                                                              |
| ------------------------ | ----------------------------------------------------------------------- | ------------------------------------------------------------------- |
| `get_layered_graph`      | optional `origin`                                                       | Reviewed layered graph projection                                   |
| `list_systems`           | none                                                                    | Reviewed system summaries                                           |
| `get_system`             | `system_id`                                                             | One reviewed Architecture Card                                      |
| `search_features`        | `query`, optional `category`, `claim_type`, `limit`                     | Matching reusable features                                          |
| `list_feature_relations` | optional `system_id`, `feature_id`, `target_system_id`, `type`, `limit` | Matching evidence-backed feature relations                          |
| `list_compositions`      | optional `input_system`, `claim_status`, `limit`                        | Matching reviewed composition proposals with cited evidence records |
| `get_modeling_bundle`    | `system_id`                                                             | Fixed-commit modeling bundle                                        |

Without `MATHEN_API_URL`, the server uses the local filesystem. Filesystem mode
can include drafts for internal backend queries when explicitly requested, but
the registered stdio tools expose reviewed records only. With `MATHEN_API_URL`,
reviewed system, feature, relation, composition, graph, and bundle reads use
the Hono/D1 API; API mode rejects draft inclusion because the hosted API is
reviewed-only.

`list_feature_relations` reads source-card-owned, evidence-backed directed
relations. Its filters select the source system or feature, target system, and
relation type; results retain source-card claim metadata and source-local
evidence IDs. It is a read tool and does not infer, accept, or write a relation.

The G6 `mathen relation-candidates` command produces a deterministic,
review-only report. It never edits canonical cards or assigns a relation type,
claim type, direction, or review status. Its scores are triage priorities for
human review, not probabilities, semantic confidence, or proof; a
`missing-target` result identifies an unresolved catalog boundary.

## 12. End-to-end operation flow

### Step 1: Select repositories

Edit or extend `data/repositories/representative.json`. Choose a stable
reference and official documentation URL.

### Step 2: Acquire and inspect a fixed revision

```bash
uv run mathen analyze data/repositories/representative.json \
  --priority seed \
  --transport auto \
  --continue-on-error
```

The analyzer attempts a shallow Git checkout and can fall back to a GitHub
source archive. It records the resolved commit and writes a report plus a
structural draft. Failed repositories are recorded in
`data/analyses/failures.json` when continuation is enabled.

### Step 3: Prepare semantic modeling input

```bash
uv run mathen prepare-modeling --write-prompts
```

Only matching report/draft pairs become bundles. The bundle fixes provenance and
the evidence boundary before an LLM is called.

### Step 4: Generate an LLM draft

```bash
export OPENAI_API_KEY=...
export MATHEN_LLM_MODEL=gpt-4.1-mini
uv run mathen model --system sqlite
```

The result is written under `data/drafts/llm/` after parsing, evidence checks,
and card validation.

### Step 5: Review and promote deliberately

Review every claim against its cited source. Correct claim types, assumptions,
benefits, costs, and counterexamples. Only then add or update a canonical card
under `data/systems/` and run:

```bash
uv run mathen validate data/systems
```

There is currently no automatic promotion command. This is intentional: review
is a governance boundary, not a formatting step.

### Step 6: Seed the local D1 database

```bash
bun run db:reset:local
```

The seed script reads reviewed cards from `data/systems/` and fixed bundles from
`data/modeling/`, generates deterministic SQL, applies the D1 migrations, and
loads the relational projection. It does not load drafts, benchmark manifests,
or other research fixtures.

### Step 7: Browse through the API or MCP

Start the local application:

```bash
bun run dev
```

Then use the browser at `http://localhost:5173`, the API at
`http://localhost:8787/api`, or the MCP server:

```bash
MATHEN_API_URL=http://localhost:8787/api bun run mcp
```

### Step 8: Provide reviewed evidence

Open an issue or pull request with the source URI, version or commit, scope,
claim type, assumptions, and evidence IDs. Work in `data/drafts/` while a card
is being prepared; run validation and request human review before adding an
accepted card to `data/systems/`. Do not overwrite canonical cards from an
automated analysis, and do not treat a draft as public API/MCP content. The
hosted API and MCP currently provide reads only; authenticated review and
promotion writes are not available.

## 13. Recommended development loop

For a small change, run:

```bash
uv run mathen validate data/systems
uv run ruff format --check .
uv run ruff check .
uv run python -m unittest discover -s tests -v
bun run check
bun run build
git diff --check
```

For repository analysis, additionally inspect the fixed commit, source
provenance, generated report, draft evidence, and unresolved questions before
accepting semantic claims.

## 14. Current limits and future extensions

The current implementation has `version_context`, `related_systems`, fixed
commit provenance, and relational evidence links, but it does not yet provide a
full temporal graph schema. Planned extensions include:

- version and evolution nodes with validity intervals;
- typed `uses`, `extends`, `composes`, `resembles`, and `influenced-by` edges;
- explicit community and architecture-family nodes;
- composition records containing inputs, constraints, preserved properties,
  conflicts, and validation results;
- candidate architecture nodes separated from implemented systems;
- query and synthesis tools over those relations;
- authenticated draft review and promotion APIs.

Structural similarity alone must never be stored as historical influence, and a
mathematical view must not be presented as a formal proof without definitions,
assumptions, and validation.

# Reviewed-card relation graph report

## Scope and method

This report evaluates the six canonical cards currently under
`data/systems/`: `git`, `sqlite`, `duckdb`, `postgresql`, `firecracker`, and
`supabase`. It also evaluates draft cards that are plausible next review
targets. The question is: **which directed, typed relations can be recorded
without turning a generic similarity or an unreviewed repository signal into a
semantic claim?**

Evidence IDs in the tables are qualified by card when necessary. `source
evidence` means IDs that can be stored on a relation in the source card; the
semantic validator requires those IDs to exist in that card's own `evidence`
array. `target evidence` is the independently reviewed evidence that supports
the other endpoint and should be checked when the relation is reviewed. A
target evidence ID must not be copied into the source card unless it is also
defined there.

The relation vocabulary is the contract vocabulary: `uses`, `extends`,
`composes`, `resembles`, and `influenced-by`. Claim type and review status are
independent: `analogy` is appropriate for structural resemblance, while
`influenced-by` requires historical evidence. A candidate relation is marked
`proposed` until it is deliberately added to a canonical card and reviewed.

## Current graph inventory

There is currently one typed relation in the six canonical cards:

| Source | Type | Target | Claim type | Status | Source evidence IDs | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `sqlite` | `resembles` | `duckdb` | `analogy` | `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | Both are embedded database engines, but the cards explicitly distinguish SQLite's general/local and transactional orientation from DuckDB's analytical and vectorized orientation. The card note says this is structural comparison, not historical influence. |

The legacy `related_systems` arrays are broader and untyped. Restricting them
to the six canonical IDs gives one undirected component
`{git, sqlite, duckdb, postgresql, supabase}` and leaves `firecracker` in a
separate component. The `firecracker` links target `qemu` and `docker`, which
are not canonical cards. `git` also has a legacy link to `kubernetes`, and
`supabase` has one to `firebase`; neither target is a reviewed card.

Restricting the graph to typed relations gives five components:

```text
{sqlite, duckdb}   {git}   {postgresql}   {firecracker}   {supabase}
```

This is an inventory result, not a reason to add edges indiscriminately.

## Relation matrix for the six canonical cards

Cells identify a candidate relation ID. Reverse cells for a `resembles`
candidate are intentionally left empty: although resemblance is conceptually
symmetric, the stored contract is directed, and one canonical orientation
avoids duplicate assertions. `—` means that the inspected local evidence does
not justify a typed relation at this time.

| Source \\ Target | `git` | `sqlite` | `duckdb` | `postgresql` | `firecracker` | `supabase` |
| --- | --- | --- | --- | --- | --- | --- |
| `git` | — | — | — | — | — | — |
| `sqlite` | — | — | **R1** | **R2** | — | — |
| `duckdb` | — | — | — | **R3** | — | — |
| `postgresql` | — | — | — | — | — | — |
| `firecracker` | — | — | — | — | — | — |
| `supabase` | — | — | — | **R4** | — | — |

### Candidate relation details

| ID | Source → type → target | Claim type / status | Source evidence IDs | Target evidence IDs | Rationale and boundary |
| --- | --- | --- | --- | --- | --- |
| R1 | `sqlite` → `resembles` → `duckdb` | `analogy` / `proposed` (existing) | `sqlite-appropriate-uses`, `sqlite-architecture` | `duckdb-why` | Existing canonical relation. The shared structure is embedded database execution. It does not claim equivalent execution, workload, storage, or historical influence. |
| R2 | `sqlite` → `resembles` → `postgresql` | `analogy` / `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | `postgresql-architecture`, `postgresql-extensions` | Both expose relational query execution, but SQLite is an embedded/local engine and PostgreSQL is a client/server engine with a broader extension and multi-client boundary. This is a comparison of architecture choices, not lineage. |
| R3 | `duckdb` → `resembles` → `postgresql` | `analogy` / `proposed` | `duckdb-why` | `postgresql-architecture`, `postgresql-extensions` | Both are relational query engines with composable query execution, while DuckDB is embedded and analytical and PostgreSQL is client/server and extensible. The relation should remain an analogy until a comparison card or cross-card review makes the shared abstraction explicit. |
| R4 | `supabase` → `composes` → `postgresql` | `fact` / `proposed` | `supabase-architecture` | `postgresql-architecture`, `postgresql-extensions` | Supabase's architecture evidence explicitly identifies PostgreSQL as the core system around which APIs, authentication, realtime, storage, and management services are assembled. `composes` is more precise than `uses`; no historical copying claim is implied. |

R2 and R3 are useful graph edges but lower-confidence than R4 because their
shared structure is an abstraction across separate system cards. They should
not be represented as `extends` or `influenced-by`. R4 is a documented product
composition and is still marked `proposed` here because the relation is not
yet present in the canonical Supabase card.

## Pairwise decisions that should remain unlinked

The following pairs were considered and rejected or deferred rather than used
to force connectivity:

| Pair | Decision | Reason |
| --- | --- | --- |
| `git` with `sqlite`, `duckdb`, or `postgresql` | No candidate | Both may be described with broad storage or graph language, but the local Git evidence only establishes content-addressed objects, mutable references, and commit ancestry. It does not establish a typed dependency, composition, or a sufficiently specific cross-system analogy. |
| `git` with `firecracker` or `supabase` | No candidate | The cards expose unrelated boundaries and contain no local evidence of use, extension, composition, or historical influence. |
| `sqlite` or `duckdb` with `supabase` | No candidate | Supabase's card identifies PostgreSQL, not either embedded engine, as its database core. A generic shared database label is insufficient. |
| `postgresql` with `firecracker` | No candidate | The systems have no shared evidenced architectural boundary in the reviewed cards. |
| `firecracker` with another canonical card | No candidate | Firecracker's reviewed evidence supports a minimal KVM-backed VMM and isolation boundary, but none of the other five canonical cards supplies a matching composition or dependency boundary. Its useful comparison target is the unreviewed QEMU draft. |
| Any canonical pair as `influenced-by` | None | No card contains historical design-lineage evidence. Similar features or a product's use of a component do not establish influence. |
| Any canonical pair as `extends` | None | The current cards have no versioned inheritance or compatible base/derived implementation claim across these systems. Supabase's relationship to PostgreSQL is composition, not an extension of PostgreSQL's implementation. |

## Strong upcoming candidates

These are candidate paths for future reviewed cards. They are not additions to
the canonical graph. The source evidence IDs below are exact IDs in the named
draft or canonical card; the review gate is part of the recommendation.

| ID | Candidate source → type → target | Claim type / status | Source evidence IDs | Target evidence IDs | Review gate |
| --- | --- | --- | --- | --- | --- |
| R5 | `firecracker` → `resembles` → `qemu` | `analogy` / `proposed` | `firecracker-design` | None yet | QEMU's draft has only repository-structure and path-signal observations. Its `official-documentation` record is a URL placeholder, not an extracted semantic architecture claim. Review QEMU's device and VMM model before recording this edge. |
| R6 | `kafka` → `resembles` → `sqlite` | `analogy` / `proposed` | `kafka-introduction` | `sqlite-wal`, `sqlite-atomic-commit` | Kafka is still a draft, but its official introduction supports partitioned append logs, retention, replay, and ordering. The comparison is specifically log/replay/checkpoint structure; it does not claim that Kafka is a database or that SQLite provides Kafka's distributed replication. |
| R7 | `redis` → `resembles` → `sqlite` | `analogy` / `proposed` | `redis-persistence` | `sqlite-wal`, `sqlite-atomic-commit` | Redis's persistence evidence supports snapshots, append-only logging, replay, and selectable durability windows. The comparison must keep Redis's in-memory command state separate from SQLite's relational pager and transaction model. |
| R8 | `redis` → `resembles` → `kafka` | `analogy` / `proposed` | `redis-data-types`, `redis-persistence` | `kafka-introduction` | Redis Streams and Kafka both expose log-like event processing, but the draft evidence also states that Redis Streams do not automatically provide Kafka's distributed durability model. Both cards need review before this edge is canonical. |
| R9 | `mysql-server` → `resembles` → `postgresql` | `analogy` / `proposed` | None sufficient | `postgresql-architecture`, `postgresql-mvcc`, `postgresql-extensions` | Do not record yet. The MySQL draft only contains repository metrics, build markers, and weak path signals. A reviewed MySQL card needs server, storage-engine, transaction, and replication evidence first. |
| R10 | `rocksdb` → `resembles` → `sqlite` | `analogy` / `proposed` | None sufficient | `sqlite-architecture`, `sqlite-atomic-commit` | Do not record yet. RocksDB's draft has no semantic evidence for an LSM tree, compaction, snapshots, or recovery; its `architecture-path-signals` feature explicitly warns that path names are not architecture proof. |
| R11 | `docker` → `resembles` → `firecracker` | `analogy` / `proposed` | None sufficient | `firecracker-design` | Do not record yet. Docker's draft does not establish namespaces, cgroups, daemon boundaries, or container lifecycle semantics. Review those facts before comparing container and microVM isolation. |

The highest-value next review order for graph connectivity is QEMU, Kafka, and
Redis. QEMU can give Firecracker a reviewed comparison target. Kafka and Redis
can connect the log/replay family to SQLite's WAL evidence without implying a
dependency. MySQL, RocksDB, Docker, and Kubernetes should not be connected
from their current deterministic drafts: their cards currently say that their
repository observations are navigation signals rather than runtime claims.

## Composition bridge already present in drafts

`data/drafts/sqlite-duckdb-analytical-workflow.json` is a useful evidence-backed
composition proposal, but it is not a relation between canonical cards and
must remain in `data/drafts/` until reviewed. It has:

| Composition field | Exact evidence IDs | Claim status |
| --- | --- | --- |
| Inputs: SQLite transactional source; DuckDB analytical reader | SQLite: `sqlite-appropriate-uses`, `sqlite-wal`, `sqlite-atomic-commit`; DuckDB: `duckdb-why` | `accepted` per input |
| Overall composition | `sqlite-appropriate-uses`, `sqlite-wal`, `sqlite-atomic-commit`, `duckdb-why` | `proposed` |
| Constraints and preserved properties | Same IDs, with `sqlite-wal` and `sqlite-atomic-commit` for snapshot/durability boundaries | `proposed` or `under-review` per claim |
| Validation gaps | `sqlite-appropriate-uses`, `sqlite-wal`, `sqlite-atomic-commit`, `duckdb-why` | `proposed` |

Its strongest result is the explicit boundary: SQLite remains the sole write
authority and DuckDB reads a defined derived snapshot. Its conflicts include
staleness and shared host-resource contention. This composition supports R1's
structural comparison, but it does not by itself prove an implementation
connector or justify adding `uses`, `extends`, or `composes` to either
canonical card.

## Isolated and unsupported nodes

### Canonical nodes

| Node | Current typed degree | Current legacy context | Assessment |
| --- | ---: | --- | --- |
| `git` | 0 | Legacy links to `sqlite` and non-canonical `kubernetes` | Isolated in the typed graph. Keep isolated until a specific, evidenced relation is found; broad “history” resemblance is not enough. |
| `sqlite` | 1 outgoing | Legacy links to `duckdb`, `postgresql`, `git` | Best current typed anchor through R1. R2 is defensible as a proposed analogy; the draft composition gives a separate SQLite–DuckDB bridge. |
| `duckdb` | 0 | Legacy links to `sqlite`, `postgresql` | Isolated in the typed graph. R3 is a reasonable proposed analogy, but no reverse duplicate of R1 is needed. |
| `postgresql` | 0 | Legacy links to `sqlite`, `duckdb`, `supabase` | Isolated in the typed graph. R4 should originate at Supabase because the documented composition is platform-to-core. |
| `firecracker` | 0 | Legacy links to non-canonical `qemu` and `docker` | Isolated because its natural comparison targets are not reviewed. Do not use unreviewed target placeholders to manufacture an edge. |
| `supabase` | 0 | Legacy link to `postgresql` and non-canonical `firebase` | Isolated in the typed graph despite strong local evidence for R4. The missing typed edge is a review/projection gap, not missing architectural evidence. |

### Draft nodes with insufficient semantic support

Most generated drafts (`qemu`, `docker`, `kubernetes`, `elasticsearch`,
`mysql-server`, `rocksdb`, and the other repository-analysis outputs) contain
`repository-commit` evidence plus an `official-documentation` URL, but their
features explicitly describe repository structure, build markers, and weak
path signals. Those records are useful navigation inputs and do not support
typed system relations. They remain unsupported nodes until a semantic card
adds facts with evidence IDs for the proposed boundary.

Kafka and Redis are exceptions: their drafts contain detailed official-doc
evidence (`kafka-introduction`, `redis-data-types`, `redis-persistence`, and
`redis-resp`). They are still draft nodes, so R6–R8 are review candidates, not
canonical edges. The SQLite–DuckDB workflow draft is another exception because
it records a complete proposed composition with validation gaps.

## Conclusions

1. The current typed graph is intentionally sparse: one reviewed edge, one
   two-node component, and four typed isolates.
2. The next safe canonical edge is R4, `supabase` `composes` `postgresql`, with
   `supabase-architecture` as the source-local evidence ID. It is a documented
   composition, not historical influence.
3. R2 and R3 can connect the reviewed database family as `resembles` analogies
   if the project wants a denser comparison graph; they must retain `analogy`
   claim types and `proposed` status.
4. Firecracker should remain isolated until QEMU or Docker receives semantic
   review. Kafka and Redis provide the best upcoming evidence-backed bridges to
   SQLite's WAL and recovery models.
5. No `influenced-by` relation is currently supported. No relation should be
   added solely to make the graph connected.

# Reviewed-card relation graph report

## Scope and method

This report evaluates the 20 reviewed Architecture Cards currently under
`data/systems/`. It asks which directed, typed relations can be recorded
without turning generic similarity, legacy metadata, or an unreviewed
repository signal into a semantic claim.

The relation vocabulary is the card contract: `uses`, `extends`, `composes`,
`resembles`, and `influenced-by`. Claim type and review status are independent.
Structural comparison uses `analogy`; documented implementation or product
integration uses `fact`; every candidate remains `proposed` until a separate
card review adds it to a canonical card.

Evidence IDs in the source-evidence column are the only IDs that may be copied
into a source card relation. Target evidence is listed for review context and
must not be copied into the source card unless it is also defined there. A
`resembles` edge is stored in one direction to avoid duplicate assertions,
although the comparison itself may be conceptually symmetric.

## Reviewed-card inventory

The current reviewed set is:

```text
cpython, duckdb, elasticsearch, ffmpeg, firecracker, git, grpc, kafka,
kubernetes, linux, llvm, nginx, postgresql, protobuf, qemu, redis, rust,
sqlite, supabase, wasmtime
```

All 20 cards pass the semantic validator. They retain fixed source provenance,
local evidence IDs, bounded architecture features, mathematical views with
questions and assumptions, and explicit trade-offs. Draft cards remain outside
the reviewed graph and are not eligible as public API nodes.

## Current graph inventory

There are four typed relations in the reviewed cards:

| Source     | Type        | Target       | Claim type | Status     | Source evidence IDs                              | Boundary                                                                                                                    |
| ---------- | ----------- | ------------ | ---------- | ---------- | ------------------------------------------------ | --------------------------------------------------------------------------------------------------------------------------- |
| `sqlite`   | `resembles` | `duckdb`     | `analogy`  | `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | Embedded database execution is structurally comparable, but workload, storage, and execution models differ.                 |
| `sqlite`   | `resembles` | `postgresql` | `analogy`  | `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | Both expose relational query execution, but SQLite is embedded/local and PostgreSQL is client/server and extensible.        |
| `duckdb`   | `resembles` | `postgresql` | `analogy`  | `proposed` | `duckdb-why`                                     | Both are relational query engines, while DuckDB is embedded and analytical and PostgreSQL is client/server and extensible.  |
| `supabase` | `composes`  | `postgresql` | `fact`     | `proposed` | `supabase-architecture`                          | Supabase documents PostgreSQL as the core around which API, auth, realtime, storage, and management services are assembled. |

The graph API also emits 35 valid legacy `related_systems` edges. These edges
are retained for compatibility but carry no typed claim or evidence metadata.
The combined graph therefore contains 39 edges across 20 nodes.

### Connectivity summary

The typed graph alone has 17 connected components:

```text
{duckdb, postgresql, sqlite, supabase}
{cpython} {elasticsearch} {ffmpeg} {firecracker} {git} {grpc}
{kafka} {kubernetes} {linux} {llvm} {nginx} {protobuf} {qemu}
{redis} {rust} {wasmtime}
```

The combined typed-plus-legacy graph has five undirected components with sizes
`[11, 4, 2, 2, 1]`:

```text
{duckdb, elasticsearch, git, kafka, kubernetes, linux, nginx,
 postgresql, redis, sqlite, supabase}
{cpython, llvm, rust, wasmtime}
{firecracker, qemu}
{grpc, protobuf}
{ffmpeg}
```

This distinction matters: legacy links make the visual graph more navigable,
but they must not be presented as evidence-backed architecture relations.
The isolated `ffmpeg` node is an evidence result, not a defect to repair by
adding a generic stream, graph, or pipeline analogy.

## Review-ready bridge candidates

The following candidates are supported by the bridge-review reports but are
not canonical graph updates. Each requires deliberate review of the source
card and exact local evidence before insertion.

| ID  | Source → type → target                  | Claim type / status    | Source evidence IDs                               | Review boundary                                                                                                                                                                                                                                |
| --- | --------------------------------------- | ---------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| B1  | `grpc` → `uses` → `protobuf`            | `fact` / `proposed`    | `grpc-core-concepts`, `grpc-source-cpp-generator` | gRPC documents Protocol Buffers as the default service/message description and generates interfaces from descriptors. This does not claim every deployment uses Protobuf, that Protobuf implements transport, or that the dependency reverses. |
| B2  | `firecracker` → `resembles` → `qemu`    | `analogy` / `proposed` | `firecracker-design`                              | Both are VMMs with guest execution and device-model boundaries; Firecracker deliberately narrows the machine model while QEMU is broad and configurable. No implementation reuse, equivalence, or historical influence is implied.             |
| B3  | `rust` → `resembles` → `llvm`           | `analogy` / `proposed` | `rustc-overview`, `rust-fixed-source`             | The Rust card names LLVM IR in a staged compiler pipeline. This is not enough to claim that Rust uses the LLVM project as an implementation dependency, so the candidate remains an analogy pending review.                                    |
| B4  | `cpython` → `resembles` → `wasmtime`    | `analogy` / `proposed` | `cpython-execution-model`, `cpython-fixed-source` | Both expose embeddable runtime context and scoped execution state, but their APIs, isolation properties, and implementations differ.                                                                                                           |
| B5  | `redis` → `resembles` → `kafka`         | `analogy` / `proposed` | `redis-data-types`, `redis-persistence`           | Redis Streams and Kafka expose append/replay shapes, but Redis does not provide Kafka's partitioned replicated cluster contract.                                                                                                               |
| B6  | `redis` → `resembles` → `sqlite`        | `analogy` / `proposed` | `redis-persistence`                               | Redis snapshots/AOF and SQLite journal/WAL both represent durability choices, but Redis reconstructs in-memory command state while SQLite protects a relational pager.                                                                         |
| B7  | `kafka` → `resembles` → `sqlite`        | `analogy` / `proposed` | `kafka-introduction`                              | Kafka retained partition logs and SQLite WAL both expose append, replay/snapshot, and checkpoint boundaries; their ordering, replication, and transaction semantics differ.                                                                    |
| B8  | `kafka` → `resembles` → `elasticsearch` | `analogy` / `proposed` | `kafka-introduction`                              | Both distribute and replicate storage units, but Kafka stores ordered event logs and Elasticsearch stores searchable Lucene shards with scatter-gather queries.                                                                                |

`grpc uses protobuf` is the strongest direct dependency candidate. The
Firecracker/QEMU edge is the strongest virtualization comparison. The
Rust/LLVM candidate is intentionally conservative: one bridge report proposed
`uses`, while another rejected that claim because naming LLVM IR does not prove
use of the LLVM project. The current report therefore keeps it as a reviewable
analogy rather than adding a dependency edge.

## Relations deliberately rejected or deferred

- No reviewed pair supports `extends`; no compatible base/derived
  implementation or versioned inheritance claim is present.
- No reviewed pair supports `influenced-by`; no historical design-lineage
  evidence is present.
- `protobuf` → `uses` → `grpc` is not justified by the reviewed Protocol
  Buffers evidence; the documented dependency direction is gRPC to Protobuf.
- `kubernetes` → `uses` → `etcd` and `qemu` → `uses` → `kvm` are not emitted
  because the target cards are not reviewed nodes.
- `elasticsearch` → `uses` → `lucene` is deferred because Lucene is not a
  reviewed target card.
- Firecracker/QEMU, Linux/Kubernetes, Linux/NGINX, Kubernetes/NGINX, and
  Firecracker/Kubernetes are not connected through generic host, scheduler,
  process, event, or isolation vocabulary.
- FFmpeg has no reviewed evidence for a bridge to Protocol Buffers, gRPC, or
  any other current node. Shared terms such as stream, graph, or pipeline are
  insufficient.
- The existing legacy `related_systems` edges are not upgraded automatically:
  they are navigation context, not typed semantic claims.

## Composition and review boundary

`data/drafts/sqlite-duckdb-analytical-workflow.json` remains a draft
composition proposal. Its strongest boundary is that SQLite remains the write
authority while DuckDB reads a defined derived snapshot. It records staleness
and shared-resource conflicts, but it does not prove an implementation
connector or justify a `uses`, `extends`, or `composes` edge between the cards.

Candidate relation payloads must use evidence IDs local to the source card,
retain `claim_status: proposed`, and preserve the distinction between fact,
inference, hypothesis, and analogy. Review reports are evidence for a future
card edit; they are not themselves canonical relations.

## Conclusions

1. The reviewed graph has 20 nodes and four typed edges; its sparse typed
   connectivity is intentional.
2. Legacy edges produce five visually connected components, while the typed
   graph has one four-node database component and 16 typed isolates.
3. Review `grpc uses protobuf` first, followed by `firecracker resembles qemu`.
   Keep the boundary notes and source-local evidence IDs intact.
4. Keep `rust`/`llvm`, runtime analogies, and log/storage analogies as explicit
   review candidates until a maintainer accepts their semantic boundaries.
5. Do not add edges solely to make the graph connected. Additional reviewed
   cards and precise evidence-backed relations are preferable to dense but
   unsupported similarity links.

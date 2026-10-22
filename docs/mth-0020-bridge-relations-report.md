# MTH-0020 reviewed-card bridge relation report

## Scope and decision rule

This report evaluates the 20 reviewed cards in `data/systems/`, with focused
attention to `cpython`, `llvm`, `rust`, and `wasmtime`. It proposes typed
cross-card relations only when the source card contains local evidence for the
claim. The relation vocabulary is limited to `uses`, `extends`, `composes`,
`resembles`, and `influenced-by`.

The report does not edit cards. Every candidate has `claim_status: proposed`
because adding a relation to a canonical card requires a separate card review.
The source evidence IDs are the IDs that could legally be placed in the source
card's `relations` entry. Target evidence IDs are listed for independent
cross-card review and must not be copied into the source card unless they are
also defined there.

The reviewed-card set examined was:

```text
cpython, duckdb, elasticsearch, ffmpeg, firecracker, git, grpc, kafka,
kubernetes, linux, llvm, nginx, postgresql, protobuf, qemu, redis, rust,
sqlite, supabase, wasmtime
```

## Decision summary

Seven proposed relations are justified by the current local evidence:

- two direct `uses` relations: Rust → LLVM and gRPC → Protocol Buffers;
- five scoped `resembles` analogies: CPython ↔ Wasmtime, Firecracker → QEMU,
  Redis → Kafka, Redis → SQLite, and Kafka → SQLite.

The analogy orientation is deliberate. `resembles` is conceptually symmetric,
but the card contract stores directed assertions; only one orientation is
recommended for each pair. No `extends` or `influenced-by` relation is
justified. The evidence does not establish implementation inheritance,
historical design lineage, or equivalence for any new pair.

## Proposed bridge relations

| ID | Source → relation → target | Claim type / status | Source feature anchor | Exact source evidence IDs | Target evidence IDs for review | Boundary note |
| --- | --- | --- | --- | --- | --- | --- |
| B1 | `rust` → `uses` → `llvm` | `fact` / `proposed` | `multi-stage-compiler-ir` | `rustc-overview`, `rust-fixed-source` | `llvm-langref`, `llvm-getting-started` | Rust's compiler pipeline includes LLVM IR and a backend boundary. This does not claim that every Rust compiler stage uses LLVM, that Rust uses every LLVM component, or that Rust's MIR is equivalent to LLVM IR. |
| B2 | `grpc` → `uses` → `protobuf` | `fact` / `proposed` | `idl-defined-service-boundary`, `generated-transport-facing-stubs` | `grpc-core-concepts`, `grpc-source-cpp-generator` | `protobuf-language-guide`, `protobuf-source-plugin` | gRPC uses Protocol Buffers by default for service and message descriptions and generates bindings from descriptors. This does not reverse the dependency, require protobuf for every gRPC serialization path, or claim that protobuf depends on gRPC. |
| B3 | `cpython` → `resembles` → `wasmtime` | `analogy` / `proposed` | `interpreter-and-thread-state-hierarchy` | `cpython-execution-model`, `cpython-fixed-source` | `wasmtime-architecture`, `wasmtime-fixed-source` | Both expose an embeddable runtime with a reusable or global context and scoped execution state: CPython runtime/interpreter/thread state versus Wasmtime Engine/Store. The analogy does not claim compatible APIs, equivalent isolation, or a shared implementation. |
| B4 | `firecracker` → `resembles` → `qemu` | `analogy` / `proposed` | `minimal-machine-model`, `kvm-event-driven-vmm` | `firecracker-design` | `qemu-system-emulation`, `qemu-kvm-source`, `qemu-qom-doc` | Both provide a VMM boundary around guest execution and virtual devices, with KVM available in the execution path. Firecracker deliberately models one small microVM, while QEMU supports broader machine emulation and composition; no lineage or compatibility is implied. |
| B5 | `redis` → `resembles` → `kafka` | `analogy` / `proposed` | `append-only-stream-data-structure`, `selectable-persistence-representations` | `redis-data-types`, `redis-persistence` | `kafka-introduction` | Redis Streams and Kafka both expose append-oriented event history and replay-related workflows. Redis's stream is a Redis data structure and its persistence modes do not provide Kafka's partitioned, replicated cluster contract; the analogy is limited to the log/replay shape. |
| B6 | `redis` → `resembles` → `sqlite` | `analogy` / `proposed` | `selectable-persistence-representations` | `redis-persistence` | `sqlite-wal`, `sqlite-atomic-commit` | Redis AOF/RDB persistence and SQLite journal/WAL mechanisms both represent recovery and durability choices involving append, replay, or snapshots. Redis remains an in-memory data-structure server and SQLite remains a relational pager/database; this is not a database equivalence claim. |
| B7 | `kafka` → `resembles` → `sqlite` | `analogy` / `proposed` | `partitioned-append-log`, `retained-replayable-events` | `kafka-introduction` | `sqlite-wal`, `sqlite-atomic-commit` | Kafka's retained partition log and SQLite's WAL both expose append, replay/snapshot, and checkpoint or retention boundaries. Kafka is distributed event storage, while SQLite's WAL is a local database concurrency and recovery mechanism; neither supplies the other's ordering, replication, or transaction semantics. |

### Candidate handling notes

B1 and B2 are direct dependency or integration claims and are the strongest
new candidates. B3–B7 are intentionally `analogy` claims. Their boundary
notes identify the specific shared shape and the semantics that must not be
collapsed when a reviewer considers adding an edge.

The existing typed relations remain valid inventory entries and are not
duplicated by this report:

| Source → relation → target | Claim type / status | Source evidence IDs |
| --- | --- | --- |
| `sqlite` → `resembles` → `duckdb` | `analogy` / `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` |
| `sqlite` → `resembles` → `postgresql` | `analogy` / `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` |
| `duckdb` → `resembles` → `postgresql` | `analogy` / `proposed` | `duckdb-why` |
| `supabase` → `composes` → `postgresql` | `fact` / `proposed` | `supabase-architecture` |

## Relations not justified by the reviewed evidence

The following are deliberate no-candidate decisions rather than missing graph
edges:

- **CPython ↔ Rust:** the cards describe different object-lifetime models
  (reference management versus ownership and borrowing), but do not establish
  dependency, composition, or a sufficiently specific shared abstraction.
- **LLVM ↔ CPython:** CPython's execution-frame and bytecode-oriented runtime
  evidence does not establish LLVM IR use or a compiler-infrastructure
  boundary.
- **LLVM ↔ Wasmtime:** both cards mention compilation, but the local evidence
  does not identify Wasmtime's compiler backend as LLVM or establish a common
  transformation contract.
- **Rust ↔ Wasmtime:** Wasmtime's card does not establish that its reviewed
  architecture depends on Rust, and Rust's card does not describe Wasmtime.
  Repository language or project ownership would not be enough for a typed
  relation without a corresponding local architecture claim.
- **Elasticsearch ↔ Kafka, Elasticsearch ↔ SQLite, and Elasticsearch ↔ Redis:**
  shard replication, translog recovery, persistence, and replay create useful
  comparison topics, but the reviewed evidence does not establish one precise
  shared contract without conflating indexed document state, recovery logs,
  and event history.
- **QEMU ↔ Linux, Firecracker ↔ Linux, Kubernetes ↔ Linux, and NGINX ↔
  Linux:** the cards expose host or platform boundaries, but the available
  evidence does not state a source-local relation strong enough to distinguish
  a specific `uses` claim from generic deployment compatibility.
- **Git, FFmpeg, and the remaining cross-domain pairs:** no local evidence
  establishes a typed dependency, composition, inheritance, or sufficiently
  specific analogy. Their legacy `related_systems` values are not promoted to
  typed relations by this analysis.

No reviewed pair supports `extends`: there is no compatible base/derived
implementation or versioned inheritance claim in the cards. No reviewed pair
supports `influenced-by`: none of the evidence records historical design
lineage. Structural resemblance must remain `analogy`, and product use or
assembly must remain `fact` with `uses` or `composes` as appropriate.

## Recommendation

Treat B1–B7 as review-ready candidates, not canonical graph updates. If only
the highest-confidence bridges are reviewed first, use B1, B2, and B4. Review
B3 and B5–B7 only with their boundary notes intact. Keeping the other pairs
unlinked preserves the distinction between an evidence-backed bridge and a
generic similarity.

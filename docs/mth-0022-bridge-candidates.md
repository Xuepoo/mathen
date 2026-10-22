# MTH-0022 reviewed-card bridge candidates

## Scope and method

This report compares every reviewed card in `data/systems/`, with particular
attention to Protocol Buffers, gRPC, and FFmpeg. It records only relations
whose source card already contains the required local evidence ID. The
relation vocabulary is limited to `uses`, `extends`, `composes`, `resembles`,
and `influenced-by`; claim types and review statuses use the existing card
contract. These are candidates for deliberate review, not edits to canonical
cards.

Evidence IDs in the source-evidence column are exact IDs from the source card
and are the only IDs that could be placed on a relation in that card. Target
evidence is listed for review context and must not be copied into the source
card unless it is also defined there.

## Decision summary

One relation is supported as a direct dependency fact:

| Candidate | Claim type / status | Source evidence | Target evidence | Decision |
| --- | --- | --- | --- | --- |
| `grpc` → `uses` → `protobuf` | `fact` / `proposed` | `grpc-core-concepts`, `grpc-source-cpp-generator` | `protobuf-language-guide`, `protobuf-source-plugin` | **Justified.** The gRPC card explicitly states that gRPC uses Protocol Buffers by default for service and message descriptions, and its fixed C++ generator emits client/server interfaces from method descriptors. The boundary is default service/message description and generated-interface integration; it does not claim that every gRPC deployment uses protobuf, that protobuf implements the RPC transport, or that the systems are equivalent. |

The following structural analogies are also supported as precise proposed
comparisons. They should remain `resembles`/`analogy`, not dependency,
composition, inheritance, or historical lineage claims:

| Candidate | Claim type / status | Source evidence | Target evidence | Boundary note |
| --- | --- | --- | --- | --- |
| `firecracker` → `resembles` → `qemu` | `analogy` / `proposed` | `firecracker-design` | `qemu-system-emulation`, `qemu-kvm-source`, `qemu-qom-doc` | Both are KVM-capable virtual-machine monitors with guest CPU execution and device-model boundaries. Firecracker deliberately limits its device model and targets microVM density; QEMU provides a broad, configurable machine and device model and can also use TCG. This compares virtualization-boundary choices, not implementation reuse, substitutability, or historical influence. |
| `rust` → `resembles` → `llvm` | `analogy` / `proposed` | `rustc-overview`, `rust-fixed-source` | `llvm-langref`, `llvm-passes`, `llvm-getting-started` | Both expose staged compiler representations and transformation/code-generation pipelines; the Rust card specifically names LLVM IR as one stage. The relation does not claim that Rust is implemented by all of LLVM, that LLVM owns Rust's earlier IRs or borrow checking, or that their pass systems are interchangeable. |
| `kafka` → `resembles` → `redis` | `analogy` / `proposed` | `kafka-introduction` | `redis-data-types`, `redis-persistence` | Both provide append-oriented, replay-related event representations. Kafka provides distributed partitioned retained logs with consumer decoupling and replication; Redis Streams are a native data structure, and Redis persistence has separate RDB/AOF representations. The relation excludes equivalent durability, replication, retention, ordering scope, or consumer-group semantics. |
| `kafka` → `resembles` → `elasticsearch` | `analogy` / `proposed` | `kafka-introduction` | `elasticsearch-cluster-shards`, `elasticsearch-read-write`, `elasticsearch-translog` | Both distribute state across partitions/shards and replicate storage units for fault tolerance. Kafka's unit is a retained ordered event log; Elasticsearch's unit is a searchable Lucene shard with scatter-gather query and translog recovery. The relation does not claim that Elasticsearch is a log broker, that Kafka supplies search semantics, or that their replication and recovery protocols match. |

## Pairwise decisions that remain unlinked

### Protocol Buffers, gRPC, and FFmpeg

The `grpc` → `uses` → `protobuf` candidate is the only direct bridge among
these three cards. The Protocol Buffers card establishes schema encoding,
unknown-field handling, descriptor-driven generation, and numbered evolution,
but it does not contain evidence that gRPC is part of the Protocol Buffers
implementation. Therefore the reverse `protobuf` → `uses` → `grpc` direction
is not justified. `resembles` would also be less precise than the documented
gRPC dependency.

FFmpeg has no reviewed evidence of a relation to either system. Its format
contexts, codec send/receive state machine, and negotiated filter graph are
media-processing boundaries. Shared words such as “stream”, “generated”, or
“graph” do not establish a typed architecture relation. No FFmpeg bridge is
justified.

### Other reviewed cards

| Pair or source | Decision | Reason and boundary |
| --- | --- | --- |
| `qemu` → `resembles` → `firecracker` | Do not add a reverse duplicate | The same virtualization comparison is best oriented from the deliberately minimal VMM to the broader reference point. A second directed `resembles` edge would duplicate the candidate rather than add evidence. |
| `sqlite`, `duckdb`, `postgresql`, `supabase` | Existing candidates remain sufficient | The current cards already contain SQLite/DuckDB and database-family candidates, plus `supabase` → `composes` → `postgresql`. The new reviewed set does not add a stronger cross-database bridge. |
| `redis` ↔ `sqlite` | No new candidate | Both have persistence/recovery evidence, but Redis reconstructs in-memory command state from snapshots/AOF while SQLite protects a relational pager/database file with rollback journal or WAL. The boundary difference is too important for a stronger relation than the existing documented candidate. |
| `elasticsearch` → `resembles` → `kafka` | Prefer the Kafka-oriented candidate | The shared partition/replica abstraction is captured without a reverse duplicate by `kafka` → `resembles` → `elasticsearch`; Elasticsearch's searchable-shard and scatter-gather boundary should remain explicit. |
| `kubernetes` → `uses` → `linux` | No relation from reviewed evidence | Kubernetes' card establishes a control-plane/API/storage/scheduling architecture, while Linux's card establishes kernel resource and module boundaries. The cards do not document Kubernetes' runtime dependency on Linux. |
| `nginx` → `uses` → `linux` | No relation from reviewed evidence | NGINX evidence documents event and process architecture but does not establish a Linux-specific implementation dependency; its event boundary abstracts over epoll, kqueue, and select. |
| `rust` ↔ `cpython`, `llvm` ↔ `cpython`, `wasmtime` ↔ `rust`/`llvm` | No additional relation | The cards share runtime or compiler vocabulary, but no local evidence establishes use, composition, implementation lineage, or a sufficiently specific structural comparison beyond the Rust/LLVM candidate. |
| Any pair as `extends` | None justified | No reviewed pair supplies a compatible base/derived implementation or versioned inheritance claim. |
| Any pair as `influenced-by` | None justified | The reviewed evidence contains architecture facts and fixed revisions, but no historical design-lineage evidence. Similarity and dependency are not influence. |

## Suggested relation payloads for review

If a maintainer chooses to record the candidates after review, the source-card
payloads would be:

```json
{
  "type": "uses",
  "target": "protobuf",
  "claim_type": "fact",
  "claim_status": "proposed",
  "evidence_ids": ["grpc-core-concepts", "grpc-source-cpp-generator"],
  "notes": "gRPC uses Protocol Buffers by default for service and message descriptions and generates client/server interfaces from method descriptors; this does not claim that every deployment uses protobuf or that protobuf implements the RPC transport."
}
```

```json
{
  "type": "resembles",
  "target": "qemu",
  "claim_type": "analogy",
  "claim_status": "proposed",
  "evidence_ids": ["firecracker-design"],
  "notes": "Both are KVM-capable virtual-machine monitors, while Firecracker deliberately limits its device model and QEMU provides a broad configurable machine model; this is a structural comparison, not implementation reuse or historical influence."
}
```

The Rust/LLVM, Kafka/Redis, and Kafka/Elasticsearch payloads should use the
same relation shape and the exact source evidence IDs shown in the tables.
No payload is being added to a canonical card by this report.

## Conclusion

At least one relation is justified: `grpc` → `uses` → `protobuf` as a
proposed fact. Four additional `resembles` candidates are precise enough to
review, with the boundaries stated above. No relation involving FFmpeg is
justified by the reviewed evidence, and no `extends` or `influenced-by`
relation is supported. The graph should remain sparse where the cards do not
establish a concrete dependency or comparison boundary.

# Mathen Catalog Backlog

This is the long-term catalog of systems, languages, libraries, runtimes,
protocols, and infrastructure that Mathen may analyze.

Every future modeling effort should begin with an entry in this catalog. The
operational repository manifest in `data/repositories/representative.json` is a
downloadable subset of this catalog; it may grow as entries become ready for
source analysis.

## Status vocabulary

| Status | Meaning |
| --- | --- |
| `reviewed` | A reviewed Architecture Card exists under `data/systems/` |
| `draft` | A generated or manually prepared card exists under `data/drafts/` |
| `cataloged` | The repository is in the operational analysis manifest or has a deterministic report |
| `planned` | The target is selected but analysis has not started |
| `candidate` | A possible future target that still needs scope or source selection |

## Priority vocabulary

| Priority | Meaning |
| --- | --- |
| `P0` | Foundational target needed to establish a domain or cross-domain relation |
| `P1` | High-value representative target for the next modeling rounds |
| `P2` | Useful comparative or specialized target |
| `P3` | Long-term expansion target |

## Current implementation status

These entries are already present in the repository at different review levels:

| ID | Name | Domain | Status | Next action |
| --- | --- | --- | --- | --- |
| `git` | Git | version control | `reviewed` | Add temporal commits, refs, and composition relations |
| `duckdb` | DuckDB | analytical database | `reviewed` | Compare with SQLite and columnar engines |
| `firecracker` | Firecracker | microvirtualization | `reviewed` | Compare with QEMU and container isolation |
| `supabase` | Supabase | backend platform | `reviewed` | Model platform composition and lineage |
| `sqlite` | SQLite | embedded database | `reviewed` | Compare with DuckDB and columnar engines |
| `postgresql` | PostgreSQL | relational database | `reviewed` | Compare PostgreSQL MVCC and extension boundaries with SQLite and Supabase using fixed-commit evidence |
| `redis` | Redis | in-memory data service | `reviewed` | Compare native structures, RESP, and persistence representations |
| `elasticsearch` | Elasticsearch | search engine | `reviewed` | Compare shard partitioning, scatter-gather search, replication, and near-real-time visibility |
| `kafka` | Apache Kafka | distributed log | `reviewed` | Compare partitioned logs, replay, replication, and stream processing |
| `zookeeper` | Apache ZooKeeper | coordination service | `reviewed` | Compare hierarchical coordination state, sessions, watches, and quorum ordering using fixed-commit evidence |
| `etcd` | etcd | distributed key-value store | `reviewed` | Compare Raft-backed revisions, transactions, watches, and leases using fixed-commit evidence |
| `consul` | Consul | service networking | `reviewed` | Compare service catalog, health-aware discovery, datacenter topology, and distributed KV using fixed-commit evidence |
| `rabbitmq` | RabbitMQ | message broker | `reviewed` | Compare exchange routing, durable queues, acknowledgements, confirms, and flow control using fixed-commit evidence |
| `mysql-server` | MySQL Server | database | `reviewed` | Compare storage-engine, transaction, and recovery boundaries with PostgreSQL and SQLite |
| `rocksdb` | RocksDB | embedded database | `reviewed` | Compare LSM, WAL, compaction, and snapshot boundaries with SQLite and Redis |
| `docker` | Docker Engine | container runtime | `draft` | Compare daemon, image, namespace, and filesystem boundaries |
| `containerd` | containerd | container runtime | `reviewed` | Compare runtime-v2 shims, typed plugins, client boundaries, and content/snapshot lifecycle using fixed-revision evidence |
| `runc` | runc | container runtime | `reviewed` | Compare OCI bundle refinement, Linux isolation primitives, lifecycle state, and checkpoint boundaries using fixed-revision evidence |
| `kata-containers` | Kata Containers | container runtime | `reviewed` | Compare VM-backed sandbox layers, shim/agent/hypervisor composition, and CRI-to-device mapping using fixed-revision evidence |
| `gvisor` | gVisor | container runtime | `reviewed` | Compare Sentry/Gofer mediation, OCI runtime integration, and selectable syscall interception platforms using fixed-revision evidence |
| `qemu` | QEMU | virtualization | `reviewed` | Compare complete machine emulation with Firecracker |
| `kubernetes` | Kubernetes | orchestration | `reviewed` | Analyze reconciliation, API resources, and etcd state |
| `linux` | Linux Kernel | operating system | `reviewed` | Analyze system calls, scheduling, memory, and modules |
| `hadoop` | Apache Hadoop | distributed storage and compute | `cataloged` | Analyze HDFS, YARN, and batch computation |
| `nginx` | NGINX | network server | `reviewed` | Analyze event-driven I/O and worker processes |
| `llvm` | LLVM | compiler infrastructure | `reviewed` | Add temporal IR and pass-pipeline relations |
| `gcc` | GCC | compiler | `reviewed` | Compare front-end, IR, pass, and target-backend boundaries with LLVM |
| `tree-sitter` | tree-sitter | parser library | `reviewed` | Compare incremental concrete syntax trees with compiler front ends |
| `coreutils` | GNU Coreutils | Unix system tools | `reviewed` | Compare command composition and multi-call packaging with BusyBox |
| `boost` | Boost | C++ library | `reviewed` | Compare modular headers, binary components, and build configuration with Rust and LLVM |
| `ffmpeg` | FFmpeg | media processing | `reviewed` | Compare format contexts, codec state machines, and filter graphs using fixed-commit evidence |
| `protobuf` | Protocol Buffers | serialization protocol | `reviewed` | Compare numbered schema evolution and generated interfaces with gRPC using fixed-commit evidence |
| `grpc` | gRPC | RPC framework | `reviewed` | Compare generated service boundaries and streaming lifecycle with Protocol Buffers using fixed-commit evidence |
| `cpython` | CPython | language runtime | `reviewed` | Compare interpreter state, object lifetime, and extension boundaries |
| `rust` | Rust | language toolchain | `reviewed` | Compare ownership, compiler IR, and incremental query boundaries |
| `wasmtime` | Wasmtime | WebAssembly runtime | `reviewed` | Compare Engine/Store isolation and JIT compilation boundaries |
| `lua` | Lua | language runtime | `reviewed` | Compare embeddable VM state, coroutines, and extension boundaries |
| `node` | Node.js | JavaScript runtime | `reviewed` | Compare event-loop scheduling, module loading, and native extension boundaries |
| `deno` | Deno | JavaScript runtime | `reviewed` | Compare permission-scoped execution and module graph boundaries |
| `v8` | V8 | JavaScript engine | `reviewed` | Compare isolate/context state, handles, and managed heap boundaries |

The operational manifest now contains 44 repositories. The following entries
were added during the foundational catalog expansion and are ready for bounded
deterministic analysis, but they do not yet have reviewed Architecture Cards:

| ID | Name | Domain | Priority |
| --- | --- | --- | --- |
| `cpython` | CPython | language runtime | `P1` |
| `rust` | Rust | language toolchain | `P1` |
| `go` | Go | language toolchain | `reviewed` | Compare goroutine/channel ordering, package interfaces, and toolchain integration using fixed-commit evidence |
| `ruby` | Ruby | language runtime | `reviewed` | Compare dynamic object dispatch, VM frames, GC, and the C extension boundary using fixed-commit evidence |
| `wasmtime` | Wasmtime | WebAssembly runtime | `P1` |
| `freebsd` | FreeBSD | operating system | `P2` |
| `systemd` | systemd | init system | `P1` |
| `xv6-public` | xv6 | educational operating system | `P1` |
| `libuv` | libuv | asynchronous I/O library | `reviewed` | Compare event-loop, handle/request, cross-platform, and thread-pool boundaries using fixed-commit evidence |
| `curl` | curl | network library | `reviewed` | Compare easy/multi handles, transfer state machines, and connection reuse using fixed-commit evidence |
| `openssl` | OpenSSL | cryptography library | `reviewed` |
| `protobuf` | Protocol Buffers | serialization protocol | `P1` |
| `grpc` | gRPC | RPC framework | `P1` |
| `mosquitto` | Eclipse Mosquitto | messaging protocol | `reviewed` |
| `mysql-server` | MySQL Server | database | `reviewed` |
| `rocksdb` | RocksDB | embedded database | `reviewed` |
| `threejs` | Three.js | 3D graphics library | `P1` |
| `blender` | Blender | 3D graphics application | `P2` |
| `sdl` | SDL | multimedia library | `P2` |

## Catalog

The following list is the intended expansion order. The IDs are stable Mathen
identifiers, not claims that the projects share the same architecture.

### Foundational operating systems and system software

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `unix` | Unix history and interfaces | `P0` | Process, file, pipe, and permission abstractions |
| `linux` | Linux Kernel | `P0` | Kernel resource model, syscalls, scheduling, and modules |
| `freebsd` | FreeBSD | `P1` | Unix kernel, networking, jails, and ports |
| `openbsd` | OpenBSD | `P2` | Security-oriented defaults and audited system design |
| `plan9` | Plan 9 | `P1` | Uniform namespace, distributed resources, and 9P |
| `minix` | MINIX 3 | `P2` | Microkernel services and fault isolation |
| `systemd` | systemd | `P1` | Service supervision, dependency graph, and lifecycle state |
| `busybox` | BusyBox | `P2` | Multi-call binary and minimal userland composition |
| `coreutils` | GNU Coreutils | `P2` | Unix command algebra and composable process interfaces |
| `musl` | musl libc | `P1` | Portable C runtime and static-linking boundary |
| `glibc` | GNU C Library | `P1` | ABI, dynamic linking, and operating-system interface |

### Programming languages and language runtimes

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `c` | C | `P0` | Manual memory, ABI, compilation, and systems interface |
| `cpp` | C++ | `P0` | Zero-cost abstractions, ownership conventions, and templates |
| `rust` | Rust | `P0` | Ownership, borrowing, algebraic types, and async runtimes |
| `go` | Go | language toolchain | `reviewed` | Compare goroutine/channel ordering, package interfaces, and toolchain integration using fixed-commit evidence |
| `python` | Python | `P1` | Dynamic object model, interpreter, modules, and ecosystem |
| `javascript` | JavaScript | `P1` | Dynamic language semantics and event-loop execution |
| `typescript` | TypeScript | `P1` | Erased static typing and gradual boundary design |
| `java` | Java | `P1` | Managed runtime, bytecode, GC, and virtual machine |
| `kotlin` | Kotlin | `P2` | JVM language design, nullability, and multiplatform compilation |
| `lua` | Lua | `P0` | Embeddable interpreter, minimal core, and extension API |
| `ruby` | Ruby | language runtime | `reviewed` | Compare dynamic object dispatch, VM frames, GC, and the C extension boundary using fixed-commit evidence |
| `erlang` | Erlang/OTP | `P0` | Actor processes, supervision trees, and fault tolerance |
| `elixir` | Elixir | `P1` | BEAM abstractions, message passing, and supervision |
| `haskell` | GHC/Haskell | `P1` | Laziness, type classes, purity, and compiler pipeline |
| `ocaml` | OCaml | `P2` | Algebraic types, modules, and native compilation |
| `zig` | Zig | `P2` | Explicit allocation, comptime, and systems toolchain |
| `wasm` | WebAssembly | `P0` | Portable instruction format, sandboxing, and embedding |

### Compilers, interpreters, and language infrastructure

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `gcc` | GCC | `P0` | Multi-language frontends, middle-end, and backends |
| `llvm` | LLVM | `P0` | Intermediate representation and optimization passes |
| `clang` | Clang | `P1` | C-family frontend and tooling architecture |
| `rustc` | rustc | `P1` | Type checking, borrow checking, MIR, and code generation |
| `cpython` | CPython | `P1` | Bytecode VM, reference counting, and extension boundary |
| `v8` | V8 | `P1` | JIT compilation, hidden classes, and managed heap |
| `luajit` | LuaJIT | `P2` | Tracing JIT and embeddable runtime boundary |
| `tree-sitter` | Tree-sitter | `P1` | Incremental parsing and concrete syntax trees |
| `antlr` | ANTLR | `P2` | Grammar-driven parser and code-generation pipeline |
| `protobuf` | Protocol Buffers | `P0` | Schema evolution, serialization, and compatibility |
| `grpc` | gRPC | `P1` | RPC contracts, streaming, and generated clients |

### Databases and storage engines

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `sqlite` | SQLite | `P0` | Embedded execution, pager, B-tree, WAL, and VFS |
| `postgresql` | PostgreSQL | `P0` | MVCC, extensibility, planner, and extension ecosystem |
| `mysql` | MySQL | `P1` | SQL server, storage-engine boundary, and replication |
| `mariadb` | MariaDB | `P2` | MySQL lineage, pluggable engines, and compatibility |
| `duckdb` | DuckDB | `P0` | Embedded OLAP, columnar storage, and vectorization |
| `redis` | Redis | `P0` | In-memory structures, event loop, and persistence |
| `rocksdb` | RocksDB | `P0` | LSM tree, compaction, write buffers, and snapshots |
| `leveldb` | LevelDB | `P1` | Minimal LSM storage and log-structured recovery |
| `foundationdb` | FoundationDB | `P1` | Ordered key-value transactions and layered database design |
| `mongodb` | MongoDB | `P1` | Document model, indexes, replication, and sharding |
| `cassandra` | Apache Cassandra | `P1` | Partitioned wide-column storage and tunable consistency |
| `cockroachdb` | CockroachDB | `P1` | Distributed SQL, ranges, consensus, and serializability |
| `tidb` | TiDB | `P2` | Distributed SQL, coprocessors, and separated storage |
| `tikv` | TiKV | `P2` | Distributed transactional key-value storage and Raft |
| `clickhouse` | ClickHouse | `P1` | Columnar analytics, vectorized execution, and merge trees |
| `influxdb` | InfluxDB | `P2` | Time-series layout, retention, and compaction |
| `neo4j` | Neo4j | `P2` | Property graph storage and traversal execution |

### Distributed systems, messaging, and coordination

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `kafka` | Apache Kafka | `P0` | Partitioned append-only log and consumer offsets |
| `hadoop` | Apache Hadoop | `P1` | Distributed filesystem and batch resource scheduling |
| `zookeeper` | Apache ZooKeeper | `reviewed` | Compare hierarchical coordination state, sessions, watches, and quorum ordering using fixed-commit evidence |
| `etcd` | etcd | `reviewed` | Compare Raft-backed revisions, transactions, watches, and leases using fixed-commit evidence |
| `consul` | Consul | `reviewed` | Compare service catalog, health-aware discovery, datacenter topology, and distributed KV using fixed-commit evidence |
| `rabbitmq` | RabbitMQ | `reviewed` | Compare exchange routing, durable queues, acknowledgements, confirms, and flow control using fixed-commit evidence |
| `nats` | NATS | `P1` | Lightweight messaging, subjects, and stream persistence |
| `pulsar` | Apache Pulsar | `P2` | Segmented logs, brokers, and separated storage |
| `flink` | Apache Flink | `P1` | Stateful stream processing and event-time semantics |
| `spark` | Apache Spark | `P1` | Distributed dataflow, DAG scheduling, and resilient datasets |
| `ray` | Ray | `P2` | Distributed task and actor execution |

### Containers, virtualization, and orchestration

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `docker` | Docker Engine | `P0` | Images, namespaces, cgroups, and daemon boundary |
| `containerd` | containerd | container runtime | `reviewed` | Compare runtime-v2 shims, typed plugins, client boundaries, and content/snapshot lifecycle using fixed-revision evidence |
| `runc` | runc | container runtime | `reviewed` | Compare OCI bundle refinement, Linux isolation primitives, lifecycle state, and checkpoint boundaries using fixed-revision evidence |
| `kata-containers` | Kata Containers | container runtime | `reviewed` | Compare VM-backed sandbox layers, shim/agent/hypervisor composition, and CRI-to-device mapping using fixed-revision evidence |
| `gvisor` | gVisor | container runtime | `reviewed` | Compare Sentry/Gofer mediation, OCI runtime integration, and selectable syscall interception platforms using fixed-revision evidence |
| `qemu` | QEMU | `P0` | Full machine emulation and device models |
| `firecracker` | Firecracker | `P0` | Minimal VMM, KVM, VirtIO, and fast startup |
| `kvm` | KVM | `P0` | Hardware virtualization interface in the Linux kernel |
| `kubernetes` | Kubernetes | `P0` | Declarative resources and reconciliation loops |
| `nomad` | HashiCorp Nomad | `P2` | Workload scheduling and cluster state |

### Networking and network services

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `nginx` | NGINX | `P0` | Event-driven I/O and worker-process architecture |
| `envoy` | Envoy | `P1` | Extensible proxy filters and control/data plane separation |
| `haproxy` | HAProxy | `P1` | Event loop, load balancing, and connection state |
| `caddy` | Caddy | `P2` | Configurable server, automatic TLS, and plugin boundary |
| `curl` | curl | network library | `reviewed` | Compare easy/multi handles, transfer state machines, and connection reuse using fixed-commit evidence |
| `openssl` | OpenSSL | `P0` | Cryptographic primitives, protocol state, and provider boundary |
| `wireguard` | WireGuard | `P1` | Minimal secure tunnel protocol and key state |
| `quiche` | quiche | `P2` | QUIC and HTTP/3 protocol implementation |
| `libp2p` | libp2p | `P2` | Modular peer-to-peer transports and identity |

### Graphics, frontend, and media libraries

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `threejs` | Three.js | `P0` | Scene graph, rendering pipeline, and WebGL abstraction |
| `webgl` | WebGL | `P0` | Browser graphics API and stateful command model |
| `vulkan` | Vulkan | `P1` | Explicit GPU resources, commands, and synchronization |
| `opengl` | OpenGL | `P1` | Stateful graphics pipeline and driver boundary |
| `sdl` | SDL | `P1` | Cross-platform window, input, audio, and device abstraction |
| `godot` | Godot | `P1` | Scene tree, nodes, resources, and game runtime |
| `react` | React | `P1` | Component tree, declarative rendering, and reconciliation |
| `vue` | Vue | `P2` | Reactive state, component graph, and compiler/runtime split |
| `svelte` | Svelte | `P2` | Compile-time UI transformation and reactive updates |
| `d3` | D3.js | `P1` | Data joins, declarative visualization, and DOM composition |
| `ffmpeg` | FFmpeg | `P0` | Codec, filter, demuxer, muxer, and stream pipelines |
| `gstreamer` | GStreamer | `P1` | Typed media elements, pads, and pipeline negotiation |
| `imagemagick` | ImageMagick | `P2` | Image operators and format conversion pipelines |

### Observability, platform, and infrastructure tools

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `prometheus` | Prometheus | `P1` | Time-series collection, labels, and query evaluation |
| `opentelemetry` | OpenTelemetry | `P0` | Portable telemetry data model and propagation |
| `grafana` | Grafana | `P2` | Query-driven dashboards and plugin architecture |
| `terraform` | Terraform | `P1` | Declarative resource graph and provider model |
| `pulumi` | Pulumi | `P2` | General-purpose language plus declarative resource state |
| `supabase` | Supabase | `P0` | Database-centered backend platform composition |
| `openresty` | OpenResty | `P2` | NGINX event core plus programmable request processing |

## Modeling order

The recommended order is:

1. **Foundations:** Unix, C, C++, Linux, SQLite, PostgreSQL, Kafka, QEMU,
   LLVM, and NGINX.
2. **Modern systems:** Rust, Go, Lua, WebAssembly, RocksDB, etcd, Docker,
   Kubernetes, and OpenTelemetry.
3. **Libraries and frameworks:** Three.js, React, Tokio, Tree-sitter, gRPC,
   GStreamer, and related ecosystems.
4. **Comparative expansion:** specialized databases, protocols, graphics
   systems, observability tools, and platform products.

For each target, use the same pipeline:

```text
catalog entry
  → fixed repository revision
  → deterministic observations
  → source/document evidence
  → semantic Architecture Card draft
  → review
  → temporal and typed graph relations
```

## Catalog governance

- Add a catalog entry before starting a new analysis.
- Prefer official repositories and documentation.
- Record a requested ref and resolved commit for every analysis.
- Keep third-party source checkouts out of Git history.
- Keep generated cards under `data/drafts/` until reviewed.
- Separate structural resemblance from historical influence.
- Record the question and assumptions for every mathematical view.
- Record composition inputs, constraints, preserved properties, conflicts, and
  evidence when describing a new architecture.
- Do not infer originality merely because two systems have similar features.

The catalog is deliberately broader than the current implementation. It is a
research backlog and an organizing map; entries become knowledge only after
evidence-backed modeling and review.

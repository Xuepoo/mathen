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
| `nats` | NATS | distributed messaging | `reviewed` | Compare subject routing, JetStream streams, consumer cursors, and replicated storage using fixed-commit evidence |
| `pulsar` | Apache Pulsar | distributed messaging | `reviewed` | Compare stateless brokers, managed ledgers, BookKeeper persistence, and metadata separation using fixed-commit evidence |
| `flink` | Apache Flink | stream processing | `reviewed` | Compare stateful dataflows, event-time watermarks, checkpoints, and JobManager/TaskManager execution using fixed-commit evidence |
| `spark` | Apache Spark | distributed dataflow | `reviewed` | Compare RDD lineage, DAG stages, driver/executor boundaries, and application scheduling using fixed-commit evidence |
| `mysql-server` | MySQL Server | database | `reviewed` | Compare storage-engine, transaction, and recovery boundaries with PostgreSQL and SQLite |
| `rocksdb` | RocksDB | embedded database | `reviewed` | Compare LSM, WAL, compaction, and snapshot boundaries with SQLite and Redis |
| `leveldb` | LevelDB | embedded database | `reviewed` | Compare ordered key-value logs, memtables, leveled compaction, recovery, and snapshots with RocksDB |
| `foundationdb` | FoundationDB | distributed database | `reviewed` | Compare ordered key-value transactions, versioning, layers, and distributed recovery with PostgreSQL and Cassandra |
| `mongodb` | MongoDB | document database | `reviewed` | Compare document collections, storage engines, oplog replication, and shard routing with PostgreSQL and Cassandra |
| `cassandra` | Apache Cassandra | distributed database | `reviewed` | Compare partitioned wide-column storage, replica coordination, commit-log recovery, and tunable consistency with Kafka and FoundationDB |
| `docker` | Docker Engine | container runtime | `reviewed` | Compare daemon, image, runtime, namespace, and filesystem boundaries using fixed-commit evidence |
| `containerd` | containerd | container runtime | `reviewed` | Compare runtime-v2 shims, typed plugins, client boundaries, and content/snapshot lifecycle using fixed-revision evidence |
| `runc` | runc | container runtime | `reviewed` | Compare OCI bundle refinement, Linux isolation primitives, lifecycle state, and checkpoint boundaries using fixed-revision evidence |
| `kata-containers` | Kata Containers | container runtime | `reviewed` | Compare VM-backed sandbox layers, shim/agent/hypervisor composition, and CRI-to-device mapping using fixed-revision evidence |
| `gvisor` | gVisor | container runtime | `reviewed` | Compare Sentry/Gofer mediation, OCI runtime integration, and selectable syscall interception platforms using fixed-revision evidence |
| `qemu` | QEMU | virtualization | `reviewed` | Compare complete machine emulation with Firecracker |
| `kubernetes` | Kubernetes | orchestration | `reviewed` | Analyze reconciliation, API resources, and etcd state |
| `linux` | Linux Kernel | operating system | `reviewed` | Analyze system calls, scheduling, memory, and modules |
| `freebsd` | FreeBSD | operating system | `reviewed` | Compare kernel subsystems, jails, networking, and GEOM storage using fixed-commit evidence |
| `systemd` | systemd | init system | `reviewed` | Compare typed units, dependency transactions, service supervision, and activation using fixed-commit evidence |
| `hadoop` | Apache Hadoop | distributed storage and compute | `reviewed` | Compare HDFS metadata, replicated blocks, YARN arbitration, and batch computation using fixed-commit evidence |
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
| `envoy` | Envoy | network proxy | `reviewed` | Compare worker dispatchers, filter chains, and control/data plane propagation using fixed-commit evidence |
| `haproxy` | HAProxy | network proxy | `reviewed` | Compare polling, task scheduling, layered connection state, and reload topology using fixed-commit evidence |
| `caddy` | Caddy | web server | `reviewed` | Compare module lifecycle, atomic configuration swaps, and automatic HTTPS using fixed-commit evidence |
| `wireguard` | WireGuard | secure tunnel | `reviewed` | Compare Noise handshake state, bounded crypto queues, and replay-window key state using fixed-commit evidence |
| `busybox` | BusyBox | Unix system tools | `reviewed` | Compare multi-call dispatch, configurable applet sets, and shared userland support using fixed-commit evidence |
| `musl` | musl libc | C runtime | `reviewed` | Compare portable interfaces, static/dynamic linking, and thread-local runtime boundaries using fixed-commit evidence |
| `glibc` | GNU C Library | C runtime | `reviewed` | Compare ABI versioning, dynamic loading, and process/thread runtime boundaries using fixed-commit evidence |
| `threejs` | Three.js | 3D graphics library | `reviewed` | Compare scene graph, geometry/material composition, and WebGL renderer boundaries using fixed-commit evidence |
| `blender` | Blender | 3D graphics application | `reviewed` | Compare data-block scenes, dependency graph evaluation, editor boundaries, and render engines using fixed-commit evidence |
| `sdl` | SDL | multimedia library | `reviewed` | Compare window/display, event queue, audio stream, and renderer/GPU boundaries using fixed-commit evidence |
| `godot` | Godot | game engine | `planned` | Add a fixed-commit source bundle and draft before review; no evidence-backed card is present yet |
| `electron` | Electron | desktop application framework | `reviewed` | Compare main/renderer process isolation, IPC, preload capabilities, and utility processes using fixed-commit evidence |
| `tauri` | Tauri | desktop application framework | `reviewed` | Compare native shell/webview composition, command IPC, capabilities, and packaging using fixed-commit evidence |
| `qt` | Qt | desktop application framework | `reviewed` | Compare QObject ownership, event dispatch, signals/slots, widgets, and platform abstraction using fixed-commit evidence |
| `gtk` | GTK | desktop application framework | `reviewed` | Compare GObject types, event controllers, widget trees, and GDK backend boundaries using fixed-commit evidence |
| `rails` | Ruby on Rails | web framework | `reviewed` | Compare engine composition, ordered initialization, autoloading, and Rack middleware using fixed-commit evidence |
| `laravel` | Laravel | web framework | `reviewed` | Compare service-container resolution, provider bootstrap, deferred services, and middleware pipelines using fixed-commit evidence |
| `spring-boot` | Spring Boot | web framework | `reviewed` | Compare application-context startup, conditional auto-configuration, environment binding, and embedded web deployment using fixed-commit evidence |
| `nestjs` | NestJS | web framework | `reviewed` | Compare module graph scanning, provider resolution, initialization phases, and transport adapters using fixed-commit evidence |

The operational manifest now contains 52 repositories. The following entries
were added during the foundational catalog expansion and are ready for bounded
deterministic analysis, but they do not yet have reviewed Architecture Cards:

| ID | Name | Domain | Priority |
| --- | --- | --- | --- |
| `cpython` | CPython | language runtime | `P1` |
| `rust` | Rust | language toolchain | `P1` |
| `go` | Go | language toolchain | `reviewed` | Compare goroutine/channel ordering, package interfaces, and toolchain integration using fixed-commit evidence |
| `ruby` | Ruby | language runtime | `reviewed` | Compare dynamic object dispatch, VM frames, GC, and the C extension boundary using fixed-commit evidence |
| `wasmtime` | Wasmtime | WebAssembly runtime | `P1` |
| `xv6-public` | xv6 | educational operating system | `reviewed` | Compare process scheduling, paging, descriptor I/O, and logged filesystems using fixed-commit evidence |
| `libuv` | libuv | asynchronous I/O library | `reviewed` | Compare event-loop, handle/request, cross-platform, and thread-pool boundaries using fixed-commit evidence |
| `curl` | curl | network library | `reviewed` | Compare easy/multi handles, transfer state machines, and connection reuse using fixed-commit evidence |
| `openssl` | OpenSSL | cryptography library | `reviewed` |
| `protobuf` | Protocol Buffers | serialization protocol | `P1` |
| `grpc` | gRPC | RPC framework | `P1` |
| `mosquitto` | Eclipse Mosquitto | messaging protocol | `reviewed` |
| `mysql-server` | MySQL Server | database | `reviewed` |
| `rocksdb` | RocksDB | embedded database | `reviewed` |
| `threejs` | Three.js | 3D graphics library | `reviewed` | Compare scene graph, geometry/material composition, and WebGL renderer boundaries using fixed-commit evidence |
| `blender` | Blender | 3D graphics application | `reviewed` | Compare data-block scenes, dependency graph evaluation, editor boundaries, and render engines using fixed-commit evidence |
| `sdl` | SDL | multimedia library | `reviewed` | Compare window/display, event queue, audio stream, and renderer/GPU boundaries using fixed-commit evidence |

## Catalog

The following list is the intended expansion order. The IDs are stable Mathen
identifiers, not claims that the projects share the same architecture.

### Foundational operating systems and system software

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `unix` | Unix history and interfaces | `P0` | Process, file, pipe, and permission abstractions |
| `linux` | Linux Kernel | `P0` | Kernel resource model, syscalls, scheduling, and modules |
| `freebsd` | FreeBSD | `reviewed` | Compare kernel subsystems, jails, networking, and GEOM storage using fixed-commit evidence |
| `openbsd` | OpenBSD | `reviewed` | Compare process/thread boundaries, pledge/unveil restrictions, and stateful packet filtering using fixed-commit evidence |
| `plan9` | Plan 9 | `reviewed` | Compare local namespace composition, 9P file services, and selective process resource sharing using fixed-commit evidence |
| `minix` | MINIX 3 | `reviewed` | Compare microkernel IPC, user-mode service isolation, reincarnation recovery, and server-mediated resources using fixed-commit evidence |
| `systemd` | systemd | `reviewed` | Compare typed units, dependency transactions, service supervision, and activation using fixed-commit evidence |
| `busybox` | BusyBox | `reviewed` | Compare multi-call dispatch, configurable applet sets, and shared userland support using fixed-commit evidence |
| `coreutils` | GNU Coreutils | `P2` | Unix command algebra and composable process interfaces |
| `musl` | musl libc | `reviewed` | Compare portable interfaces, static/dynamic linking, and thread-local runtime boundaries using fixed-commit evidence |
| `glibc` | GNU C Library | `reviewed` | Compare ABI versioning, dynamic loading, and process/thread runtime boundaries using fixed-commit evidence |

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
| `zig` | Zig | language toolchain | `reviewed` | Compare explicit allocation, comptime specialization, typed errors, and cross-target tooling using fixed-revision evidence |
| `wasm` | WebAssembly | portable instruction format | `reviewed` | Compare validation, store/module instances, structured execution, and bounded linear memory using fixed-revision evidence |

### Compilers, interpreters, and language infrastructure

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `gcc` | GCC | `P0` | Multi-language frontends, middle-end, and backends |
| `llvm` | LLVM | `P0` | Intermediate representation and optimization passes |
| `clang` | Clang | `P1` | C-family frontend and tooling architecture |
| `rustc` | rustc | compiler infrastructure | `reviewed` | Compare typed IR lowering, MIR ownership analysis, query compilation, and LLVM backend boundaries using fixed-revision evidence |
| `cpython` | CPython | `P1` | Bytecode VM, reference counting, and extension boundary |
| `v8` | V8 | `P1` | JIT compilation, hidden classes, and managed heap |
| `luajit` | LuaJIT | language runtime | `reviewed` | Compare interpreter/tracing-JIT transitions, FFI, and embeddable runtime boundaries using fixed-revision evidence |
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
| `cockroachdb` | CockroachDB | `reviewed` | Compare distributed SQL layering, range replication, leases, and serializable MVCC transactions using fixed-commit evidence |
| `tidb` | TiDB | `reviewed` | Compare stateless SQL compute, PD scheduling and timestamps, key-value mapping, and coprocessor pushdown using fixed-commit evidence |
| `tikv` | TiKV | `reviewed` | Compare Region partitioning, Raft replication, RocksDB persistence, and MVCC transactional APIs using fixed-commit evidence |
| `clickhouse` | ClickHouse | `reviewed` | Compare columnar parts, vectorized execution, and background merges with DuckDB and PostgreSQL using fixed-commit evidence |
| `influxdb` | InfluxDB | `reviewed` | Compare timestamp/tag-set identity, WAL and Parquet persistence, queryable buffers, and retention using fixed-commit evidence |
| `neo4j` | Neo4j | `P2` | Property graph storage and traversal execution |

### Distributed systems, messaging, and coordination

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `kafka` | Apache Kafka | `P0` | Partitioned append-only log and consumer offsets |
| `hadoop` | Apache Hadoop | `reviewed` | Compare HDFS metadata, replicated blocks, YARN arbitration, and batch computation using fixed-commit evidence |
| `zookeeper` | Apache ZooKeeper | `reviewed` | Compare hierarchical coordination state, sessions, watches, and quorum ordering using fixed-commit evidence |
| `etcd` | etcd | `reviewed` | Compare Raft-backed revisions, transactions, watches, and leases using fixed-commit evidence |
| `consul` | Consul | `reviewed` | Compare service catalog, health-aware discovery, datacenter topology, and distributed KV using fixed-commit evidence |
| `rabbitmq` | RabbitMQ | `reviewed` | Compare exchange routing, durable queues, acknowledgements, confirms, and flow control using fixed-commit evidence |
| `nats` | NATS | `P1` | Lightweight messaging, subjects, and stream persistence |
| `pulsar` | Apache Pulsar | `P2` | Segmented logs, brokers, and separated storage |
| `flink` | Apache Flink | `P1` | Stateful stream processing and event-time semantics |
| `spark` | Apache Spark | `P1` | Distributed dataflow, DAG scheduling, and resilient datasets |
| `hadoop` | Apache Hadoop | `P1` | Distributed filesystem and batch resource scheduling |
| `zookeeper` | Apache ZooKeeper | `P0` | Coordination tree, sessions, and consensus-adjacent state |
| `etcd` | etcd | `P0` | Raft-backed consistent key-value store and watch stream |
| `consul` | Consul | `P1` | Service discovery, health state, and distributed KV |
| `rabbitmq` | RabbitMQ | `P1` | Broker queues, routing, acknowledgements, and flow control |
| `nats` | NATS | `reviewed` | Compare subject routing, JetStream streams, consumer cursors, and replicated storage using fixed-commit evidence |
| `pulsar` | Apache Pulsar | `reviewed` | Compare stateless brokers, managed ledgers, BookKeeper persistence, and metadata separation using fixed-commit evidence |
| `flink` | Apache Flink | `reviewed` | Compare stateful dataflows, event-time watermarks, checkpoints, and JobManager/TaskManager execution using fixed-commit evidence |
| `spark` | Apache Spark | `reviewed` | Compare RDD lineage, DAG stages, driver/executor boundaries, and application scheduling using fixed-commit evidence |
| `ray` | Ray | `P2` | Distributed task and actor execution |

### Containers, virtualization, and orchestration

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `docker` | Docker Engine | `reviewed` | Compare daemon, image, runtime, namespace, and filesystem boundaries using fixed-commit evidence |
| `containerd` | containerd | `reviewed` | Compare runtime-v2 shims, typed plugins, client boundaries, and content/snapshot lifecycle using fixed-revision evidence |
| `runc` | runc | `reviewed` | Compare OCI bundle refinement, Linux isolation primitives, lifecycle state, and checkpoint boundaries using fixed-revision evidence |
| `kata-containers` | Kata Containers | `reviewed` | Compare VM-backed sandbox layers, shim/agent/hypervisor composition, and CRI-to-device mapping using fixed-revision evidence |
| `gvisor` | gVisor | `reviewed` | Compare Sentry/Gofer mediation, OCI runtime integration, and selectable syscall interception platforms using fixed-revision evidence |
| `qemu` | QEMU | `P0` | Full machine emulation and device models |
| `firecracker` | Firecracker | `P0` | Minimal VMM, KVM, VirtIO, and fast startup |
| `kvm` | KVM | `P0` | Hardware virtualization interface in the Linux kernel |
| `kubernetes` | Kubernetes | `P0` | Declarative resources and reconciliation loops |
| `nomad` | HashiCorp Nomad | `P2` | Workload scheduling and cluster state |

### Networking and network services

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `nginx` | NGINX | `P0` | Event-driven I/O and worker-process architecture |
| `envoy` | Envoy | `reviewed` | Compare worker dispatchers, filter chains, and control/data plane propagation using fixed-commit evidence |
| `haproxy` | HAProxy | `reviewed` | Compare polling, task scheduling, layered connection state, and reload topology using fixed-commit evidence |
| `caddy` | Caddy | `reviewed` | Compare module lifecycle, atomic configuration swaps, and automatic HTTPS using fixed-commit evidence |
| `curl` | curl | network library | `reviewed` | Compare easy/multi handles, transfer state machines, and connection reuse using fixed-commit evidence |
| `openssl` | OpenSSL | `P0` | Cryptographic primitives, protocol state, and provider boundary |
| `wireguard` | WireGuard | `reviewed` | Compare Noise handshake state, bounded crypto queues, and replay-window key state using fixed-commit evidence |
| `quiche` | quiche | `P2` | QUIC and HTTP/3 protocol implementation |
| `libp2p` | libp2p | `P2` | Modular peer-to-peer transports and identity |

### Graphics, frontend, and media libraries

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `threejs` | Three.js | `reviewed` | Compare scene graph, geometry/material composition, and WebGL renderer boundaries using fixed-commit evidence |
| `blender` | Blender | `reviewed` | Compare data-block scenes, dependency graph evaluation, editor boundaries, and render engines using fixed-commit evidence |
| `webgl` | WebGL | `reviewed` | Compare browser context state, typed GPU resources, shader submission, and security boundaries using fixed-commit evidence |
| `vulkan` | Vulkan | `reviewed` | Compare explicit resources, command recording/submission, queue ownership, and synchronization using fixed-commit evidence |
| `opengl` | OpenGL | `reviewed` | Compare context state, object bindings, programmable pipeline, and platform integration using fixed-commit evidence |
| `sdl` | SDL | `reviewed` | Compare window/display, event queue, audio stream, and renderer/GPU boundaries using fixed-commit evidence |
| `godot` | Godot | `P1` | Scene tree, nodes, resources, and game runtime |
| `react` | React | `reviewed` | Compare component trees, hooks, reconciliation, and host commit boundaries using fixed-commit evidence |
| `vue` | Vue | `reviewed` | Compare proxy/ref reactivity, component effects, compiler-informed rendering, and host patching using fixed-commit evidence |
| `svelte` | Svelte | `reviewed` | Compare component-file compilation, generated DOM updates, and reactive dependency analysis using fixed-commit evidence |
| `d3` | D3.js | `P1` | Data joins, declarative visualization, and DOM composition |
| `ffmpeg` | FFmpeg | `P0` | Codec, filter, demuxer, muxer, and stream pipelines |
| `gstreamer` | GStreamer | `reviewed` | Compare typed media elements, pad links, caps negotiation, bins, and pipeline state using fixed-commit evidence |
| `imagemagick` | ImageMagick | `reviewed` | Compare image state, ordered operators, coder dispatch, and format conversion pipelines using fixed-commit evidence |

### Observability, platform, and infrastructure tools

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `prometheus` | Prometheus | `reviewed` | Compare labeled time series, pull collection, and temporal query evaluation with OpenTelemetry using fixed-commit evidence |
| `opentelemetry` | OpenTelemetry | `reviewed` | Compare signal data models, context propagation, and exporter boundaries with Prometheus using fixed-commit evidence |
| `grafana` | Grafana | `P2` | Query-driven dashboards and plugin architecture |
| `terraform` | Terraform | `reviewed` | Compare declarative resource graphs, provider boundaries, and plan/state lifecycle with Kubernetes using fixed-commit evidence |
| `pulumi` | Pulumi | `P2` | General-purpose language plus declarative resource state |
| `supabase` | Supabase | `P0` | Database-centered backend platform composition |
| `openresty` | OpenResty | `P2` | NGINX event core plus programmable request processing |

### Web applications and full-stack frameworks

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `react` | React | `reviewed` | Compare component trees, hooks, reconciliation, and host commit boundaries using fixed-commit evidence |
| `vue` | Vue | `reviewed` | Compare proxy/ref reactivity, component effects, compiler-informed rendering, and host patching using fixed-commit evidence |
| `svelte` | Svelte | `reviewed` | Compare component-file compilation, generated DOM updates, and reactive dependency analysis using fixed-commit evidence |
| `angular` | Angular | `reviewed` | Compare compiled templates, hierarchical dependency injection, change detection, and signals using fixed-commit evidence |
| `nextjs` | Next.js | `reviewed` | Compare server/client component boundaries, filesystem routing, route handlers, caching, and deployment artifacts using fixed-commit evidence |
| `express` | Express | `reviewed` | Compare ordered middleware, router dispatch, Node HTTP adapters, mounted applications, and view boundaries using fixed-commit evidence |
| `fastapi` | FastAPI | `reviewed` | Compare typed path operations, dependency DAGs, validation boundaries, and OpenAPI projection using fixed-commit evidence |
| `django` | Django | `reviewed` | Compare application registry, URL resolution, adaptive middleware, ORM model metadata, and template response boundaries using fixed-commit evidence |
| `rails` | Ruby on Rails | `reviewed` | Engine composition, ordered initialization, autoloading, routing, and middleware |
| `laravel` | Laravel | `reviewed` | Service container, provider bootstrap, deferred resolution, routing, and middleware pipeline |
| `spring-boot` | Spring Boot | `reviewed` | Application-context lifecycle, conditional auto-configuration, environment binding, and embedded web deployment |
| `nestjs` | NestJS | `reviewed` | Module graph scanning, provider resolution, initialization lifecycle, and transport adapters |

### Desktop and cross-platform application frameworks

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `electron` | Electron | `reviewed` | Compare main/renderer process isolation, IPC, preload capabilities, and utility processes using fixed-commit evidence |
| `tauri` | Tauri | `reviewed` | Compare native shell/webview composition, command IPC, capabilities, and packaging using fixed-commit evidence |
| `qt` | Qt | `reviewed` | Compare QObject ownership, event dispatch, signals/slots, widgets, and platform abstraction using fixed-commit evidence |
| `gtk` | GTK | `reviewed` | Compare GObject types, event controllers, widget trees, and GDK backend boundaries using fixed-commit evidence |
| `wxwidgets` | wxWidgets | `reviewed` | Compare native widget adapter refinement, typed event routing, and application loop lifecycle using fixed-commit evidence |
| `javafx` | JavaFX | `reviewed` | Compare constrained scene graphs, observable property dependencies, and pulse-driven rendering using fixed-commit evidence |
| `flutter` | Flutter | `reviewed` | Compare immutable widget reconciliation, render-object pipelines, and engine/embedder boundaries using fixed-commit evidence |
| `wails` | Wails | `reviewed` | Compare Go/webview shells, generated typed bindings, runtime events, and native window bridges using fixed-commit evidence |

### CLI and developer tools

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `neovim` | Neovim | `P1` | Event-driven editor state, MessagePack-RPC channels, embedded Lua, and plugin boundaries |
| `vscode` | Visual Studio Code | `P1` | Layered workbench services, extension-host IPC, target environments, and contributions |
| `ripgrep` | ripgrep | `P1` | Ignore-aware parallel traversal, regex/search stages, adaptive I/O, and result streams |
| `fd` | fd | `P2` | Ignore-aware walking, path/metadata predicates, parallel jobs, and output coordination |
| `jq` | jq | `P1` | JSON value algebra, filter composition, streaming execution, and CLI protocols |
| `yq` | yq | `P2` | Multi-format tree transformations, expression evaluation, and stream processing |
| `just` | Just | `P2` | Declarative recipe graph, shell execution, parameter binding, and environment propagation |
| `bazel` | Bazel | `P1` | Hermetic action graph, sandboxed execution, caching, and incremental builds |

### Cloud-native and platform infrastructure

| ID | Target | Priority | Modeling focus |
| --- | --- | --- | --- |
| `helm` | Helm | `reviewed` | Chart composition, values rendering, release state, and Kubernetes integration using fixed-commit evidence |
| `argo-cd` | Argo CD | `reviewed` | Desired/observed state reconciliation, GitOps sync, health assessment, and rollback using fixed-commit evidence |
| `istio` | Istio | `reviewed` | Sidecar proxy mesh, traffic policy, control/data plane, and telemetry propagation using fixed-commit evidence |
| `cilium` | Cilium | `reviewed` | eBPF datapath, identity policy, service routing, and observability using fixed-commit evidence |
| `traefik` | Traefik | `P2` | Dynamic provider configuration, routers, middleware chains, and certificates |
| `crossplane` | Crossplane | `P2` | Kubernetes-native composition, provider controllers, and managed resource reconciliation |

### Identity, API, workflow, and application services

| ID | Target | Priority | Modeling focus |
| --- | --- | --- |
| `keycloak` | Keycloak | `P1` | Realm/tenant boundaries, identity flows, token issuance, and adapters |
| `kong` | Kong Gateway | `P1` | Plugin pipeline, route/service abstraction, control/data plane, and credentials |
| `apisix` | Apache APISIX | `reviewed` | Compare dynamic routing, phase-aware plugins, etcd-backed configuration, and upstream proxy boundaries using fixed-commit evidence |
| `temporal` | Temporal | `reviewed` | Compare durable event histories, task queues, deterministic replay, and activity retry boundaries using fixed-commit evidence |
| `airflow` | Apache Airflow | `reviewed` | Compare DAG readiness, metadata-mediated scheduling, pluggable executors, and separated DAG processing using fixed-commit evidence |
| `celery` | Celery | `reviewed` | Compare broker-mediated task delivery, acknowledgement/redelivery, result backends, and message-composed workflows using fixed-commit evidence |
| `oauth2-proxy` | OAuth2 Proxy | `reviewed` | Compare middleware-chain authentication, provider adapters, encrypted cookie/Redis sessions, and upstream forwarding using fixed-commit evidence |
| `authentik` | authentik | `reviewed` | Compare staged flow planning, policy aggregation, provider/application boundaries, and managed outpost reconciliation using fixed-commit evidence |

### Machine learning and computer vision

| ID | Target | Priority | Modeling focus |
| --- | --- | --- |
| `pytorch` | PyTorch | `P1` | Tensor/autograd graphs, eager execution, dispatch, and accelerator backends |
| `tensorflow` | TensorFlow | `P1` | Tensor graphs, runtime devices, saved models, and distributed execution |
| `jax` | JAX | `P2` | Functional transformations, tracing, XLA compilation, and sharding |
| `scikit-learn` | scikit-learn | `P1` | Estimator protocols, pipelines, transformers, and model selection |
| `opencv` | OpenCV | `P1` | Matrix/image data model, algorithm modules, backends, and streaming pipelines |
| `transformers` | Hugging Face Transformers | `P1` | Model/config/tokenizer boundaries, generation loops, and weight loading |
| `mlflow` | MLflow | `P2` | Run/artifact provenance, flavor-aware model packaging, registry versions, aliases, and lifecycle |
| `ray` | Ray | `P2` | Distributed task and actor execution |

### Storage, data platforms, and infrastructure services

| ID | Target | Priority | Modeling focus |
| --- | --- | --- |
| `dbt` | dbt Core | `P1` | Declarative resource DAGs, ref ordering, adapter execution, materialization strategies, and tests |
| `dagster` | Dagster | `P1` | Software-defined asset dependencies, schedules, sensors, daemon coordination, and run state |
| `minio` | MinIO | `P1` | S3 object namespace, erasure-coded fragment layout, quorum, and background healing |
| `seaweedfs` | SeaweedFS | `reviewed` | Compare volume/filer/master separation, direct volume routing, topology-aware replication, and object APIs using fixed-commit evidence |
| `vault` | HashiCorp Vault | `reviewed` | Compare barrier-protected storage, mounted backend authorization, seal state, and leased credential lifecycle using fixed-commit evidence |
| `openbao` | OpenBao | `reviewed` | Compare barrier encryption, policy-authorized engine routing, seal state, and lease-based revocation using fixed-commit evidence |
| `clickhouse-operator` | ClickHouse Operator | `reviewed` | Compare custom-resource desired state, hierarchical reconciliation, StatefulSet identity, and database lifecycle using fixed-commit evidence |
| `velero` | Velero | `reviewed` | Compare Kubernetes resource backup, object-storage archives, restore ordering, and plugin boundaries using fixed-commit evidence |

### Frontend, mobile, build, and testing ecosystems

| ID | Target | Priority | Modeling focus |
| --- | --- | --- |
| `react-native` | React Native | `reviewed` | Compare JavaScript/native representation, render-commit-mount stages, layout, threading, and platform renderers using fixed-commit evidence |
| `expo` | Expo | `reviewed` | Compare native modules, config-plugin generation, OTA compatibility, and native build boundaries using fixed-commit evidence |
| `capacitor` | Capacitor | `reviewed` | Compare web/native bridge, plugin lifecycle, asset synchronization, and platform capability access using fixed-commit evidence |
| `ionic` | Ionic | `reviewed` | Compare web component primitives, framework adapters, navigation lifecycle, and platform capability boundaries using fixed-commit evidence |
| `vite` | Vite | `reviewed` | Compare environment module graphs, on-demand transforms, HMR, dependency pre-bundling, and production output using fixed-commit evidence |
| `webpack` | webpack | `reviewed` | Compare compiler phases, module/chunk graphs, loader and plugin hooks, and cache/emission boundaries using fixed-commit evidence |
| `rollup` | Rollup | `reviewed` | Compare plugin-driven module graphs, tree-shaking, chunk generation, and multi-host package boundaries using fixed-commit evidence |
| `esbuild` | esbuild | `reviewed` | Compare parallel parsing, incremental module graphs, linking, bundling, and transform boundaries using fixed-commit evidence |
| `playwright` | Playwright | `reviewed` | Compare browser/context isolation, page protocol control, fixture scopes, and tracing using fixed-commit evidence |
| `storybook` | Storybook | `reviewed` | Compare story indexing, manager/preview isolation, addon channels, and component test workflows using fixed-commit evidence |

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

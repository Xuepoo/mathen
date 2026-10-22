# Reviewed-card relation graph report

## Scope and method

This report evaluates the 154 reviewed Architecture Cards under `data/systems/`. It distinguishes evidence-backed typed relations from legacy navigation metadata and refuses to add generic similarity edges solely to remove isolated nodes. Draft cards remain outside the public reviewed graph.

The relation vocabulary is the card contract: `uses`, `extends`, `composes`, `resembles`, and `influenced-by`. Claim type and review status are independent. `fact` describes documented implementation or product integration; `analogy` describes structural comparison; every current typed relation remains `proposed` until a deliberate review accepts it.

Source-card relation evidence must use IDs defined in the source card. Target evidence is review context only. No current relation claims historical influence or formal equivalence.

## Reviewed-card inventory

The reviewed inventory contains **154 systems**, **553 features**, and **416 mathematical views**:

`airflow`, `angular`, `apisix`, `argo-cd`, `authentik`, `bazel`, `blender`, `boost`
`busybox`, `caddy`, `capacitor`, `cassandra`, `celery`, `cilium`, `clickhouse`, `clickhouse-operator`
`cockroachdb`, `consul`, `containerd`, `coreutils`, `cpython`, `crossplane`, `curl`, `dagster`
`dbt`, `deno`, `django`, `docker`, `duckdb`, `elasticsearch`, `electron`, `envoy`
`esbuild`, `etcd`, `expo`, `express`, `fastapi`, `fd`, `ffmpeg`, `firecracker`
`flink`, `flutter`, `foundationdb`, `freebsd`, `gcc`, `git`, `glibc`, `go`
`grpc`, `gstreamer`, `gtk`, `gvisor`, `hadoop`, `haproxy`, `helm`, `imagemagick`
`influxdb`, `ionic`, `istio`, `javafx`, `jax`, `jq`, `just`, `kafka`
`kata-containers`, `keycloak`, `kong`, `kubernetes`, `laravel`, `leveldb`, `libuv`, `linux`
`llvm`, `lua`, `luajit`, `minio`, `minix`, `mlflow`, `mongodb`, `mosquitto`
`musl`, `mysql-server`, `nats`, `neovim`, `nestjs`, `nextjs`, `nginx`, `node`
`oauth2-proxy`, `openbao`, `openbsd`, `opencv`, `opengl`, `openssl`, `opentelemetry`, `plan9`
`playwright`, `postgresql`, `prometheus`, `protobuf`, `pulsar`, `pytorch`, `qemu`, `qt`
`rabbitmq`, `rails`, `react`, `react-native`, `redis`, `ripgrep`, `rocksdb`, `rollup`
`ruby`, `runc`, `rust`, `rustc`, `scikit-learn`, `sdl`, `seaweedfs`, `spark`
`spring-boot`, `sqlite`, `storybook`, `supabase`, `svelte`, `systemd`, `tauri`, `temporal`
`tensorflow`, `terraform`, `threejs`, `tidb`, `tikv`, `traefik`, `transformers`, `tree-sitter`
`v8`, `vault`, `velero`, `vite`, `vscode`, `vue`, `vulkan`, `wails`
`wasm`, `wasmtime`, `webgl`, `webpack`, `wireguard`, `wxwidgets`, `xv6-public`, `yq`
`zig`, `zookeeper`

All reviewed cards pass semantic validation, retain fixed source provenance, local evidence IDs, bounded features, mathematical views with questions and assumptions, and explicit trade-offs. The expansion preserved the separate draft corpus; no draft is promoted automatically by the graph API.

## Current typed relations

There are **4 directed typed relations**:

| Source | Type | Target | Claim type | Status | Source evidence IDs | Boundary |
| --- | --- | --- | --- | --- | --- | --- |
| `duckdb` | `resembles` | `postgresql` | `analogy` | `proposed` | `duckdb-why` | Both are relational query engines, while DuckDB is embedded/analytical and PostgreSQL is client/server/extensible. |
| `sqlite` | `resembles` | `duckdb` | `analogy` | `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | Embedded database execution is structurally comparable, but workload, storage, and execution models differ. |
| `sqlite` | `resembles` | `postgresql` | `analogy` | `proposed` | `sqlite-appropriate-uses`, `sqlite-architecture` | Both expose relational query execution, but SQLite is embedded/local while PostgreSQL is client/server and extensible. |
| `supabase` | `composes` | `postgresql` | `fact` | `proposed` | `supabase-architecture` | Supabase documents PostgreSQL as the core around which API, auth, realtime, storage, and management services are assembled. |

Typed connectivity is intentionally sparse. Adding 150+ systems did not create evidence for relations merely because systems share words such as “pipeline”, “runtime”, “graph”, “storage”, or “controller”.

## Connectivity summary

- Typed relations: **4 directed edges**; **151 undirected components**, sizes `[4, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`. The only non-singleton typed component is `duckdb, postgresql, sqlite, supabase`.
- Legacy `related_systems`: **228 valid directed edges**.
- Combined graph: **232 directed edges** and **190 unique undirected edges**; **48 components**, sizes `[104, 3, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]`.

The largest combined component contains:

`airflow`, `boost`, `busybox`, `capacitor`, `clickhouse`, `cockroachdb`, `consul`, `containerd`, `coreutils`, `cpython`, `curl`, `dagster`, `dbt`, `deno`, `django`, `docker`, `duckdb`, `elasticsearch`, `electron`, `esbuild`, `etcd`, `expo`, `express`, `fastapi`, `fd`, `ffmpeg`, `firecracker`, `freebsd`, `gcc`, `git`, `glibc`, `go`, `grpc`, `gstreamer`, `gvisor`, `hadoop`, `influxdb`, `jax`, `kafka`, `kata-containers`, `kubernetes`, `laravel`, `libuv`, `linux`, `llvm`, `lua`, `luajit`, `minix`, `mlflow`, `mosquitto`, `musl`, `mysql-server`, `neovim`, `nestjs`, `nextjs`, `nginx`, `node`, `openbsd`, `opencv`, `openssl`, `opentelemetry`, `plan9`, `playwright`, `postgresql`, `prometheus`, `protobuf`, `pytorch`, `qemu`, `rabbitmq`, `rails`, `react`, `react-native`, `redis`, `ripgrep`, `rocksdb`, `rollup`, `ruby`, `runc`, `rust`, `rustc`, `scikit-learn`, `sdl`, `spring-boot`, `sqlite`, `storybook`, `supabase`, `systemd`, `temporal`, `tensorflow`, `terraform`, `threejs`, `tidb`, `tikv`, `transformers`, `tree-sitter`, `v8`, `velero`, `vite`, `vscode`, `wasm`, `wasmtime`, `xv6-public`, `zig`, `zookeeper`

Other non-singleton combined components:

- `opengl, vulkan, webgl`
- `minio, seaweedfs`

There are **45 combined isolated nodes**. Isolation is an evidence-backed graph result, not a defect to repair with unsupported relations. The legacy graph is navigation context and must not be presented as typed semantic evidence.

## Review-ready bridge candidates

The following candidates remain review backlog items; they are not canonical graph updates:

| Candidate | Claim boundary |
| --- | --- |
| `grpc` → `uses` → `protobuf` | Strongest direct dependency candidate. Review gRPC source-local evidence for generated service/message descriptors; do not reverse the dependency or claim every deployment uses Protobuf. |
| `firecracker` → `resembles` → `qemu` | Virtualization comparison candidate: narrowed Firecracker machine model versus QEMU’s broad device/emulation model; no reuse, equivalence, or historical influence. |
| `rust` → `resembles` → `llvm` | Conservative analogy only. Naming LLVM IR does not prove a dependency on the LLVM project. |
| `redis`/`kafka`/`sqlite` storage analogies | Keep as hypotheses until source-local evidence and boundaries are reviewed; shared append, replay, snapshot, or durability vocabulary is insufficient. |

No current reviewed pair supports `extends` or `influenced-by`. Relations to unreviewed targets such as etcd, KVM, Lucene, or other draft systems are not emitted. `FFmpeg` and other isolated nodes remain isolated when no source-supported bridge is available.

## Composition and review boundary

`data/drafts/sqlite-duckdb-analytical-workflow.json` remains a draft composition proposal. It records a possible SQLite write authority plus DuckDB derived-snapshot workflow with staleness and shared-resource conflicts; it does not prove an implementation connector or justify a canonical relation.

Candidate relation payloads must use source-local evidence IDs, retain `claim_status: proposed`, and preserve the distinction between fact, inference, hypothesis, and analogy. Review reports are inputs to a future card edit, not canonical relations by themselves.

## Conclusions

1. The reviewed graph now contains 154 nodes, 4 typed relations, and 228 valid legacy navigation edges.
2. Typed connectivity remains intentionally sparse: one four-node database component and singleton systems elsewhere.
3. Legacy metadata creates a larger navigational graph, but its edges carry no typed claim or evidence metadata.
4. Review `grpc uses protobuf` first, followed by `firecracker resembles qemu`, while retaining conservative boundaries for all analogies.
5. Do not add edges solely to make the graph connected. More evidence-backed relations are preferable to dense unsupported similarity links.

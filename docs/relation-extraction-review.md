## MTH-0061 isolated-system review (2026-10-23)

This pass reviewed all 45 nodes that were isolated in the combined graph at the
start of the task. The review used the primary source URLs already recorded in
each card and added only relations whose source-card evidence documents a
concrete dependency, composition boundary, or narrowly stated structural
comparison. Every added relation is `proposed`; relation evidence IDs are local
to the source card. No relation was added to `temporal.json`, and no draft or
catalog file was changed.

### Added relations

The pass added 29 typed relations in 21 reviewed cards:

- Direct/runtime or platform boundaries: `argo-cd → kubernetes`,
  `argo-cd → helm` (supported manifest source), `helm → kubernetes`,
  `istio → envoy`, `istio → kubernetes`, `cilium → linux`,
  `cilium → kubernetes`, `apisix → nginx` (OpenResty/NGINX boundary),
  `kong → nginx` (OpenResty/NGINX boundary), `tauri → rust`,
  `wails → go`, `grpc → protobuf`, `clickhouse-operator → kubernetes`,
  `clickhouse-operator → clickhouse`, `crossplane → kubernetes`, and
  `spark → kubernetes`.
- Explicit framework composition: `ionic → angular`, `ionic → react`, and
  `ionic → vue`, based on Ionic's published framework integration packages.
- Bounded structural comparisons: `firecracker → qemu`, `yq → jq`,
  `spark → flink`, `angular → vue`, `angular → svelte`, `vue → svelte`,
  `openbao → vault`, and `keycloak → authentik`. These use `resembles` with
  `claim_type: analogy`; none asserts implementation reuse, equivalence, or
  historical influence.

Important scope boundaries include: APISIX and Kong relations target the
reviewed NGINX card while naming their OpenResty/NGINX variant; Cilium's Linux
relation is to the kernel eBPF boundary; Tauri's Rust relation is to its native
backend; gRPC's Protobuf relation is the documented default rather than a claim
about every deployment; and Argo CD's Helm relation is a supported source
rather than a universal application dependency.

### Deferred isolates

The remaining 20 reviewed isolates were inspected and left unchanged because
the card-local primary evidence did not establish a safe relation to another
reviewed target without broadening the claim beyond the source: `bazel`, `blender`,
`cassandra`, `celery`, `flutter`, `foundationdb`, `gtk`, `haproxy`, `imagemagick`,
`javafx`, `just`, `leveldb`, `mongodb`, `nats`, `oauth2-proxy`, `pulsar`, `qt`,
`traefik`, `webpack`, and `wxwidgets`. Caddy and WireGuard were connected to the
reviewed Go card by explicit implementation-language evidence. In particular, Flutter's
engine boundary does not justify a V8 edge, generic UI/event-loop resemblance
was not emitted for GTK/Qt/JavaFX/wxWidgets, and Spark/Flink was limited to a
specific dataflow analogy; the graph counts below are authoritative.

### Graph effect

Before this pass the reviewed graph had 154 nodes, 4 typed relations, 228
valid legacy `related_systems` edges, and 45 combined isolates. After the card
edits it has 154 nodes, 33 typed relations, 228 valid legacy edges, 261 total
directed edges, and 20 combined isolates (the legacy edge set was unchanged).
The typed relation component count and isolate count should be regenerated from cards
during review rather than inferred from this prose if later edits land.

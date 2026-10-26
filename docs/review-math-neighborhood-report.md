# Mathematical-neighborhood review of reviewed cards

## Scope and method

This is an audit of the reviewed snapshot at `fb40053` (`feat(data): expand
reviewed architecture graph to 154 systems`), not a current inventory. The
checked-in canonical tree now contains 219 cards and 608 mathematical views;
the counts below remain reproducible only for that historical snapshot. The
unit of reference below is a
deterministic view ID of the form `<card-id>#mv-<1-based position>`; these IDs
are report-local navigation identifiers, since the card schema does not assign
an ID field to a mathematical view.

I inspected every `data/systems/*.json` card, ran `uv run mathen validate`, and
computed the counts from the JSON files (there is no `scripts/metrics` or
equivalent metrics script in this snapshot). The check covered the four required
view fields (`model`, `question`, `assumptions`, `evidence_ids`), claim type,
and source-local evidence resolution. Family labels below are deliberately
conservative: a family means that the views can be navigated together because
they ask related structural questions. It does **not** mean the systems use the
same implementation, satisfy the same laws, are historically related, or are
equivalent/provably composable.

## Executive result

- **154/154 cards and 416/416 views validate** under the repository validator.
- **416/416 views have non-empty model, question, assumptions, and evidence
  references; 416/416 evidence reference sets resolve within the same card.**
- Claim labels are **305 `inference` (73.3%)**, **109 `hypothesis` (26.2%)**,
  and **2 `analogy` (0.5%)**; no view is labeled `fact`. This is directionally
  appropriate for mathematical abstractions, but does not itself establish
  model soundness.
- **373 views have three assumptions, 34 have two, eight have four, and one has
  one.** The one-assumption view is `duckdb#mv-2` (`Batched dataflow
transformation`) and is under-specified relative to the otherwise strong
  convention.
- Evidence cardinality is uneven: **39 views cite one evidence item, 257 cite
  two, 114 cite three, and six cite four**. One source can be valid but is a
  weak basis for a cross-cutting or quantitative claim; the one-evidence cases
  should be prioritized for review.

The current dataset is therefore structurally healthy and unusually consistent,
but its shared mathematical neighborhoods are inferred by model/question text,
not represented as a first-class, evidence-backed relation. The report
recommends using the families below for search and comparison only.

## Explicit navigation families

### 1. Dependency, causality, ownership, and routing graphs

**Use when:** the question is about entities as vertices and dependency,
causality, ownership, containment, routing, or capability edges. Typical
models include DAGs, directed graphs, trees, forests, tries, bipartite graphs,
and typed relations.

**Representative views:**

- `git#mv-1` (content-addressed graph) and `git#mv-2` (commit DAG) separate
  immutable-content identity from ancestry.
- `bazel#mv-1`, `dbt#mv-1`, `dagster#mv-1`, `spark#mv-1`, and `vulkan#mv-1`
  are dependency/execution-order neighborhoods; they should not be collapsed
  into one “DAG semantics” because their vertices and readiness rules differ.
- `rabbitmq#mv-1`, `nats#mv-1`, `mosquitto#mv-1`, `express#mv-2`,
  `kong#mv-1`, and `traefik#mv-1` are routing/dispatch neighborhoods.
- `react#mv-1`, `threejs#mv-1`, `blender#mv-1`, `gtk#mv-1`, `qemu#mv-2`,
  and `tree-sitter#mv-2` are hierarchical object/tree neighborhoods, with
  materially different identity, ownership, transform, or syntax semantics.
- `cilium#mv-2`, `openbsd#mv-2`, `vault#mv-2`, `deno#mv-2`, and
  `capacitor#mv-1` are capability/policy or boundary graphs.

**Conservative boundary:** a shared “graph” label says only that graph
notation is a useful index. It does not say two graphs are isomorphic, that an
edge has the same meaning, or that a topological order exists. In particular,
`git#mv-2` is a DAG by construction, while a runtime ownership graph or policy
graph may be cyclic, dynamic, or partially ordered.

### 2. State machines and labeled transition systems

**Use when:** the question asks how explicit states change under commands,
events, failures, retries, scheduling, lifecycle operations, or protocol
steps. This is the largest recurring model family.

**Representative views:**

- Workflow/task execution: `airflow#mv-2`, `celery#mv-1`, `temporal#mv-1`,
  `temporal#mv-2`, and `rabbitmq#mv-2`.
- Storage and transaction state: `sqlite#mv-2`, `rocksdb#mv-2`,
  `redis#mv-4`, `postgresql#mv-2`, `mysql-server#mv-2`, and
  `foundationdb#mv-1`.
- Runtime/protocol lifecycle: `containerd#mv-2`, `runc#mv-2`,
  `wasm#mv-2`, `openssl#mv-2`, `wireguard#mv-1`, and `plan9#mv-2`.
- UI/event lifecycle: `react#mv-2`, `react#mv-3`, `vue#mv-2`, `gtk#mv-2`,
  `qt#mv-2`, `sdl#mv-1`, and `wxwidgets#mv-2`.
- Control/reconciliation: `argo-cd#mv-3`, `kubernetes#mv-3`,
  `terraform#mv-2`, `authentik#mv-3`, and `clickhouse-operator#mv-2`.

**Conservative boundary:** “transition system” is a modeling vocabulary, not
an assertion that the implementation is finite-state, deterministic, complete,
or formally verified. `kubernetes#mv-3` explicitly leaves non-convergence
possible; that is not equivalent to `etcd#mv-1`'s committed revision history or
to `react#mv-2`'s render/commit phase boundary.

### 3. Typed data, schema, and interface relations

**Use when:** the question concerns typed objects, records, schemas, API
contracts, keyspaces, descriptors, tensor views, or compatibility of values
and interfaces.

**Representative views:**

- Data/query structure: `duckdb#mv-1`, `clickhouse#mv-1`, `sqlite#mv-1`,
  `prometheus#mv-1`, `influxdb#mv-1`, and `redis#mv-1`.
- Interface/schema boundaries: `grpc#mv-1`, `fastapi#mv-1`, `protobuf#mv-1`,
  `protobuf#mv-3`, `go#mv-3`, `wasm#mv-1`, and `transformers#mv-1`.
- Array/tensor representations: `opencv#mv-1`, `opencv#mv-2`, `jax#mv-4`,
  and `pytorch#mv-1`.
- Typed composition and containment: `containerd#mv-1`, `caddy#mv-1`,
  `nestjs#mv-1`, `rails#mv-2`, and `systemd#mv-1`.

**Conservative boundary:** “typed” does not imply one common type theory or
that the relation is total. `wasm#mv-1` is a specification validation
judgment; `grpc#mv-1` is a service contract graph; and `opencv#mv-2` is an
interface/dispatch abstraction. They are navigational neighbors, not proofs
of substitutability.

### 4. Pipelines, composition, and transducers

**Use when:** the question concerns ordered operators, middleware, filters,
serialization/compilation passes, stream transformations, or functions that
map one representation to another.

**Representative views:**

- Request/filter pipelines: `apisix#mv-2`, `envoy#mv-2`, `express#mv-1`,
  `kong#mv-2`, `laravel#mv-3`, and `traefik#mv-2`.
- Data/query/media pipelines: `duckdb#mv-1`, `dbt#mv-2`, `ffmpeg#mv-1`,
  `gstreamer#mv-2`, `imagemagick#mv-1`, `jq#mv-1`, and `ripgrep#mv-1`.
- Compilation/transformation: `esbuild#mv-2`, `llvm#mv-2`, `jax#mv-1`,
  `svelte#mv-1`, `vite#mv-3`, `wasmtime#mv-2`, and `webpack#mv-3`.

**Conservative boundary:** pipeline membership does not imply commutativity,
associativity, idempotence, or even totality. `apisix#mv-2` explicitly says
arbitrary plugins need not commute; similar assumptions should be retained for
all pipeline comparisons. The word “algebra” in `jq#mv-2`, `jax#mv-1`, or
`webpack#mv-3` should be read as a candidate composition vocabulary unless the
operations and laws are stated.

### 5. Refinement, representation, compatibility, and abstraction boundaries

**Use when:** the question compares a higher-level contract with a lower-level
representation, implementation, backend, serialization, ABI, runtime, or
storage layer.

**Representative views:**

- Storage/representation: `cassandra#mv-1`, `leveldb#mv-1`, `rocksdb#mv-1`,
  `redis#mv-3`, `mongodb#mv-1`, `mysql-server#mv-1`, `tidb#mv-1`, and
  `sqlite#mv-3`.
- Runtime/platform isolation: `docker#mv-2`, `firecracker#mv-1`,
  `gvisor#mv-3`, `kata-containers#mv-1`, `runc#mv-1`, and `wasm#mv-3`.
- Compiler/API/backend substitution: `rust#mv-1`, `rustc#mv-1`,
  `gcc#mv-1`, `glibc#mv-1`, `pytorch#mv-3`, `gtk#mv-3`, `qt#mv-3`,
  `wxwidgets#mv-1`, `tauri#mv-3`, and `electron#mv-2`.
- Durable-history/refinement comparisons: `kafka#mv-3`, `kafka#mv-6`,
  `temporal#mv-3`, `tensorflow#mv-3`, and `protobuf#mv-2`.

**Conservative boundary:** “refinement” must identify the observation boundary
and preserved properties. A representation refinement is not implementation
equivalence, performance equality, or a proof that a concrete backend is
interchangeable. `docker#mv-3` and `redis#mv-3` are useful neighbors because
both compare visible state to durable/physical representation, but their
contracts and failure boundaries are different.

### 6. Replication, logs, visibility, convergence, and recovery

**Use when:** the question concerns append histories, replica coordination,
acknowledgements, snapshots, MVCC visibility, replay, checkpoints, recovery,
or desired/observed convergence.

**Representative views:**

- Append/replay logs: `kafka#mv-1` through `kafka#mv-6`, `pulsar#mv-2`,
  `redis#mv-2`, `temporal#mv-1`, and `xv6-public#mv-3`.
- Snapshot/MVCC visibility: `postgresql#mv-2`, `postgresql#mv-5`,
  `mysql-server#mv-3`, `rocksdb#mv-3`, `leveldb#mv-2`, and
  `sqlite#mv-4`.
- Replication and recovery: `cassandra#mv-2`, `cassandra#mv-3`,
  `elasticsearch#mv-2`, `foundationdb#mv-3`, `hadoop#mv-1`,
  `mongodb#mv-2`, `tikv#mv-2`, and `zookeeper#mv-1`.
- Reconciliation/convergence: `apisix#mv-3`, `argo-cd#mv-1`,
  `authentik#mv-3`, `envoy#mv-3`, `istio#mv-1`, `kubernetes#mv-1`,
  `kubernetes#mv-3`, and `terraform#mv-2`.

**Conservative boundary:** a replicated log, an MVCC visibility relation, and a
control-loop convergence model are adjacent neighborhoods, not one model.
“Eventually convergent” is a hypothesis with explicit health and delivery
assumptions; it is not a guarantee that all replicas, controllers, or external
effects converge. `kafka#mv-4` deliberately limits ordering to equal-key
partitions, while `kafka#mv-6` asks an availability/refinement question.

### 7. Resource, scheduling, placement, and cost models

**Use when:** the question is about bounded resources, queueing, placement,
parallel work, scheduling policy, retention, or trade-offs among cost and
durability.

**Representative views:**

- Scheduling/queues: `airflow#mv-3`, `fd#mv-2`, `hadoop#mv-3`,
  `linux#mv-2`, `node#mv-1`, `opentelemetry#mv-3`, `rabbitmq#mv-2`,
  `temporal#mv-2`, and `wireguard#mv-2`.
- Placement/allocation: `jax#mv-4`, `kubernetes#mv-3`, `seaweedfs#mv-2`,
  `tensorflow#mv-2`, and `vulkan#mv-1`.
- Cost/retention trade-offs: `redis#mv-5`, `sqlite#mv-5`,
  `svelte#mv-3`, and `influxdb#mv-3`.

**Conservative boundary:** only `redis#mv-5` explicitly uses a Pareto model;
most other performance language remains qualitative. No view currently
provides a probability distribution, reliability model, queueing parameters,
or asymptotic complexity result. These views can be grouped for navigation but
should not be rendered as comparable benchmarks or quantitative guarantees.

## False positives and over-broad neighborhoods

The following are likely false positives if a consumer groups solely by a
keyword such as “graph”, “state machine”, “refinement”, or “algebra”. They are
not card defects by themselves; they are boundaries a neighborhood index must
preserve.

1. **All DAGs are not one family.** `airflow#mv-1` asks task eligibility under
   prior task-instance states; `git#mv-2` asks immutable commit ancestry;
   `pytorch#mv-1` asks reverse-mode accumulation over a dynamic computation
   graph; and `spark#mv-1` asks partitioned lineage. They share directed edges,
   but not node identity, edge semantics, or transition laws.
2. **All transition systems are not interchangeable.** `wasm#mv-2` is an
   abstract machine over store/stack configurations, `react#mv-2` is a
   scheduled render/commit model, `etcd#mv-1` is a committed revision history,
   and `kubernetes#mv-3` is a non-guaranteed placement/reconciliation model.
   A generic “state machine” filter should expose the question and assumptions
   before suggesting similarity.
3. **“Refinement” is overloaded.** `kafka#mv-3` compares observable event
   history under replica representation, `gvisor#mv-3` compares platform
   isolation behavior, `rust#mv-1` describes compiler-representation lowering,
   and `protobuf#mv-2` describes schema evolution. None implies the same
   refinement preorder or preserved observation set.
4. **“Algebra” does not establish algebraic laws.** `authentik#mv-2` has an
   explicit Boolean aggregation operation, while `postgresql#mv-3` is an
   extension boundary and `webpack#mv-3` is an extensible transformation
   vocabulary. These should remain separate unless operations, domains, and
   laws are made explicit.
5. **Graph words hide different boundaries.** `rabbitmq#mv-1` models broker
   routing, `nats#mv-1` models subject-trie subscription matching,
   `openbsd#mv-1` models process/thread ownership, and `threejs#mv-1` models
   transform propagation. The shared graph notation does not imply a common
   edge direction or update semantics.
6. **Replication keywords hide different guarantees.** `cassandra#mv-2`
   models acknowledgement thresholds, `elasticsearch#mv-2` models primary/
   in-sync replica transitions, `postgresql#mv-3` mentions replication only as
   part of an extension boundary, and `kubernetes#mv-1` is a controller feedback
   model. These should not be grouped as “eventual consistency” without a
   separately stated guarantee.
7. **UI/rendering is not one equivalence class.** `react#mv-1`, `vue#mv-2`,
   `svelte#mv-3`, `threejs#mv-2`, `gtk#mv-3`, and `electron#mv-2` span host-tree
   reconciliation, compiler/runtime cost, GPU submission, native backend
   selection, and protocol refinement. The neighborhood is useful for browsing,
   but there is no evidence here for behavioral equivalence.

## Missing or thin model dimensions

The cards cover structural graphs and operational transitions very well. The
following dimensions are underrepresented or absent and would improve
navigation without forcing new claims into existing cards.

### Quantitative performance and reliability

There is no explicit probability/reliability view, queueing model with rates,
or complexity/cost model with asymptotic variables. `redis#mv-5` and
`sqlite#mv-5` are useful cost trade-off candidates, and `rabbitmq#mv-2` is a
natural queueing candidate, but they state no fitted parameters or measured
distribution. Add candidate dimensions only when workload, units, boundary,
and evidence are available; otherwise preserve them as qualitative navigation
tags.

### Temporal logic and invariant vocabulary

Many views state invariants in prose (for example `etcd#mv-1`, `wasm#mv-3`,
`elasticsearch#mv-2`, and `foundationdb#mv-2`), but no view explicitly uses a
temporal-logic model or lists preconditions/postconditions as structured
objects. This makes it hard to compare safety (“nothing bad happens”) with
liveness (“something eventually happens”). `kubernetes#mv-3`,
`argo-cd#mv-1`, `etcd#mv-2`, and `temporal#mv-3` are strong candidates for a
future safety/liveness navigation dimension, subject to explicit assumptions.

### Algebraic laws and compositional semantics

Views named “algebra”, “lattice”, “category”, or “endomorphism” generally use
the term as an explanatory candidate. The dataset has no view that states a
complete operation domain and verifies closure, associativity, identity,
monotonicity, or order laws. In particular, `airflow#mv-3` (“Executor
refinement lattice”), `openbsd#mv-2` (“policy lattice”), and
`postgresql#mv-5` (“isolation-level refinement lattice”) should not be treated
as the same lattice. A future index should distinguish “ordered comparison”
from “lattice laws established”.

### Distributed-time and causal models

`git#mv-2`, `kafka#mv-4`, `flink#mv-2`, and `postgresql#mv-4` expose ancestry,
partial order, watermarks, and dependency edges, but there is no shared
clock/causality dimension describing physical time, logical time, vector clocks,
watermark delay, or clock uncertainty. This is a meaningful missing
neighborhood for distributed systems and stream processors; it must remain
distinct from generic dependency DAGs.

### Security and information-flow semantics

Policy/capability views exist (`openbsd#mv-2`, `deno#mv-1`, `vault#mv-2`,
`cilium#mv-2`, `wasm#mv-3`), but there is no explicit information-flow,
noninterference, attack-surface, or trust-model view. The current capability
graphs are useful navigation anchors, not security proofs. A future model
dimension should state the attacker, observations, trust boundary, and policy
composition rules.

### Error, fault, and recovery cost

Recovery transitions are well represented (`cassandra#mv-3`, `rocksdb#mv-2`,
`sqlite#mv-2`, `velero#mv-1`, `minio#mv-2`), but failure severity, fault
domains, recovery-point/recovery-time objectives, and repair success
probabilities are not modeled uniformly. Do not merge these with ordinary
lifecycle state machines: the failure boundary and recovery objective are the
important discriminators.

### Cross-card version and temporal comparison

The mathematical view itself has no version/validity fields. Temporal context
exists at card level, but a neighborhood consumer cannot tell whether two views
are intended to compare the same release-era semantics. This matters especially
for `rust#mv-1`/`rustc#mv-1`, `gtk#mv-3`/`qt#mv-3`/`wxwidgets#mv-1`, and the
database families. Navigation should surface card version context and evidence
dates before suggesting a cross-card comparison.

## Evidence and modeling follow-ups

1. Add stable view IDs to the schema or a derived deterministic index if
   cross-card neighborhood links are expected. Until then, use the report-local
   `<card>#mv-<position>` notation and treat positions as unstable under view
   reordering.
2. Review the 39 one-evidence views, especially the six-view Kafka set
   (`kafka#mv-1` through `kafka#mv-6`), the five-view Redis set
   (`redis#mv-1` through `redis#mv-5`), and the SQLite visibility/SQL views
   (`sqlite#mv-1`, `sqlite#mv-4`). They are valid references today, but a
   second independent source would improve confidence for cross-cutting claims.
3. Tighten `duckdb#mv-2` with assumptions about bounded batch shape, operator
   purity/side effects, execution backend, and what “amortizes overhead” means;
   its current one assumption is the only view below the normal two-assumption
   floor.
4. Keep claim type and evidence local when adding neighborhoods. A shared model
   family is a navigation aid, not a new `relation`, `influenced-by` edge, or
   composition proof. Historical influence requires separate evidence, and
   equivalence requires explicit observations, mappings, and laws.
5. If the project adds metrics tooling, emit the card count, view count,
   required-field completeness, evidence resolution, claim-type distribution,
   assumption/evidence cardinality, and family membership as reproducible
   outputs. The counts in this report were generated directly from the reviewed
   JSON snapshot because no `scripts/metrics` implementation is present.

## Audit conclusion

Every current reviewed mathematical view meets the repository's basic contract:
model, concrete question, assumptions, and same-card evidence IDs are present
and valid. The strongest reusable organization is a set of overlapping
navigation families—graphs, transitions, typed relations, pipelines,
refinements, distributed history/convergence, and resource/cost models—with
the question and observation boundary retained as the primary discriminator.
The dataset should not infer mathematical equivalence, historical influence,
formal proof, or composability from family membership. The main quality work is
now semantic tightening at overloaded terms (“lattice”, “algebra”,
“refinement”), adding quantitative/temporal/security dimensions where evidence
supports them, and making view identity/versioning explicit for durable
cross-card navigation.

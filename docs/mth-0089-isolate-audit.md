# MTH-0089 G6 candidate and isolate audit

## Scope and method

This audit covers all **172** reviewed cards in `data/systems/`, with focused
review of the G6 candidates and the requested component families. It uses only
card-local evidence IDs and existing reviewed target cards. `related_systems`
entries remain legacy navigation metadata; they do not become typed relations
without a directional, evidence-backed claim. No edge was added merely to make
the graph more connected, and drafts were not inspected or changed.

The initial G6 report regenerated from the 172-card set contained 270 review
candidates. After the two proposed edges below were recorded, the final
candidate report contains 268 candidates because existing typed relations
suppress those two pairs. A candidate score is a review priority, not semantic
confidence.

| Candidate | G6 signal | Decision |
| --- | --- | --- |
| `react-native → react` | `related_systems`, score 30 | **Added proposed `uses`**. The React Native render-pipeline evidence explicitly starts from React element trees. |
| `react-native → threejs` | `related_systems`, score 30 | **No edge**. The cards describe different tree/render domains: React Native mounts platform host views; Three.js submits browser 3D scenes. Shared tree vocabulary is not integration evidence. |
| `ast-grep → tree-sitter` | `related_systems`, score 30 | **Added proposed `uses`**. The workspace, README, and parser-adapter evidence identify a pinned Tree-sitter dependency and direct parser API use. |
| `minio → seaweedfs` | `related_systems`, score 30 | **No typed edge**. Both are distributed object/storage systems, but MinIO evidence does not state that it uses, composes with, or implements SeaweedFS. |
| `expo → react-native` | `related_systems`, source-local mention, score 100 | **Outside this isolate pass**. The candidate is already a concrete review item in the non-isolate Expo card and was not promoted automatically here. |
| `neovim → tree-sitter` | `related_systems`, score 30 | **No edge in this pass**. The candidate has no source-local evidence ID in the current Neovim relation signal; legacy navigation alone is insufficient. |
| `vscode → tree-sitter` | `related_systems`, score 30 | **No edge in this pass**. The candidate has no source-local evidence ID in the current VS Code relation signal. |

## Focused family findings

### React Native and Three.js

React Native has a legitimate framework-input relation to the reviewed React
card. `react-native-render-pipeline` describes React elements becoming host
components and entering the shadow/render/mount pipeline. The relation is a
proposed `uses` fact and is explicitly bounded to that input boundary.

React Native → Three.js is semantic isolation, not missing connectivity. The
React Native card concerns JavaScript element trees, C++ shadow trees, Yoga
layout, and platform host views (`react-native-render-pipeline`,
`react-native-shadow-node-source`, `react-native-mounting-source`). Three.js
concerns Object3D scene hierarchy, geometry/material resources, and a browser
renderer boundary (`threejs-object3d-source`, `threejs-mesh-source`,
`threejs-webgl-renderer-source`). Neither card establishes an integration or
dependency. The existing legacy entry is retained for navigation only.

### Flink and Spark

Spark → Flink is already a safe proposed `resembles` relation with
`claim_type: analogy`, local evidence `spark-cluster-overview` and
`spark-rdd-guide`. It is correctly bounded to distributed scheduling over
partitioned/operator dataflows and explicitly excludes equivalence of state,
time, and execution semantics. No reverse edge or `uses` edge is warranted.

### MongoDB

MongoDB remains a genuine semantic isolate. Its card is internally complete:
document/collection and index abstractions sit above record stores and write
units (`mongodb-collection-api`, `mongodb-record-store`,
`mongodb-write-unit`), with replication/oplog and sharded routing boundaries
(`mongodb-replication-coordinator`, `mongodb-oplog`,
`mongodb-sharding-state`, `mongodb-router-transaction`). No other reviewed
card is identified as a MongoDB integration, and shared database/storage terms
do not justify an edge.

### MinIO and SeaweedFS

The pair is a two-node legacy component, not a typed dependency. MinIO uses an
S3 object namespace, erasure-coded object layout, and healing
(`minio-s3-doc`, `minio-erasure-doc`, `minio-erasure-source`,
`minio-healing-doc`, `minio-healing-source`). SeaweedFS separates volume,
master, filer/gateway, direct routing, and topology-aware replication
(`seaweedfs-readme`, `seaweedfs-volume-source`, `seaweedfs-master-source`,
`seaweedfs-wdclient-source`, `seaweedfs-topology-source`). These are useful
comparative review subjects, but current source-local evidence does not support
`uses`, `composes`, or a sufficiently specific `resembles` claim. The legacy
`minio.related_systems` entry remains unchanged.

### LSP, ast-grep, and Tree-sitter

LSP is a protocol contract and remains isolated because its card deliberately
excludes parser, compiler, index, and server implementation details
(`lsp-initialize`, `lsp-base`). It should not be connected to ast-grep or
Tree-sitter merely because language tooling may use those technologies.

ast-grep → Tree-sitter is the second safe proposed `uses` edge in this pass.
`ast-grep-workspace` records the workspace dependency, `ast-grep-parser`
records the adapter and parser calls, and `ast-grep-readme` attributes parsing
to Tree-sitter. This is a direct implementation boundary and remains
`claim_status: proposed` with `claim_type: fact`.

Tree-sitter's legacy `related_systems` entries for GCC and LLVM remain
navigation-only. The card describes an embeddable C11 parser runtime and does
not state that it uses either compiler toolchain (`tree-sitter-introduction`,
`tree-sitter-getting-started`, `tree-sitter-fixed-source`).

### Qt, GTK, and Flutter

These are semantic isolates. Qt and GTK are independent UI toolkit cards with
different object models, event systems, and platform boundaries; Flutter has
its own Dart widget/element/render-object pipeline and engine/embedder boundary.
The cards provide no integration evidence among the three. Similar concepts
such as widget trees, event dispatch, and platform backends support comparison
work but not an automatic typed edge. Ghostty → GTK remains the existing
proposed `uses` fact, narrowly scoped to Ghostty's selected GTK runtime
(`ghostty-runtime-source`, `ghostty-readme`).

### Kitty, WezTerm, Alacritty, and Ghostty

Kitty, WezTerm, and Alacritty are genuine isolates in the current system graph;
Ghostty is in the `ghostty`–`gtk` two-node component. Their cards are rich
enough for a comparative terminal-emulator review: PTY lifecycle, terminal
parser/screen state, rendering, input, and session topology. They do not cite
one another, and analogous terminal architecture is not historical influence
or implementation reuse. No cross-terminal edge is added.

The cards do not provide a source-local evidence ID that supports adding
`uses` edges to the reviewed Rust card. WezTerm and Alacritty summaries mention
Rust, but relation evidence must be tied to a cited source claim rather than a
summary-only language label. Ghostty's Zig implementation and GTK runtime
selection are distinct boundaries. Thus the terminal family remains isolated
or in its existing GTK component by design.

## Classification of the remaining isolates

The recomputed singleton set is:

`alacritty`, `bazel`, `blender`, `cassandra`, `flutter`, `foundationdb`,
`haproxy`, `imagemagick`, `javafx`, `just`, `kitty`, `leveldb`, `lsp`,
`mongodb`, `oauth2-proxy`, `pulsar`, `qt`, `traefik`, `wezterm`, `wxwidgets`.

For this task's requested families:

- **Genuine semantic isolation:** Alacritty, Flutter, Kitty, LSP, MongoDB, Qt,
  and WezTerm have no supported directional relation to an existing reviewed
  target in the current cards. Their mathematical views remain available and
  are not evidence of software dependency.
- **Missing review:** `ast-grep → tree-sitter` and `react-native → react` were
  the two source-backed reviews resolved here. `expo → react-native` remains a
  separate high-priority G6 candidate because it has source-local mention
  evidence, but is outside this narrowly scoped isolate edit.
- **Legacy navigation:** React Native → Three.js, MinIO → SeaweedFS,
  ast-grep → Tree-sitter before this edit, and Tree-sitter → GCC/LLVM are
  legacy `related_systems` signals unless promoted by an evidence-backed typed
  claim. The two promoted edges preserve their legacy entries.
- **Safe proposed edges already present:** Spark → Flink (`resembles`, analogy)
  and Ghostty → GTK (`uses`, fact) remain correctly bounded and proposed.

## Recomputed metrics

Using the canonical cards after the two relation edits:

- Systems: **172**
- Features: **661**
- Mathematical views: **481**
- Typed relations: **45** (`uses`: 30, `composes`: 4, `resembles`: 11)
- Valid legacy `related_systems` edges: **262**
- Combined directed edges: **307**
- Combined undirected components: **27**
- Component sizes: **140, 2, 2, 2, 2, 2, 2, and 20 singletons**
- Largest component: **140**
- Isolated nodes: **20**

The added edges do not remove a singleton: both source cards were already
connected through legacy navigation or existing graph structure. This is
intentional; graph connectivity is not the acceptance criterion.

The mathematical-view count is a separate navigational projection. It should
not be interpreted as typed software relations, implementation reuse, or
proof of composition compatibility.

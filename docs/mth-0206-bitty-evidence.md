# MTH-0206 Bitty core terminal-platform evidence

<!-- markdownlint-disable MD013 -->

## Research status

**Research-only; non-canonical; review-required; promotion not determined.**
This report is bounded to the fixed revisions below and records evidence for
Bitty's core terminal platform. It does not create or promote a Mathen system
card, relation, API/MCP record, migration, production change, paper, or external
repository edit.

Machine-readable companion: [`data/analyses/external/mth-0206-bitty.json`](../data/analyses/external/mth-0206-bitty.json).

## Fixed provenance and scope

| Repository | Fixed commit | Scope used |
| --- | --- | --- |
| `bitty` | `a168b1976bea8bbab2149e09e24868890f5a4223` | Core Rust crates: runtime orchestration, PTY, platform adapter, rendering, registry/session lifecycle, and core Runtime IPC publication seam |
| `bitty-terminal-docs` | `68af6669c1d28a7dea1651208f800b2e3d232455` | Core terminal-platform documentation: terminal state, registry/view lifecycle, and the local `bittyd` candidate's explicit status boundary |

The source repositories had unrelated working-tree changes, so citations were
read from the fixed commits with `git show`, not from their working trees. Local
documentation references to plugins/extensions, Bitty AI, Wheel, or other
sibling repositories were not used as architectural evidence. Those areas are
recorded only as out of scope.

## Evidence-backed architecture

### 1. Staged terminal truth and bounded side paths

The terminal-state RFC defines the core pipeline as:

```text
PTY bytes -> UTF-8 decoder -> VT Parser -> Action stream -> Terminal State -> Snapshot -> Renderer
```

It states that the parser-produced `Action` stream is the only write path into
terminal state and that readers use versioned snapshots. It also specifies
bounded parsing and invariants for geometry, cells, cursor, scrollback, modes,
tab stops, replies, and hidden channels ([`BTY-DOC-001`](../data/analyses/external/mth-0206-bitty.json#BTY-DOC-001), [`BTY-DOC-002`](../data/analyses/external/mth-0206-bitty.json#BTY-DOC-002)).

The fixed runtime source independently describes the same core flow as PTY
bytes → parser → state → damage → draw list → present, with a strictly bounded
cold queue for observations. When that queue is full, the oldest event is
dropped and counted ([`BTY-SRC-001`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-001), [`BTY-SRC-002`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-002)).

**Typed claim:** `fact` for the documented/source pipeline and bounds;
`inference` for the candidate operational-semantics view.

### 2. PTY/process boundary and flow control

`bitty-pty` exposes an owned PTY/process lifecycle. The source documents direct
argv spawning without shell interpolation, close-on-exec descriptor handling,
fresh Unix child sessions, and a finite reader channel. A stalled consumer
propagates pressure through the channel and kernel PTY, rather than allowing
unbounded memory growth ([`BTY-SRC-003`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-003), [`BTY-SRC-004`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-004)).

This supports a candidate finite-capacity/backpressure model. It does not imply
a throughput, latency, or loss guarantee beyond the cited source wording.

### 3. UI/platform and rendering seams

The platform crate owns the OS event-loop adapter and an owned event vocabulary;
its source says it has no grid, render, or terminal-state business semantics.
Pure event/DPI logic is headless-testable, while display-dependent integration is
opt-in and unavailable displays return an owned error ([`BTY-SRC-006`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-006)).

The render crate consumes public `Snapshot`/`Damage`, creates owned draw records,
and documents an opt-in headless compositor. Runtime construction and tick paths
also use a deterministic in-memory surface for ordinary CI; the source calls out
real GPU/window verification as a separate gap ([`BTY-SRC-001`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-001), [`BTY-SRC-005`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-005)).

**Boundary:** headless evidence supports deterministic logic and composition;
it is not evidence that every real GPU/window path is verified.

### 4. Registry/view lifecycle and identity fencing

The local lifecycle RFC separates terminal lifecycle from view lifecycle and
explicitly excludes multi-window orchestration, `bittyd`, and remote UI from
its scope ([`BTY-DOC-003`](../data/analyses/external/mth-0206-bitty.json#BTY-DOC-003)). It defines distinct terminal, view, runtime, persistent, and generation identities; single ownership; one-view attachment; bounded allocation; and typed fail-closed errors ([`BTY-DOC-004`](../data/analyses/external/mth-0206-bitty.json#BTY-DOC-004)).

The source implements the corresponding bounded constants, newtypes, monotonic
generation checks, persistent-ID validation, and validated logical geometry
boundary ([`BTY-SRC-007`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-007), [`BTY-SRC-008`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-008)). This is suitable for a candidate typed state-machine view of stale handles and lifecycle transitions.

### 5. Local session persistence is fresh-process restoration

The runtime session source records bounded format/restore rules. Restore does not
resurrect a live PTY or `RuntimeId`; it creates fresh shells and treats restored
scrollback as immutable history. Validation completes before mutation, and the
source lists explicit file, line, workspace, pane, scrollback, and depth bounds
([`BTY-SRC-009`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-009)).

Save uses a unique temporary sibling, `write_all`, `sync_all`, atomic rename, and
best-effort parent-directory sync; an oversize snapshot fails before filesystem
mutation ([`BTY-SRC-010`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-010)). This is local file persistence, not daemon session continuity.

### 6. Core IPC publication boundary, not a daemon

The core `host_bridge` source reads committed Runtime state and publishes bounded
observations for out-of-process consumers. It explicitly does not paint, write to
the PTY, mutate terminal truth, spawn a process, or open a socket. Its live
snapshot includes bounded text, generation, cwd, and semantic-zone metadata; the
source also describes read-only inspect registration and deny-by-default effect
tools ([`BTY-SRC-011`](../data/analyses/external/mth-0206-bitty.json#BTY-SRC-011)).

This is evidence of an IPC-facing publication seam inside core. It is not
evidence of a daemon, socket transport, remote UI, session host, or cross-process
registry.

## Candidate reusable features

The JSON packet proposes six reviewable features:

1. `bounded-terminal-state-pipeline` — staged PTY/parser/action/state/snapshot/render flow.
2. `bounded-pty-process-backpressure` — owned direct-argv PTY lifecycle with finite buffering.
3. `headless-rendering-seam` — snapshot/damage rendering with a deterministic headless path.
4. `typed-registry-view-lifecycle` — typed identities, generation fencing, bounded resources, and fail-closed lifecycle errors.
5. `fail-closed-session-rehydration` — atomic bounded local persistence with fresh process identities.
6. `read-publication-ipc-boundary` — bounded observation publication without a daemon claim.

Every feature is `fact`/`proposed` and points to source-local evidence IDs.
Candidate mathematical views are marked `inference`/`proposed`; they describe
questions and assumptions rather than formal proofs.

## Candidate relationships

The packet records three **candidate**, non-canonical supports relationships:

- The terminal pipeline supports the typed registry lifecycle because runtime
  orchestration supplies the terminal-state/render path while the registry
  supplies multi-terminal/view lifecycle (`rel-runtime-supports-registry`).
- Fresh-process session rehydration supports registry identity fencing because
  restored processes receive fresh runtime identities (`rel-session-fences-runtime`).
- The IPC publication seam supports observation of the terminal pipeline because
  it reads committed state without becoming a second state writer
  (`rel-ipc-observes-runtime`).

These are bounded structural inferences, not historical influence, equivalence,
substitutability, or Mathen canonical relations.

## Daemon boundary and limitations

The local `bittyd` session-host document is explicitly marked design input,
not an accepted contract or implementation evidence; it says `bittyd` does not
ship and authorizes no daemon, transport, registry, or fake-server code
([`BTY-DOC-005`](../data/analyses/external/mth-0206-bitty.json#BTY-DOC-005)). The registry RFC independently excludes daemon and remote UI. Accordingly,
this research records daemon/session-host as an explicit negative boundary and
does not model it as an implemented Bitty structure.

Additional limitations:

- Real GPU/window behavior is separately gated from headless runtime evidence.
- Local session files do not establish daemon restart continuity.
- No load, performance, security-audit, historical-influence, or external
  repository claim is made.
- Plugins/extensions, Bitty AI, Wheel, experiments, website, gallery, SDK, and
  other sibling repositories are out of scope and were not cited as evidence.

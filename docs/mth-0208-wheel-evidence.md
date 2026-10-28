# MTH-0208: Wheel architecture evidence

**Status:** research-only, non-canonical, review-required; promotion is not
determined.

## Boundary and provenance

This record covers only the read-only inspection of
`/mnt/data/Workspace/Projects/bitty-terminal/bitty-ai/plugins/wheel` at fixed
HEAD `0d4495692870b91de30ce574060bc8950ffcada8`. The Wheel checkout was not
edited. Structured evidence is in
[`data/analyses/external/mth-0208-wheel.json`](../data/analyses/external/mth-0208-wheel.json).
The JSON records source paths, line ranges, excerpts, source digests, excerpt
digests, claim types, scope, provenance, limitations, and candidate
relationships.

## Findings

### Out-of-process harness and runtime

Wheel's README calls it an independent out-of-process harness. The documented
runtime is a standalone POSIX process with a `WheelHost` seam for filesystem,
process, temporary-file, time, and CPU-time primitives. `host.lua` documents a
`setsid`-recorded process group, bounded stdout/stderr capture, an allowlisted
child environment, explicit stdin staging, timeout outcomes, and cleanup states.
The implementation uses a constant shell wrapper and positional arguments for
the argv path; this is a bounded host seam, not an OS sandbox.

### Authority and security boundary

The trust boundary is the invoking OS user account. Bitty does not grant the
harness authority at runtime. The policy ledger names workspace read/write,
arbitrary argv, shell command strings, provider network egress, and named
provider secrets as the 0.1.0 ceiling, while retaining deny-by-default grants
for sessions, roles, and tools. The source's own security inventory is explicit
that policy is not assurance and lists known gaps: lexical-only path
containment, ambient `HOME` access, partial role enforcement, partial command
screening, and no rlimit/cgroup/seccomp/OS confinement.

### Task roles and orchestration

Roles are Commander, Coding, Debug, Research, and Reviewer. Research and
Reviewer are intended to be read-only, while Commander plans and orchestrates
without direct modification. `WheelTeam` dispatches ready tasks in waves,
publishes task artifacts to context slots, can hand work to an independent
Reviewer, merges accepted task branches, and reports structured telemetry.
`WheelKernel` transitions dependency tasks from pending to ready after
predecessor success and cascades failures to blocked dependents. The source
also documents a headless panel working container for agents; it is a runtime
container/presentation invariant, not evidence of OS isolation.

### Session and daemon behavior

The experimental session control plane lets a runtime outlive one client. A
detached daemon owns one `WheelContext`, opens two private POSIX FIFOs, and
serves bounded `wheel-session/1` newline-framed JSON. Session start validates
the name/root, takes a start lock, cleans only stale state, creates FIFOs, and
publishes metadata after readiness and lock handoff. Client serialization uses
lock files; stop sends explicit `shutdown`. The daemon is deliberately not a
task executor, provider caller, agent runner, or remote service.

The security residual is material: FIFO modes prevent other OS users from
reaching the control plane, but do not authenticate same-user peer processes;
partial input can stall the single-threaded daemon. These are recorded as
limitations rather than hidden behind the word “daemon.”

### Host/plugin boundary

The 0.1.0 product position is one standalone harness artifact. The in-tree
`bitty-plugin.toml` is transitional and is not the supported distribution path;
a Bitty panel or terminal is presentation/input only. The source explicitly
states that there is no plugin-host execution adapter or `bitty.api_version`
authority probe. Future host IPC or a plugin facade is follow-up work and is
not included in this record.

## Explicit references to other systems

- **Git:** Wheel's README explicitly says its context versioning is “inspired by
  Git principles” and describes commits, refs, branches, reflog, LCA merge,
  and cherry-pick. This supports a structural analogy candidate only; it does
  not support historical influence, code reuse, or Git interoperability.
- **SQLite:** `tests/e2e_cross_process.lua` explicitly labels a cross-process
  host fixture and a shared restart database as SQLite. This supports a
  test-source reference only. It does not establish that the standalone Wheel
  runtime or local session daemon is SQLite-backed.
- **Graph/DAG terminology:** local docs and source explicitly use Task DAG,
  topological waves, lowest common ancestor, parent hashes, closed commit
  graph, and parent-cycle rejection. A graph-structured candidate view is
  therefore reasonable as an inference. No general graph-theory theorem or
  formal proof is claimed.
- **OpenCode:** no OpenCode reference was found in the inspected fixed HEAD.
  No OpenCode relationship is asserted.

## Review boundary

The JSON artifact is research evidence, not a `data/systems` card. It does not
modify canonical cards, relations, API/MCP surfaces, migrations, production
resources, paper files, or MTH-0151. Every interpretation remains
`under-review`; `promotion_not_determined` is explicit. Candidate relationships
are bounded research hypotheses/analogies with local evidence and must not be
treated as production graph edges without separate review.

## Reproducibility

Evidence entries use repository-relative source paths and line ranges. Each
entry records the full source-file SHA-256 and an SHA-256 over the UTF-8 excerpt
text (without line-number prefixes). The source commit, inspection boundary,
claim status, and negative OpenCode search result are recorded in the JSON.

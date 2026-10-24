# CarryCtx lifecycle safety

Mathen uses a repository-owned adapter at
`scripts/carryctx_lifecycle.py` for completion verification. Run it from a
registered Mathen worktree:

```bash
uv run python scripts/carryctx_lifecycle.py verify --profile full
uv run python scripts/carryctx_lifecycle.py complete-verified MTH-0000 --profile full
uv run python scripts/carryctx_lifecycle.py complete MTH-0000 --profile full
uv run python scripts/carryctx_lifecycle.py audit MTH-0000 --json
uv run python scripts/carryctx_lifecycle.py audit --all --json
uv run python scripts/carryctx_lifecycle.py verify --profile full --dry-run
uv run python scripts/carryctx_lifecycle.py observe --dry-run
```

`complete-verified` is the recommended repository-owned completion command. It
emits one JSON evidence document containing the selected profile, each command
and result, the task state, the managed/clean/no-active-session/detached gates,
the exact `carryctx task complete` dispatch, and a post-dispatch task read-back.
It runs verification first, re-checks all gates afterward, and dispatches
completion only if every gate passes. It reports `completed` and
`mutation_performed: true` only when the read-back task status is actually
`completed`. A failed profile, dirty worktree, active session, detached checkout,
unmanaged path, or post-verification change returns a non-zero status and does
not dispatch completion. A dispatch failure or read-back mismatch returns a
distinct non-zero result and does not claim confirmed completion. The command
never removes files, worktrees, or branches.

Use `--dry-run` to validate the policy and produce the same evidence shape
without executing verification or changing Git/CarryCtx state:

```bash
uv run python scripts/carryctx_lifecycle.py complete-verified MTH-0000 \
  --profile full --dry-run
```

## Verification profiles

`.carryctx/verification.toml` defines the ordered `python`, `typescript`, and
`full` profiles. Commands run from the Git repository root with `CI=1`, stop at
the first failure, and preserve the command output and exit code. A failed
command returns 10 and never calls `carryctx task complete`.

The `full` profile covers card validation, Python tests/format/lint, TypeScript
checks, API/web/MCP tests, and the web build. The lockfiles and `uv run`/`bun`
commands make the expected tool resolution explicit; the script does not
install dependencies or use an ad-hoc package runner. Profile entries are
parsed as direct argument vectors, not passed through a shell; shell operators
are rejected as invalid policy.

## Completion and cleanup gates

`complete-verified` is intentionally narrower than a generic `carryctx task complete`:

1. the current path must be a registered CarryCtx worktree;
2. the task must be active, attached to a branch, clean, and have no active
   CarryCtx session;
3. the selected profile must pass;
4. the worktree must still be clean after verification;
5. only then is `carryctx task complete` dispatched once.

The older `complete` subcommand remains for compatibility and retains its
historical active-session notice behavior. New automation must call
`complete-verified` and consume its JSON evidence.

An active session is reported as a notice, not treated as permission to remove
anything. CarryCtx's committed policy keeps cleanup `when_idle`, requires a
clean worktree and no active session, and never deletes branches. Therefore an
active session or a cleanup race leaves the worktree preserved with an
actionable CarryCtx cleanup reason. Dirty, missing, unmanaged, external, or
detached paths are never adopted or silently handled.

Repeated completion is idempotent for an already completed task: the adapter
reports the terminal state and does not dispatch completion or retry cleanup.
`--dry-run` produces a stable JSON report containing the selected profile, each
direct `argv` vector, all completion gates, and the projected result. It
validates shell-operator policy but executes no verification command and never
changes project or CarryCtx state. `audit --json` is read-only and explicitly
reports preservation reasons for unmanaged, dirty, and active-session cases.

`audit --all --json` inventories every Git worktree known to the repository's
Git metadata, including the current managed worktree, unmanaged and external
paths, detached checkouts, missing/prunable paths, and dirty status where the
path still exists. It joins the inventory with CarryCtx-managed worktree
records, all sessions, normalized cleanup requests, and a
`git worktree prune --dry-run -v` observation. The prune command is strictly
observational: it is never run without `--dry-run`, and the JSON report marks
that no mutation was performed. Rerunning the audit is therefore repeatable
apart from changes made by external operators.

## Pull request and cleanup observability

`observe` is the repository-owned, read-only first slice for issue #53. It
reports the current branch, an optional GitHub pull-request lookup, the
preservation policy, and the cleanup outbox in one stable JSON document:

```bash
uv run python scripts/carryctx_lifecycle.py observe --json
uv run python scripts/carryctx_lifecycle.py observe --branch carryctx/mth-0000 --dry-run
```

The PR classifier has exactly these states:

- `open`: a non-draft open PR was found;
- `draft`: an open draft PR was found;
- `merged`: GitHub explicitly reports the selected PR as merged;
- `closed`: a closed, unmerged PR was found;
- `local-only`: no PR was found, but the branch exists locally;
- `absent`: no PR was found and the branch is not local (including a missing
  or detached checkout).

The lookup uses only `gh pr list --state all --json`; the adapter does not
create, edit, merge, close, or delete a PR and never embeds credentials.
Unavailable `gh` authentication or network access is reported as an error,
not treated as evidence of absence. A confirmed merge changes only the
observation; the branch policy remains `preserve` with `delete_branch =
"never"`, so branch protection and owner decisions remain authoritative.

The cleanup section exposes counts, pending requests, retryable/blocked
requests, attempt metadata returned by CarryCtx, and the safe retry hint
`carryctx worktree cleanup run --dry-run`. Observation never calls cleanup,
edits CarryCtx SQLite, prunes Git metadata, or removes a worktree or branch.
Use CarryCtx's own cleanup command only as an explicit, separately reviewed
operation. Re-running `observe` is idempotent and has no side effects.

## PR-aware cleanup preview and confirmation

MTH-0126 adds a repository-owned operator gate that joins each selected
CarryCtx cleanup outbox request with the existing PR-aware `branch_policy` and
`cleanup_eligibility` decisions:

```bash
# Dry-run is the default; select one task or worktree when needed.
uv run python scripts/carryctx_lifecycle.py cleanup MTH-0126 --json
uv run python scripts/carryctx_lifecycle.py cleanup \
  --worktree /path/to/worktree --json

# A local-only deliverable requires the explicit existing policy switch.
uv run python scripts/carryctx_lifecycle.py cleanup MTH-0126 \
  --local-deliverable --confirm --json

# Explicitly acknowledge eligible requests. This remains a policy preview.
uv run python scripts/carryctx_lifecycle.py cleanup MTH-0126 --confirm --json
```

Without `--confirm`, an otherwise eligible request reports
`confirmation.required = true` and exits with the unsafe status. `--confirm`
only records the operator's explicit acknowledgement in the output; it does
not dispatch `carryctx worktree cleanup run`, remove a worktree, delete a
branch, prune Git metadata, reset files, edit CarryCtx state, or alter the
outbox. All unsafe requests—including open, draft, closed, lookup-error,
absent, local-only without an explicit policy switch, unmanaged, external,
detached, dirty, and active paths—remain preserved. Historical completed and
cancelled outbox records are retained.

The exact mutation contract is therefore `native_cleanup_dispatched: false`
and `mutation_performed: false` for every invocation. CarryCtx 0.12's native
cleanup operation cannot consume the repository's selected PR state, so this
command intentionally stops at a deterministic policy/preview boundary rather
than bypassing the safety gates. A future native integration must accept the
same PR-state, worktree, session, cleanliness, and task-completion evidence
before dispatch is safe.

The existing CarryCtx Git hooks remain managed by CarryCtx itself:
`carryctx hooks status` is read-only, and repeated `carryctx hooks install`
invocations are the only supported way to reconcile the native hook shims.
The adapter does not overwrite `.git/hooks`, chain an unknown hook, or dispatch
the completion operation from a Git event. The pre-push Lefthook command calls
the same full profile, so a failed verification has one deterministic result
regardless of whether it is requested manually or by the repository hook.

## CarryCtx upstream boundary

CarryCtx v0.12 supports a single ordered `[verification].commands` list and
Git `post-commit`/`prepare-commit-msg` hooks. It does not currently provide
named verification profiles or a completion hook that runs project commands
before `task complete`. The supported list in `.carryctx/config.toml` points to
the full adapter profile, while the profile definitions and completion policy
remain in this repository until that upstream contract exists. Do not add a
second dispatcher or edit CarryCtx's runtime `state.sqlite`.

The adapter is advisory for orchestration: it may refuse unsafe work, but it
does not remove worktrees, delete branches, reset files, prune Git metadata, or
override CarryCtx's cleanup gates.

## Lifecycle state machine

The repository adapter models completion as an explicit, fail-closed state
machine. The allowed transitions are:

| Current state | Event               | Next state         | Meaning                                                   |
| ------------- | ------------------- | ------------------ | --------------------------------------------------------- |
| `ready`       | `start`             | `in_progress`      | Work has an active owner.                                 |
| `in_progress` | `submit_for_review` | `review`           | Verification output is ready for review.                  |
| `in_progress` | `complete`          | `completed`        | Completion gates passed and completion may be dispatched. |
| `review`      | `complete`          | `completed`        | Review accepted the verified result.                      |
| `review`      | `reopen`            | `in_progress`      | Review found work that must continue.                     |
| `completed`   | `observe_cleanup`   | `cleanup_deferred` | Completion is terminal; cleanup remains separately gated. |
| `cancelled`   | `reopen`            | `ready`            | An owner explicitly reopens cancelled work.               |
| `blocked`     | `unblock`           | `ready`            | The blocking condition was explicitly resolved.           |

Unknown states and events are rejected rather than inferred. No transition
deletes a branch, removes a worktree, resets files, or changes CarryCtx state.
The `complete-verified` command enforces the same boundary operationally: unmanaged,
external, detached, dirty, failed-verification, and post-verification-dirty
conditions preserve the worktree and leave the task incomplete. Cleanup is
represented as `cleanup_deferred` and must be performed only by CarryCtx's own
separately reviewed cleanup gate.

## MTH-0120 implementation boundary

The current adapter slice implements and tests the following safeguards:

- GitHub lookup failures are reported as `lookup-error`, never as `local-only`
  or `absent`;
- branch names are validated with Git before lookup/use, and completion refuses
  a managed record that has no branch owner (detached completion);
- cleanup eligibility is a read-only, fail-closed policy projection: a
  confirmed merged PR may pass only with clean/no-session/completed-task gates;
  a local-only branch requires the explicit local-deliverable policy; open,
  draft, closed, absent, lookup-error, detached, unmanaged, and external cases
  are preserved;
- cleanup outbox records expose normalized `retryable`, `safe_to_retry`,
  `preservation_reason`, and `operator_action` fields.

The remaining upstream boundary is native CarryCtx invocation: direct
`carryctx task complete MTH-0000` can still bypass this repository adapter
because CarryCtx v0.12 has no native completion hook or named completion
profile that invokes repository verification and gates before completion.
Operators must explicitly use
`uv run python scripts/carryctx_lifecycle.py complete-verified MTH-0000`
when they require these fail-closed gates. This repository does not intercept
native CarryCtx commands, replace the CarryCtx binary, install a completion
hook, or change CarryCtx globally.

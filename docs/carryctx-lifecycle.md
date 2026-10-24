# CarryCtx lifecycle safety

Mathen uses a repository-owned adapter at
`scripts/carryctx_lifecycle.py` for completion verification. Run it from a
registered Mathen worktree:

```bash
uv run python scripts/carryctx_lifecycle.py verify --profile full
uv run python scripts/carryctx_lifecycle.py complete MTH-0000 --profile full
uv run python scripts/carryctx_lifecycle.py audit MTH-0000 --json
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

`complete` is intentionally narrower than a generic `carryctx task complete`:

1. the current path must be a registered CarryCtx worktree;
2. the task must be active and the worktree must be clean;
3. the selected profile must pass;
4. the worktree must still be clean after verification;
5. only then is `carryctx task complete` dispatched once.

An active session is reported as a notice, not treated as permission to remove
anything. CarryCtx's committed policy keeps cleanup `when_idle`, requires a
clean worktree and no active session, and never deletes branches. Therefore an
active session or a cleanup race leaves the worktree preserved with an
actionable CarryCtx cleanup reason. Dirty, missing, unmanaged, external, or
detached paths are never adopted or silently handled.

Repeated completion is idempotent for an already completed task: the adapter
reports the terminal state and does not dispatch completion or retry cleanup.
`--dry-run` lists/verifies the selected profile and never changes project or
CarryCtx state. `audit --json` is read-only and explicitly reports preservation
reasons for unmanaged, dirty, and active-session cases.

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

# CarryCtx lifecycle safety

Mathen uses a repository-owned adapter at
`scripts/carryctx_lifecycle.py` for completion verification. Run it from a
registered Mathen worktree:

```bash
uv run python scripts/carryctx_lifecycle.py verify --profile full
uv run python scripts/carryctx_lifecycle.py complete MTH-0000 --profile full
uv run python scripts/carryctx_lifecycle.py audit MTH-0000 --json
uv run python scripts/carryctx_lifecycle.py observe --dry-run
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

These safeguards do **not** mean the parent lifecycle issue is complete. The
remaining acceptance gaps are an `audit --all --json` inventory of every Git
worktree (including external, unmanaged, detached, and prunable paths),
inventory of cleanup requests/sessions plus dry-run prune observation, stable
structured `verify --dry-run` profile/argv/projected-result output, and a
fully documented/implemented lifecycle state-machine integration. Native
CarryCtx `task complete` remains able to bypass this repository adapter; this
repository documents that upstream gap but does not claim to intercept or
change CarryCtx globally.

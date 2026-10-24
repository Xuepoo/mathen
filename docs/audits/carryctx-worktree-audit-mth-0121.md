<!-- markdownlint-disable MD013 MD038 -->

# CarryCtx worktree audit (MTH-0121)

> Snapshot timestamp: `2026-10-24T13:12:09Z`
> Scope: read-only inventory and classification for GitHub issue #51. No worktree, branch, file, CarryCtx outbox request, or external path was deleted or modified by this audit.

## Executive decision

**Do not run cleanup or pruning from this report.** The repository contains user work and unmanaged paths that cannot be safely inferred as disposable. The only unambiguous automated result is that five missing `/tmp/opencode` registrations are _Git-prunable_, but they remain owner-confirmation cases because the branches and commits are still present and Git metadata is shared.

The existing policy is appropriately fail-closed: `.carryctx/config.toml` sets `on_task_completed = "when_idle"`, `require_clean = true`, `require_no_active_session = true`, and `delete_branch = "never"`. This audit recommends preserving those settings until the follow-up observability and verification tasks land.

## Deterministic classification contract

Each row below has the following fields:

- `management`: `carryctx_managed`, `unmanaged_git_worktree`, `unmanaged_git_registration`, `main_checkout`, or `carryctx_record_without_git_registration`.
- `classification`: `active`, `retained_task_worktree`, `completed_task_retained`, `external_or_unbound`, `prunable`, `managed_unresolved`, or `unresolved`.
- `dirty`: `true` when `git status --porcelain=v1 --untracked-files=all` returned output; `false` when clean; `null` when the path is missing.
- `detached`: `true` when Git reports no symbolic branch; detached paths are never treated as disposable solely for that reason.
- `active_session_count` / `stale_session_count`: counts from CarryCtx session records. `stale` means ACTIVE and older than the configured two-hour threshold; stale is a warning, not permission to delete.
- `prunable`: `true` only when the Git registration path is missing and `git worktree prune --dry-run` reports the corresponding admin record.
- `recommended_next_action`: explicit preservation or owner-confirmation step; no row authorizes deletion.

## Inventory summary

| Source                           | Count | Meaning                                           |
| -------------------------------- | ----: | ------------------------------------------------- |
| Git worktree registrations       |    53 | Current `git worktree list --porcelain` inventory |
| CarryCtx list entries            |    47 | 41 task-bound records plus 6 unbound Git entries  |
| CarryCtx-managed task worktrees  |    41 | Bound to a CarryCtx task                          |
| Unmanaged/external Git worktrees |    11 | Git-visible but not bound to a CarryCtx task      |
| Missing/prunable registrations   |     5 | `git worktree prune --dry-run` only; not removed  |
| Dirty worktrees                  |     5 | Includes user files; cleanup must remain blocked  |
| Detached worktrees               |     5 | Detached state alone is not evidence of staleness |
| Cleanup outbox requests          |    61 | 60 completed, 1 blocked                           |
| CarryCtx sessions                |     9 | 6 active, 3 ended at snapshot                     |

### Source-of-truth discrepancy

CarryCtx reports 47 entries (41 bound), while Git reports 53 registrations. The eleven Git-only registrations are not automatically safe to remove: six existing external-looking worktrees and five missing paths are present outside CarryCtx's task bindings. Treat the discrepancy as an observability/reconciliation issue, not as cleanup authorization.

## Action queue (non-destructive)

| Priority | Target                                                                                                                                        | Evidence                                                                                                                  | Recommended next action                                                                                                                                                                                                      |
| -------- | --------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| P0       | `carryctx/mth-0019`                                                                                                                           | Completed task; dirty; cleanup outbox blocked after 52 attempts; `docs/relation-graph-report.md` deleted in worktree      | Ask the owner to recover or explicitly discard the deletion. Do not clean, reset, checkout, or remove. After owner decision, re-run status and let the configured cleanup gate decide.                                       |
| P0       | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0070`, `mth-0072`, `mth-0074`                                                             | Dirty, task status `ready`/`in_progress`; untracked review documents                                                      | Preserve. These are user/research files. No cleanup or prune.                                                                                                                                                                |
| P1       | `/tmp/opencode/mathen-drag-fix`, `mathen-graph-startup`, `mathen-model-navigation-api`, `mathen-ui-model-neighborhood`, `mathen-final-review` | Git admin records prunable because paths are missing; four branches remain and one is detached                            | Owner-confirm each path/branch and preserve commit references. Only then may an operator run a narrowly scoped, non-force `git worktree prune` for metadata; branch deletion is prohibited by project policy and this audit. |
| P1       | `/home/fuyu/.local/share/opencode/worktree/41d577/*`                                                                                          | Six external-looking paths are Git-visible but unbound to CarryCtx; deployment branch exists and detached paths are clean | Treat as external/unmanaged. Ask the owning OpenCode session/operator before any remove. Do not bind or remove automatically.                                                                                                |
| P2       | 60 completed cleanup requests                                                                                                                 | Outbox records are completed, but corresponding historical paths are absent from the current Git inventory                | Retain outbox history for auditability. No replay is needed.                                                                                                                                                                 |
| P2       | Active sessions older than two hours                                                                                                          | CarryCtx marks stale sessions as warnings; activity records may be stale or abandoned                                     | Reconcile session ownership through CarryCtx (`session show`/team status) before considering any cleanup. Never infer from age alone.                                                                                        |

## Cleanup outbox

The outbox contains 61 requests. Sixty are `completed`. The sole unresolved request is:

| Request                      | Branch              | State     | Attempts | Blocker          | Path                                                      |
| ---------------------------- | ------------------- | --------- | -------: | ---------------- | --------------------------------------------------------- |
| `01M5JB3C20ZZH11ZCEN0KJ2TQN` | `carryctx/mth-0019` | `blocked` |       52 | `dirty_worktree` | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0019` |

Do not run `carryctx worktree cleanup run` as part of this audit. `mth-0019` is intentionally blocked because its dirty state is evidence of user work; forced cleanup would violate the issue scope and project policy.

## Git-only and prunable registrations

| Path                                                                            | Branch/HEAD state                                              | Present | Dirty   | Classification        |
| ------------------------------------------------------------------------------- | -------------------------------------------------------------- | ------- | ------- | --------------------- |
| `/home/fuyu/.local/share/opencode/worktree/41d577/cli-data-doctor`              | `DETACHED` / `379ce6840f2d`                                    | `true`  | `false` | `external_or_unbound` |
| `/home/fuyu/.local/share/opencode/worktree/41d577/cross-platform-ci`            | `DETACHED` / `b17e7e65bf4c`                                    | `true`  | `false` | `external_or_unbound` |
| `/home/fuyu/.local/share/opencode/worktree/41d577/deployment-configurable-urls` | `chore/MTH-0108-deployment-configurable-urls` / `568210a3516d` | `true`  | `false` | `external_or_unbound` |
| `/home/fuyu/.local/share/opencode/worktree/41d577/frontend-followup`            | `DETACHED` / `67a8503e4c0e`                                    | `true`  | `false` | `external_or_unbound` |
| `/home/fuyu/.local/share/opencode/worktree/41d577/hosted-mcp-r2`                | `DETACHED` / `497e31b1f459`                                    | `true`  | `false` | `external_or_unbound` |
| `/home/fuyu/.local/share/opencode/worktree/41d577/web-performance`              | `DETACHED` / `bc6e9700fa40`                                    | `true`  | `false` | `external_or_unbound` |
| `/tmp/opencode/mathen-drag-fix`                                                 | `UNAVAILABLE` / `UNAVAILABLE`                                  | `false` | `none`  | `prunable`            |
| `/tmp/opencode/mathen-final-review`                                             | `UNAVAILABLE` / `UNAVAILABLE`                                  | `false` | `none`  | `prunable`            |
| `/tmp/opencode/mathen-graph-startup`                                            | `UNAVAILABLE` / `UNAVAILABLE`                                  | `false` | `none`  | `prunable`            |
| `/tmp/opencode/mathen-model-navigation-api`                                     | `UNAVAILABLE` / `UNAVAILABLE`                                  | `false` | `none`  | `prunable`            |
| `/tmp/opencode/mathen-ui-model-neighborhood`                                    | `UNAVAILABLE` / `UNAVAILABLE`                                  | `false` | `none`  | `prunable`            |

`git worktree prune --dry-run -v` reported these five missing admin records:

- `mathen-drag-fix`: `/tmp/opencode/mathen-drag-fix` (`UNAVAILABLE`, HEAD `c4399b6f855e`); **not pruned**.
- `mathen-final-review`: `/tmp/opencode/mathen-final-review` (`UNAVAILABLE`, HEAD `0d5194cc7603`); **not pruned**.
- `mathen-graph-startup`: `/tmp/opencode/mathen-graph-startup` (`UNAVAILABLE`, HEAD `18b69365ad66`); **not pruned**.
- `mathen-model-navigation-api`: `/tmp/opencode/mathen-model-navigation-api` (`UNAVAILABLE`, HEAD `2d2d9c1e0ee8`); **not pruned**.
- `mathen-ui-model-neighborhood`: `/tmp/opencode/mathen-ui-model-neighborhood` (`UNAVAILABLE`, HEAD `8133291d9241`); **not pruned**.

## CarryCtx-managed worktrees

| Path                                                      | Branch              | Task       | Task status   | Dirty   | Cleanup pending | Sessions | Classification            |
| --------------------------------------------------------- | ------------------- | ---------- | ------------- | ------- | --------------- | -------: | ------------------------- |
| `/tmp/opencode/mathen-mth-0121`                           | `carryctx/mth-0121` | `MTH-0121` | `in_progress` | `false` | `false`         |        1 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0008` | `carryctx/mth-0008` | `MTH-0008` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0012` | `carryctx/mth-0012` | `MTH-0012` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0013` | `carryctx/mth-0013` | `MTH-0013` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0014` | `carryctx/mth-0014` | `MTH-0014` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0015` | `carryctx/mth-0015` | `MTH-0015` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0016` | `carryctx/mth-0016` | `MTH-0016` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0017` | `carryctx/mth-0017` | `MTH-0017` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0018` | `carryctx/mth-0018` | `MTH-0018` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0019` | `carryctx/mth-0019` | `MTH-0019` | `completed`   | `true`  | `true`          |        0 | `completed_task_retained` |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0058` | `carryctx/mth-0058` | `MTH-0058` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0059` | `carryctx/mth-0059` | `MTH-0059` | `in_progress` | `false` | `false`         |        1 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0060` | `carryctx/mth-0060` | `MTH-0060` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0061` | `carryctx/mth-0061` | `MTH-0061` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0062` | `carryctx/mth-0062` | `MTH-0062` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0063` | `carryctx/mth-0063` | `MTH-0063` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0064` | `carryctx/mth-0064` | `MTH-0064` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0065` | `carryctx/mth-0065` | `MTH-0065` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0066` | `carryctx/mth-0066` | `MTH-0066` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0067` | `carryctx/mth-0067` | `MTH-0067` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0069` | `carryctx/mth-0069` | `MTH-0069` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0070` | `carryctx/mth-0070` | `MTH-0070` | `ready`       | `true`  | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0071` | `carryctx/mth-0071` | `MTH-0071` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0072` | `carryctx/mth-0072` | `MTH-0072` | `in_progress` | `true`  | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0073` | `carryctx/mth-0073` | `MTH-0073` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0074` | `carryctx/mth-0074` | `MTH-0074` | `in_progress` | `true`  | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0075` | `carryctx/mth-0075` | `MTH-0075` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0076` | `carryctx/mth-0076` | `MTH-0076` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0078` | `carryctx/mth-0078` | `MTH-0078` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0083` | `carryctx/mth-0083` | `MTH-0083` | `blocked`     | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0086` | `carryctx/mth-0086` | `MTH-0086` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0087` | `carryctx/mth-0087` | `MTH-0087` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0089` | `carryctx/mth-0089` | `MTH-0089` | `review`      | `false` | `false`         |        1 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0090` | `carryctx/mth-0090` | `MTH-0090` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0094` | `carryctx/mth-0094` | `MTH-0094` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0096` | `carryctx/mth-0096` | `MTH-0096` | `review`      | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0099` | `carryctx/mth-0099` | `MTH-0099` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0100` | `carryctx/mth-0100` | `MTH-0100` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0101` | `carryctx/mth-0101` | `MTH-0101` | `ready`       | `false` | `false`         |        0 | `retained_task_worktree`  |
| `/tmp/opencode/mathen-mth-0111`                           | `carryctx/mth-0111` | `MTH-0111` | `in_progress` | `false` | `false`         |        0 | `active`                  |
| `/tmp/opencode/mathen-mth-0112`                           | `carryctx/mth-0112` | `MTH-0112` | `in_progress` | `true`  | `false`         |        0 | `active`                  |

Notes:

- The current audit worktree (`MTH-0121`) is clean and has an active session; it is `active`, never a cleanup candidate.
- Ready tasks with no active session remain retained task worktrees, not stale disposable paths. Their task status is a lifecycle signal, not an authorization to delete.
- `mth-0019` is the only managed completed-task worktree with pending cleanup and is blocked by dirty user content.

## Dirty state details

### `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0019`

- ` D docs/relation-graph-report.md`

### `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0070`

- `?? docs/review-math-neighborhood-report.md`

### `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0072`

- `?? docs/review-graph-ux.md`

### `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0074`

- `?? docs/review-extraction-pipeline.md`

### `/tmp/opencode/mathen-mth-0112`

- ` M src/mathen/cli.py`
- ` M src/mathen/llm.py`
- ` M src/mathen/modeling.py`

## Sessions and liveness

CarryCtx session policy says ACTIVE/PAUSED sessions older than `stale_after = "2h"` are reported stale on status; staleness is not terminal and must not trigger deletion. At this snapshot, several historical active sessions have last activity older than two hours, including sessions associated with `MTH-0089`, `MTH-0059`, `MTH-0023`, and the external `/mnt/data/Workspace/Projects/soft2math` checkout. Their worktrees must remain preserved until ownership is reconciled.

| Session                      | State    | CWD                                                       | Task                         | Last activity                         | Audit treatment              |
| ---------------------------- | -------- | --------------------------------------------------------- | ---------------------------- | ------------------------------------- | ---------------------------- |
| `01M5Q0EMFK4GBSQYN92BMT2NHA` | `active` | `/tmp/opencode/mathen-mth-0121`                           | `01M5PZESHTFM6HRGSCEYN2YYCD` | `2026-10-24T13:08:55.922891119+00:00` | preserve; active             |
| `01M5MSXHE41P74V3812RT748B2` | `ended`  | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0088` | `01M5MS3WV58FF9BVXXC969SA4K` | `2026-10-23T16:36:15.426462527+00:00` | historical; retain record    |
| `01M5MSBMA1JNWM280FW5EWWVJH` | `active` | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0089` | `01M5MS3WVTTMBBX2ZRQ0DESB88` | `2026-10-23T16:26:28.545536581+00:00` | preserve; stale warning only |
| `01M5MMYAJCH0BCVR9R1JVJH41F` | `active` | `/mnt/data/Workspace/Projects/mathen`                     | `—`                          | `2026-10-23T15:09:18.270616574+00:00` | preserve; stale warning only |
| `01M5KH560KVJMZG63B3SYWYH36` | `ended`  | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0073` | `01M5KH0JPNEDQVZ2HEBW61NWFM` | `2026-10-23T04:43:54.250063121+00:00` | historical; retain record    |
| `01M5KGWNHFTATS28K584HF6N16` | `ended`  | `/mnt/data/Workspace/Projects/mathen`                     | `—`                          | `2026-10-23T04:39:15.247006370+00:00` | historical; retain record    |
| `01M5KGF8R1W17JWM07N3NNWYPF` | `active` | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0059` | `01M5KGBJ87VDS31HD355GQCHVW` | `2026-10-23T04:31:56.158091294+00:00` | preserve; stale warning only |
| `01M5JFNFEY17E48VM1FTEGBZ6F` | `active` | `/mnt/data/Workspace/Projects/mathen/.worktrees/mth-0023` | `01M5JA36G6XDNSFMHGJ6Z63C1D` | `2026-10-22T18:58:36.636310724+00:00` | preserve; stale warning only |
| `01M5ERKR1X65B6K7144HFN0746` | `active` | `/mnt/data/Workspace/Projects/soft2math`                  | `—`                          | `2026-10-21T08:17:59.356963981+00:00` | preserve; stale warning only |

## Safe migration procedure (future operator, still non-destructive by default)

1. Save a fresh, timestamped inventory using `carryctx worktree list --json`, `carryctx task list --json`, `carryctx session list --json`, `carryctx worktree cleanup list --json`, `git worktree list --porcelain`, and `git status --porcelain=v1 --untracked-files=all` in each existing path.
2. For every path, compare the Git registration, CarryCtx binding, task status, session state/age, branch, HEAD, dirty state, detached state, and path existence. Do not treat a missing CarryCtx row or stale session as proof of disposability.
3. For dirty paths, stop and obtain owner instructions. Preserve untracked and deleted files; do not reset, checkout, clean, or force-remove.
4. For active/review/ready task worktrees, preserve the path and branch. For completed tasks, use the outbox only after clean and no-active-session gates are independently verified.
5. For Git-only or external paths, obtain explicit owner confirmation and record the decision. Binding an external path to CarryCtx is a state change and must not be inferred.
6. For missing Git paths, preserve branch and commit references first. If owner-approved, run only a narrowly scoped, non-force metadata prune; never delete branches under the current `delete_branch = "never"` policy.
7. Re-run the complete inventory and verify that only the explicitly approved metadata changed. Record the before/after IDs, branches, paths, HEADs, and outbox result.

## No-delete policy

This audit made no destructive changes. Specifically, it did not run `carryctx worktree cleanup run`, `carryctx worktree remove`, `git worktree remove`, `git worktree prune` without `--dry-run`, `git branch -D`, `git reset`, `git checkout`, recursive deletion, or edits to CarryCtx runtime state. Future automation must preserve this fail-closed rule: never delete a worktree, branch, user file, detached checkout, or unmanaged/external path based only on age, task completion, missing registration, dirtiness uncertainty, or prunable metadata.

## Reproducibility and unresolved cases

- Repository HEAD at audit start: `9fcc4db470af94c85fa4e298099ad2b92acb794f`.
- Runtime state is in the shared CarryCtx SQLite database and is intentionally not committed or edited by hand.
- The report is a point-in-time snapshot. Concurrent sessions can change task/session/outbox state after the timestamp.
- Unresolved: owners of the five prunable `/tmp/opencode` registrations and six external `/home/fuyu/.local/share/opencode`/Git-only paths must confirm intent.
- Unresolved: the deleted `docs/relation-graph-report.md` in `mth-0019` requires owner decision; this report does not restore or discard it.
- Unresolved: stale active session records require lifecycle reconciliation; no session was ended or abandoned.

## Evidence commands

```text
carryctx worktree list --json
carryctx task list --json --fields id,display_id,status,title,owner_agent_id,updated_at,completed_at
carryctx session list --json
carryctx worktree cleanup list --json
git worktree list --porcelain
git worktree prune --dry-run -v
git status --porcelain=v1 --untracked-files=all
```

**Recommended disposition: preserve everything pending explicit owner decisions; this issue is audit-complete but cleanup/migration is intentionally not authorized.**

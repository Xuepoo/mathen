# CarryCtx

<!-- carryctx:v1 -->

This directory stores versioned CarryCtx project configuration committed to Git.
It is safe to commit `.carryctx/` — it holds shared config, presets, and rules.

Runtime state (tasks, agents, events, sessions) lives in
`<git-common-dir>/carryctx/state.sqlite`, not in `.carryctx`.
Do not edit `state.sqlite` by hand; use `carryctx` commands or MCP tools.

## Snapshot lifecycle boundary

The fixed `refs/heads/carryctx-snapshots` branch is an operator-only,
repository-owned publication channel for **redacted CarryCtx lifecycle
metadata**. It is not canonical architecture research data and must never
contain unredacted state. Use `just workflow-publish --dry-run` to validate;
only an explicit `just workflow-publish --push` may send the validated ref to a
remote. Use `just workflow-import --dry-run` before restoring and pass
`--force` only when replacing a non-empty local database is intentional.

Publication provenance is carried by the snapshot commit's
`CarryCtx-Source` and `CarryCtx-Export-Id` trailers and checked against the
redacted manifest. Import restores an existing `.carryctx/config.toml`
byte-identically and refuses unsafe local-state replacement by default.

Snapshot publication and import are operator actions; ordinary checks and merge
automation do not invoke them. Keep reviewed cards, drafts, evidence, and
canonical research boundaries under `data/` independent of this lifecycle
metadata channel.

- Repository: https://github.com/Xuepoo/carryctx
- Documentation: https://carryctx.xuepoo.xyz
  (see `carryctx-docs/configuration.md` for storage and XDG layout)

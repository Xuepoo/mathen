# CarryCtx

<!-- carryctx:v1 -->

This directory stores versioned CarryCtx project configuration committed to Git.
It is safe to commit `.carryctx/` — it holds shared config, presets, and rules.

Runtime state (tasks, agents, events, sessions) lives in
`<git-common-dir>/carryctx/state.sqlite`, not in `.carryctx`.
Do not edit `state.sqlite` by hand; use `carryctx` commands or MCP tools.

## Snapshot lifecycle boundary

`refs/heads/carryctx-snapshots` is an operator-only publication channel for
**redacted CarryCtx lifecycle metadata**. It is not a D1 backup, and it is not
canonical architecture research data: it must never contain cards, drafts,
evidence bundles, analyses, or research data. Use `just workflow-publish
--dry-run` to validate; only an explicit `just workflow-publish --push` may
send the validated immutable ref to a remote. Use `just workflow-import
--dry-run` before restoring and pass `--force` only after reviewing local
state.

Publication provenance is carried by the snapshot commit's
`CarryCtx-Source` and `CarryCtx-Export-Id` trailers and checked against the
redacted manifest. Import restores an existing `.carryctx/config.toml`
byte-identically, preserving its mode, and refuses active or non-empty shared
database replacement by default. Scripts resolve Cargo-managed CarryCtx 0.12.0
explicitly or require `CARRYCTX_BIN`; PATH order is not trusted.

Snapshot publication and import are operator actions. Ordinary checks, merge
automation, and CI never publish, import, or create the snapshot branch.

- Repository: https://github.com/Xuepoo/carryctx
- Documentation: https://carryctx.xuepoo.xyz
  (see `carryctx-docs/configuration.md` for storage and XDG layout)

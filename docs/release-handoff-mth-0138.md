# MTH-0138 protected-main release handoff

**Status:** handoff for commander review; no push, merge, deployment, or task
completion was performed by this worktree.

## Release identity

- **Source:** local protected `main` at `2ba05db`
  (`fix(public-mvp): align retrieval docs and evidence links`), 55 commits
  ahead of `origin/main` (`9fcc4db`). The worktree is clean and contains no
  generated build output.
- **Public browser/API:** [https://mathen.xuepoo.xyz](https://mathen.xuepoo.xyz)
- **Production Worker:** `mathen-api`, version
  `729ea77e-4d48-400e-974d-a82b9cc13377`, read back at 100% traffic on
  2026-10-25T10:07:16Z.
- **Alternate origin:**
  `https://mathen-api.ven3428set.workers.dev` (not used as the release URL).

## Scope and data boundaries

The release provides a reviewed-only architecture atlas, graph projections,
read APIs, and the hosted/read-only MCP transport. D1 is the canonical
structured store for reviewed systems, features, evidence, views, trade-offs,
and explicit relations. Graph projections and retrieval indexes are derived
and rebuildable; drafts, schemas, fixtures, analyses, and local benchmark
manifests are not promoted into D1 or exposed through the hosted API/MCP.

The retrieval MVP is a **bounded lexical baseline** over hydrated reviewed D1
records (`GET /api/retrieval` and MCP `search_semantic`). It uses lexical
overlap ranking with uncalibrated discovery scores and preserves IDs, claim
metadata, evidence, scope, provenance, and warnings. It does not infer graph
edges, truth, compatibility, causality, originality, or historical influence.
There are no semantic/vector embeddings or Vectorize integration yet; the
future index remains optional and rebuildable.

## API, browser, and MCP behavior

- The browser uses same-origin `/api/*` requests at the public URL.
- API success responses retain the `{ "data": ... }` envelope. The hosted
  API and MCP are read-only and reviewed-only; no authenticated write or
  promotion flow exists.
- The hosted MCP endpoint is `/api/mcp`. Requests require the exact
  `Authorization: Bearer <API_ACCESS_TOKEN>` secret. An unauthenticated call
  returns 401; an origin outside the exact `MCP_ALLOWED_ORIGINS` list is
  rejected (403); allowed-origin preflight succeeds with CORS headers.
- No token was supplied for authenticated MCP verification, so successful
  token-authenticated `tools/list` and `search_semantic` calls remain an
  operator follow-up. Browser MCP is intentionally not a no-token path.
- The stdio MCP client can read reviewed filesystem/API data, but retrieval is
  explicitly unavailable in filesystem mode without a verified local index.

## Verification and deployment read-back

The accepted MTH-0142 verification recorded:

- 194 Python unit tests passed; card validation, retrieval evaluation command,
  Ruff format/check, Actionlint, Gitleaks, and `git diff --check` passed.
- Commander/mainline verification passed the TypeScript checks, API/Web/MCP
  tests, and Web build. The independent verifier worktree lacked
  `node_modules`, so its direct Bun checks were environment-limited; do not
  report those failed local invocations as product regressions.
- Public homepage/assets, health, access configuration, graph, model graph,
  layered graph, and known retrieval query returned 200. Retrieval returned
  `ready`, `canonical_cards`, `bounded_lexical_baseline`,
  `lexical_overlap`, three reviewed results, evidence/provenance, and no draft
  paths. A long no-match query returned a successful empty result with its
  warning.
- Hosted MCP read-back returned allowed-origin `OPTIONS` 204, no-token 401,
  and denied-origin `OPTIONS`/POST 403. No authenticated token was available.
- Remote D1 migrations `0001` through `0006` are applied with no pending
  migrations; read-only SQL read-back reported 219 systems and
  `rows_written=0`. The Worker deployment was not rerun for this handoff.

There is no formal representative mobile performance/device matrix in this
release. Touch and small-screen behavior is supported by the current UI, but
mobile performance remains unclaimed pending representative-device evidence.

## Remaining boundaries and transport

- CarryCtx upstream issues [#52](https://github.com/Xuepoo/mathen/issues/52)
  (verification profiles) and
  [#53](https://github.com/Xuepoo/mathen/issues/53) (PR/cleanup observability)
  remain upstream boundaries; this handoff does not alter or dispatch them.
- Protected `main` is the correct release source, but it is local-only and
  ahead of `origin/main`. The commander/release owner must choose the approved
  protected-main transport (for example, the repository's normal reviewed
  fast-forward/PR process). This agent must not push, force-push, create a PR
  through the network, or merge.
- No source, card, draft, D1, R2, Worker configuration, secret, or production
  deployment was changed by this handoff.

## Handoff recommendation

Accept the release summary above as the production read-back for the local
protected-main baseline, retain the documented no-token/no-browser-MCP,
no-formal-mobile-matrix, and no-semantic/vector-embeddings limitations, and
transport `2ba05db` only through the protected-main release process. MTH-0138
remains open until the commander independently verifies and completes it.

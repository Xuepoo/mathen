# MTH-0202 browser evidence readiness

Date: 2026-10-28  
Source commit: `2308f26` (`origin/main` after the PR #74 release)  
Scope: remaining browser evidence gaps listed in
[`mth-0198-graph-browser-audit.md`](mth-0198-graph-browser-audit.md). This is a
readiness record only. No API, canonical card, production, or paper files were
changed.

<!-- markdownlint-disable MD013 -->

## Execution boundary

The browser-only checks used a local Vite server and explicit Playwright route
fixtures for the graph, system summaries, model graph, access configuration,
and card detail. The local D1-backed API was not usable in this worktree: its
reused Wrangler state reported `no such table: systems` and then
`SQLITE_CANTOPEN`. Consequently, no real API-backed graph payload, card
payload, or network timing is claimed by this record.

| Item | Actual value |
| --- | --- |
| Browser automation | Playwright 1.64.0 from the installed global module |
| Chromium | 156.0.8078.47, `/usr/bin/chromium`, headless, `--no-sandbox` |
| Firefox | Mozilla Firefox 158.0.1, `/usr/bin/firefox` |
| Desktop viewport | 1280 × 900 CSS px, device scale factor 1 |
| Bounded touch emulation | 390 × 844 CSS px, device scale factor 3, `isMobile=true`, `hasTouch=true`; Chromium desktop binary, not a real device |
| UI source | Vite dev server from this worktree, with mocked API responses |
| Real API / D1 | null; not measured because local D1 could not open a usable seeded database |

## Remaining-gap observations

| Gap | Result | Bounded observation |
| --- | --- | --- |
| Firefox automation attachability | **Not measured** | Launching `/usr/bin/firefox` through Playwright 1.64.0 `juggler-pipe` failed before a page was created. Firefox exited with code 0 after the Juggler pipe launch; no Firefox UI result is claimed. |
| Real mobile/touch behavior | **Not measured** | Chromium emulation exposed `innerWidth × innerHeight = 390 × 844`, `devicePixelRatio = 3`, and `ontouchstart` support. This is emulation only; real mobile hardware, touch gestures, and pinch behavior are null. |
| Network metrics | **Not measured** | Real API request timings, mobile network profile, Lighthouse mobile metrics, and Core Web Vitals are null. The fixture run intentionally did not substitute local fixture timing for network evidence. |
| Card-close assertion | **Pass, fixture scope only** | On Chromium 156.0.8078.47 with Playwright 1.64.0, the architecture-card dialog closed and lost its `open` state at both 1280 × 900 and the bounded 390 × 844 touch-emulated viewport. The detail payload was mocked; this is not a real API-backed card pass. Both runs reported no page or console errors. |
| Interactive saved two-endpoint path/color flow | **Not measured** | The fixture browser run loaded the path panel but did not reach two selected endpoints or expose the save-color action. No interactive path or color pass is claimed. Existing deterministic route/serialization unit tests remain separate evidence. |
| Edge-hit relation metadata | **Not measured** | No stable pointer hit on a WebGL edge was obtained. Relation metadata was not promoted from the existing keyboard/card checks to an edge-hit pass. |

## Bounded browser smoke observations

These observations are limited to the fixture-backed UI run and are not
production or performance claims.

| Viewport | Load-to-count | Body bounds | Count | Page/console errors |
| --- | ---: | --- | --- | --- |
| 1280 × 900, DPR 1 | 152 ms | 1280 × 900 | 3 systems / 1 relation | none observed |
| 390 × 844, DPR 3, touch emulation | 151 ms | 390 × 844 | 3 systems / 1 relation | none observed |

The load values above are local fixture-run observations, not network metrics,
mobile metrics, or Core Web Vitals.

<!-- markdownlint-enable MD013 -->

## Reproduction and readiness limitations

```sh
bun run check:web
bun test apps/web/src/*.test.ts
bun run build
# Browser-only fixture run used the installed Playwright module and a local
# Vite server; its temporary script and output stayed under /tmp/opencode/.
```

The web checks passed once the existing ignored dependency links from another
worktree were reused; no dependencies were installed. The API-backed browser
run remains blocked by the local D1 state described above. A future complete
record needs a named Firefox automation path that attaches successfully, a
real touch-capable device, a named network profile and workload, stable
two-endpoint interaction, and a reproducible WebGL edge target. Until then,
the corresponding values remain **null / not measured** rather than inferred.

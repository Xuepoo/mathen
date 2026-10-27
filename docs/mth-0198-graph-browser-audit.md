# MTH-0198 graph browser audit

Date: 2026-10-27  
Source commit: `ec70a18316ff54f7efda3706d40bc40efb7d256a`  
Scope: browser verification of the current graph exploration UI only. No API,
canonical card, relation, production, or paper files were changed.

## Execution assumptions

<!-- markdownlint-disable MD013 -->

| Item | Actual value |
| --- | --- |
| Browser | Chromium 156.0.8078.47, headed, system binary `/usr/bin/chromium` |
| Automation | Playwright 1.64.0, global module; no dependencies installed |
| Firefox | Mozilla Firefox 158.0.1 present, but Playwright could not attach to the system binary through `juggler-pipe`; no Firefox result is claimed |
| Desktop viewport | 1280 × 900 CSS px, reduced-motion context, device scale factor 1 |
| Bounded small viewport | 390 × 844 CSS px, reduced-motion context, device scale factor 1; desktop Chromium context, not a real mobile device |
| URL | `http://127.0.0.1:5173/`, Vite dev server backed by the local API on port 8787 |
| Graph payload | 219 systems / 421 relations; Math Models: 219 systems / 307 models / 592 model links |
| Build | Vite 7.3.7 production build from this commit |

The temporary browser scripts and traces were kept outside the repository under
`/tmp/opencode/`. The worktree dependency directories used for the run were
ignored symlinks/reused local packages and are not part of the commit.

## Executed browser evidence

| Check | Result | Observation |
| --- | --- | --- |
| Graph load | Pass | Both viewports loaded the graph and lazy `3d-force-graph` chunk. Headed Chromium load-to-count was 416 ms desktop and 383 ms at 390 × 844 in this local run. |
| Canvas and body bounds | Pass | Canvas filled the viewport. `scrollWidth × scrollHeight` was 1280 × 900 desktop and 390 × 844 small viewport; no body overflow. |
| Systems / Math Models mode | Pass | The mode toggle reached Math Models and returned to Systems with the counts above. |
| Accessible Math Models labels | Pass | The keyboard catalog showed `Mathematical model family` entries and `Locate on graph` buttons. Example: `Same title: Abstraction-layer compatibility relation`. On the small viewport, graph labels are intentionally focused-only; the catalog remains the accessible label surface. |
| Search and inspector | Pass | Searching `Temporal` exposed one result and opened the Temporal inspector. The clear-selection button restored the inspector hidden state. |
| Exploration path panel | Pass | Adding one endpoint opened the path panel and displayed the explicit exploratory-only boundary text. |
| Hidden-node route behavior | Pass | Hiding a selected node changed the count to 218 systems / 418 relations and exposed `Restore hidden (1)`; restoring hid the button again. On the small viewport the control is in the collapsed More group, so the audit opened that group before attempting it. |
| Catalog close/focus | Pass | Escape closed Browse systems and focus returned to `#catalog-open`. |
| Card rendering and relation metadata | Pass | The Temporal card opened from the keyboard catalog, rendered `Feature relations` and `Relations`, and had no page/console errors. |
| Card close | Not measured | The isolated card run reached card rendering but its close assertion was interrupted by the harness timeout; no card-close pass is claimed. |
| Saved paths/colors | Not measured interactively | WebGL label-to-node pointer targeting was not stable enough to select two endpoints reproducibly. Deterministic unit tests cover route serialization and saved color behavior; no interactive pass is claimed here. |
| Relation metadata from a clicked edge | Not measured interactively | Dense WebGL edges were not reliably targetable by pointer automation. Card relation metadata was verified through the keyboard card surface; no edge-hit pass is claimed. |

<!-- markdownlint-enable MD013 -->

The browser run recorded no ordinary JavaScript page errors or console errors in
the completed focused checks. The earlier failed script steps were harness
selector/sequence failures and are not reported as product passes.

## Local performance smoke

Lighthouse 13.5.0 ran against the production preview at
`http://127.0.0.1:4174/`, using headless Chromium 156.0.8078.47 with the system
binary and `--no-sandbox`. These are local smoke values, not representative
mobile metrics:

| Metric | Actual value |
| --- | ---: |
| Performance | 72/100 |
| Accessibility | 100/100 |
| Best practices | 100/100 |
| SEO | 92/100 |
| First Contentful Paint | 2.0 s |
| Largest Contentful Paint | 3.9 s |
| Total Blocking Time | 570 ms |
| Speed Index | 2.0 s |
| Time to Interactive | 4.5 s |
| Cumulative Layout Shift | 0 |
| Initial JS asset | 70.05 KiB raw / 24.64 KiB gzip |
| Lazy graph chunk | 1.32 MiB raw / 368.42 KiB gzip |

Representative mobile hardware, touch/pinch execution, and mobile network
profile metrics: **not measured**. The 390 × 844 run is a bounded desktop
Chromium viewport check only. No UI defect was narrowly reproduced, so no
product fix was made.

## Reproduction

```sh
bun run db:reset:local
bun run build
# API: cd apps/api && bun run dev -- --port 8787
# Web: cd apps/web && bun run dev -- --port 5173
bun run check:web
bun test apps/web/src/*.test.ts
lighthouse http://127.0.0.1:4174/ --output=json \
  --output-path=/tmp/opencode/mth-0198-lighthouse.json \
  --chrome-path=/usr/bin/chromium --chrome-flags='--no-sandbox' --quiet
bun scripts/web_performance_report.ts \
  --dist apps/web/dist \
  --lighthouse-json /tmp/opencode/mth-0198-lighthouse.json \
  --output /tmp/opencode/mth-0198-performance-report.md
```

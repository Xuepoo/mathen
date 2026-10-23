# Graph-first UX review (MTH-0072)

Date: 2026-10-23

Reviewed integration: `b1bd2c7` (`[MTH-0058] feat(web): replace catalog with force graph explorer`)

## Reproducible setup

From the MTH-0058 worktree:

```bash
bun run check
bun run build
bun run db:reset:local

# Terminal 1
cd apps/api
bun run wrangler dev --local --var APP_ENV:local --port 8787

# Terminal 2
cd apps/web
bun run vite --host 127.0.0.1 --port 5184

# Browser automation used for this review
bun /tmp/opencode/review-graph.mjs
bun /tmp/opencode/interaction.mjs
bun /tmp/opencode/mobile-reduced.mjs
bun /tmp/opencode/edge-scan.mjs
```

The scripts use the installed system Chromium (`/usr/bin/chromium`) through the
globally installed Playwright package. Screenshots captured during review:

- `/tmp/opencode/graph-desktop.png`
- `/tmp/opencode/temporal-selected.png`
- `/tmp/opencode/graph-mobile.png`
- `/tmp/opencode/graph-reduced.png`
- `/tmp/opencode/edge-scan.png`

## Results

### Desktop viewport and graph scale — pass

- Chromium viewport: `1440 × 900`.
- The graph canvas occupies the complete viewport: `1440 × 900`.
- The graph loaded with `154 systems / 232 relations`.
- Initial graph readiness was approximately `3.1 s` after navigation in the
  first run and approximately `4.0–4.4 s` on subsequent runs.
- The screenshot shows the graph as the dominant surface, with compact floating
  search, controls, navigation filters, selection inspector, and legend.

### Force simulation and dragging — partial pass / blocker

- The force graph rendered and exposed `Pause forces`, `Resume forces`, and
  `Reheat` controls. Clicking pause changed the button to `Resume forces` and
  status to `Forces paused · navigation active`; clicking Reheat changed status
  to `Forces settling…`.
- Drag attempts over rendered node locations reheated the simulation and updated
  the status, which confirms the drag/reheat path is reachable.
- A page exception was reproduced during the interaction run:

  ```text
  TypeError: Cannot read properties of undefined (reading 'x')
  ```

  It occurred while repeatedly dragging/clicking the WebGL graph. The exception
  did not prevent the page from continuing in that run, but it is a runtime UX
  reliability defect and needs investigation before sign-off.

### 2D / 3D toggle — pass

- Initial state: 2D `aria-pressed="true"`, 3D `aria-pressed="false"`.
- Clicking 3D changed the state to 2D `false`, 3D `true` and changed the hint
  to `Drag a node to reshape its neighborhood. Drag space to orbit.`.
- Returning to 2D restored the 2D pressed state and camera behavior.

### Search, including Temporal — pass with metadata blocker

- Searching `Temporal` produced one result, selected the Temporal node, showed
  the Data navigation group, and enabled Focus.
- The selected Temporal inspector reported one visible relation.
- The catalog drawer reported all `154 systems` and included Temporal.
- The selected Temporal card initially displayed `Card scope loading on demand`.
  The page also displayed `System summaries unavailable. Search by name or open
  a card for its actual scope.` with a Retry summaries action.
- Direct API checks show the pagination response does not advance:

  ```text
  /api/systems?limit=100&offset=0   => 100, firecracker … redis
  /api/systems?limit=100&offset=100 => 100, firecracker … redis
  /api/systems?limit=100&offset=200 => 100, firecracker … redis
  ```

  Because `loadAllSystems()` correctly requests offsets `0`, `100`, … and
  deduplicates by ID, it stops after the repeated page guard and shows the
  metadata-unavailable notice. This is a reproducible integration blocker for
  complete search metadata and card summaries, although graph-node-name search
  remains usable.

### Domain filter — pass

- The Data navigation group reduced the graph to `34 systems / 52 relations`.
- Temporal remained present in the filtered catalog/search view.
- The UI copy correctly describes navigation groups as broad categories rather
  than evidence-backed card scope.

### Model filter — blocker

- No model filter is exposed in the graph UI; only Navigation group/domain and
  Relation type selects are present.
- `GET /api/graph/models` returns `404 Not Found` in the reviewed local API.
- The requested model-filter scenario therefore could not be exercised.

### Edge selection — blocker / not verified

- The UI implements a link click handler and distinguishes Typed relation from
  Legacy association in the inspector.
- The scripted canvas hit sweep did not select an edge at any tested point, so
  relation inspector rendering, evidence text, and source-card navigation were
  not verified interactively. The current graph is dense and WebGL hit targets
  are difficult to target reliably at the initial fit; a reproducible test hook,
  larger link hit area, or an accessible relation list would make this review
  possible.
- The same sweep produced no additional page exception once the page was loaded
  with both local servers available.

### Drawer Escape and focus — pass

- Opening Browse systems created a modal dialog containing all `154` catalog
  items.
- Escape closed the catalog and restored focus to `#catalog-open`.
- Escape also closed the Help dialog and restored focus to `#help-open`.
- The catalog drawer is keyboard-oriented and exposes ordinary buttons for Read
  card and Locate on graph.

### Mobile viewport — pass

- Chromium viewport: `390 × 844`.
- Graph remained full viewport (`390 × 844`) with no horizontal/vertical body
  scroll (`scrollWidth=390`, `scrollHeight=844`).
- Top bar measured `366 × 58` at `(12,12)`; controls and filters fit without
  horizontal overflow. Footer/legend remained visible at the bottom.
- Mobile screenshot: `/tmp/opencode/graph-mobile.png`.

### Reduced motion — pass with visual/performance caveat

- With Playwright `reducedMotion: 'reduce'`, the graph initialized paused and
  exposed `Resume forces`; status was `Forces paused · navigation active`.
- No page errors or console errors were observed in the dedicated reduced-motion
  run.
- WebGL emitted GPU stall warnings in normal runs, and one interaction run
  emitted `CONTEXT_LOST_WEBGL: loseContext: context lost`. These are Chromium
  software/WebGL test-environment warnings, but the context-loss warning is
  worth monitoring for lower-powered/mobile devices.

### Console/network timing — partial pass

- No failed requests or console errors occurred in the successful desktop,
  mobile, and reduced-motion runs.
- The first successful graph page run took approximately `3.1 s` to reach the
  loaded graph; later responsive runs took approximately `4.0–4.4 s`.
- `bun run build` passed, but Vite reported a `1,425.04 kB` minified JS chunk
  (`389.15 kB` gzip), above the default 500 kB warning threshold. This is a
  material first-load/performance concern for a graph-first mobile surface.
- WebGL GPU stall warnings were observed while screenshotting/interacting:
  `GPU stall due to ReadPixels`. No ordinary JavaScript console errors were
  recorded in the clean runs.

## Blockers for acceptance

1. Fix the reproducible `TypeError: Cannot read properties of undefined
   (reading 'x')` during graph interaction/drag.
2. Fix `/api/systems` pagination so offsets advance; currently the UI cannot
   load complete summaries and shows a metadata-unavailable notice.
3. Provide the requested model filter and its data/API contract, or document a
   deliberate replacement before acceptance.
4. Make edge selection reliably testable/usable at this density; the current
   WebGL hit sweep could not open the relation inspector.

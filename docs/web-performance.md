# Web graph loading evidence

The browser entry point keeps `3d-force-graph` out of the initial application
chunk. `apps/web/src/main.ts` imports only its TypeScript instance type
statically; the runtime constructor is loaded by a Vite dynamic import after
the graph payload request starts. The graph chunk and graph payload therefore
download in parallel instead of forming a request waterfall. `lazyModule` also
shares an in-flight request, so a graph retry or mode switch cannot instantiate
two graph loaders at the same time. A rejected chunk load clears the cached
promise and remains retryable.

## Verification

Run from the repository root:

```sh
bun run check:web
bun test apps/web/src/*.test.ts
bun run build
```

The build should emit a small entry chunk and a separate chunk whose filename
contains `3d-force-graph`. Record the generated `dist/assets` sizes in review
notes; do not treat a local build size as a universal performance guarantee.
The initial HTML shell and data request can render before the graph runtime is
downloaded, while graph interaction waits for that chunk.

The October 24, 2026 local production build emitted:

- entry JavaScript: 48.11 kB (17.24 kB gzip)
- `3d-force-graph` chunk: 1,388.69 kB (377.26 kB gzip)
- production preview Lighthouse: performance 1.00, accessibility 1.00,
  first contentful paint 1.1 s, largest contentful paint 1.3 s, total blocking
  time 0 ms, and 23 KiB transferred before the graph API response

The Lighthouse run used `lighthouse http://127.0.0.1:4174/` against a local
`vite preview` server with headless Chromium. It is a repeatable smoke
measurement, not a field-user baseline; API latency, browser cache state, GPU,
and device class materially change graph startup.

The optimization changes loading boundaries only. It does not claim that the
force simulation, WebGL renderer, or network request has a fixed latency across
devices and deployments.

## Reproducible report harness

The repository includes `scripts/web_performance_report.ts`, which records the
production asset sizes (raw and gzip) and can optionally include a Lighthouse
JSON export. It deliberately labels these as local smoke evidence and marks
representative mobile hardware evidence unavailable unless a separately
recorded device run is supplied.

```sh
bun run build
bun scripts/web_performance_report.ts \
  --dist apps/web/dist \
  --output docs/web-performance-report.md

# Optional local preview smoke run:
lighthouse http://127.0.0.1:4174/ \
  --output=json \
  --output-path=/tmp/opencode/mathen-lighthouse.json
bun scripts/web_performance_report.ts \
  --dist apps/web/dist \
  --lighthouse-json=/tmp/opencode/mathen-lighthouse.json \
  --output docs/web-performance-report.md
```

Do not substitute local desktop or headless-Chromium values for mobile
evidence. A representative mobile trace must identify the device, browser,
network profile, build, URL, and workload.

## API-backed acceptance and optional browser trace

`scripts/web_acceptance.ts` is the reproducible acceptance harness for the
graph entry point. It always checks `/api/access/config`, `/api/graph`, and
`/api/graph/models` against a running API-backed preview. It writes a report
whose entries distinguish executed checks from checks that were not run.

Start the local API and web preview from separate terminals, then run the
API-backed checks:

```sh
bun run db:reset:local
(cd apps/api && bun run dev -- --port 8787)
(cd apps/web && bun run dev -- --port 5173)
bun scripts/web_acceptance.ts \
  --base-url http://127.0.0.1:5173/ \
  --output docs/web-acceptance-report.md
```

If API access protection is enabled, provide the configured service token with
`--api-token` or `MATHEN_API_ACCESS_TOKEN`. The script does not bypass
Turnstile or synthesize a browser session.

Browser checks are opt-in because Playwright and its browser binaries are not
project dependencies. When an operator has an installed Playwright module and
Chromium, add `--browser` and a trace path. The module can be supplied
explicitly with `--browser-module`:

```sh
bun scripts/web_acceptance.ts \
  --base-url http://127.0.0.1:5173/ \
  --browser \
  --browser-module /absolute/path/to/playwright/index.mjs \
  --trace /tmp/opencode/mathen-web-acceptance.zip \
  --output docs/web-acceptance-report.md
```

The opt-in browser run verifies the lazy graph chunk request, Systems and Math
models mode transitions, the catalog Escape/focus restoration path, the `/`
search shortcut, and keyboard search/selection. Add `--drag`, `--pan`, and/or
`--orbit` to execute real mouse pointer paths for 2D node drag, 2D background
pan, and 3D orbit respectively:

```sh
bun scripts/web_acceptance.ts \
  --base-url http://127.0.0.1:5173/ \
  --browser --drag --pan --orbit \
  --browser-module /absolute/path/to/playwright/index.mjs \
  --trace /tmp/opencode/mathen-web-acceptance.zip
```

Each requested path is reported `passed` only after the browser observes its
complete pointerdown/move/up sequence on the graph canvas. Unrequested paths
are `not-run`; a missing browser run never becomes a pass. The report includes
trace metadata (browser, headless mode, viewport, and path). This does not
claim that a mouse path hit a graph node, moved a node, or proves touch/pinch
behavior. Real mobile-device and touch evidence remains external and must name
the device, browser, viewport, execution, build, URL, and workload.

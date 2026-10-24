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

# MTH-0207 — VectoJS bounded evidence report

**Status:** research-only · non-canonical · review-required · promotion-not-determined
**Fixed commits:** `vectojs@906d4f466e1e2d3436df8593e59a35241ef9db5a` · `vectojs-docs@661671ef3d4f9a33c25c4bcae99ae04e9fabe872`

## Scope and method

This report analyzes only the VectoJS core package and authoritative framework/core documentation at the fixed commits above. Included paths are `packages/core/src/**` in `vectojs` and the framework/core material under `content/learn/**` and `content/reference/**` in `vectojs-docs`, with the specific files listed below.

Gallery, website, native forge applications, skills, motif, and other sibling repositories are out of scope and were not used as evidence. API/MCP, migrations, production deployment, and paper analysis are also out of scope. No canonical card, relation, API, or MCP artifact is changed by this research.

Evidence excerpts were captured from pinned Git blobs. The JSON companion records SHA-256 digests for each cited source file. A source statement is labeled **fact**; a synthesis is labeled **inference**; an open modeling question is labeled **hypothesis**; and a structural comparison is labeled **analogy**.

## Findings

### 1. Canvas Runtime and Virtual Math Tree — fact

`Entity` is a retained scene-graph node with `parent`/`children`, local transform properties, a six-scalar world-transform cache, and an optional resident WASM store slot (`packages/core/src/tree/Entity.ts:804-872`). The VMT runtime documentation describes a causal pipeline from dirty propagation through transform gathering, layout/hit testing, culling, render traversal, and a11y synchronization, ending in pixels plus DOM mirrors (`content/learn/deep-dive/06-vmt-runtime.md:7-54`).

The source therefore supports a retained numeric tree as the core runtime abstraction. It does not by itself establish a complete formal semantics for all update ordering, cache paths, or backend equivalence.

### 2. Mathematical structures — fact, then bounded inference

Core defines `AffineTransform { a, b, c, d, e, f }` and local `Bounds` used for viewport culling (`packages/core/src/tree/Entity.ts:32-52`). The math foundations document gives the corresponding homogeneous affine matrix, parent-times-local composition, scalar traversal, and closed-form inverse with determinant check (`content/learn/math-foundations.md:72-114`).

**Fact:** affine composition and inverse are explicit in source/docs.
**Inference:** the runtime can be modeled as affine state carried over a rooted entity tree.
**Limitation:** this is not a proof that all renderer, WASM, hit-test, and projection paths are numerically identical.

### 3. Semantic and accessibility projection — fact

The a11y manager collects projected elements, records region membership, tracks active IDs for pruning, and reorders normal elements by visual reading order (`packages/core/src/tree/scene/A11yProjectionManager.ts:80-210`). The docs describe a transparent `a11yRoot`, native tags/ARIA state, visual-order tab traversal, composite widget nesting, and a shared depth-first synchronization walk (`content/learn/deep-dive/03-semantic-projection.md:7-73`; `content/learn/runtime-architecture.md:9-59`).

`a11yProjection` has `eager`, `onDemand`, and `never` modes. The source documents focus/pointer-target/explicit-request engagement for `onDemand`, and states that projected mirrors are the pointer dispatch route while `findEntityAt` is a query API (`packages/core/src/tree/Entity.ts:944-990`). This is a source contract; it was not independently tested here.

### 4. Content projection — fact

`ContentProjection` exposes logical text plus optional line/run geometry, selection flags, and a retained grid plan. `ContentProjectionHint` is advisory: an entity may build more than the requested band, but should not omit source text needed for find-in-page, copy, or assistive technology (`packages/core/src/tree/Entity.ts:88-185`). The core renderer reference describes the hook as producing a transparent, position-synchronized, viewport-lazy, dirty-checked DOM representation (`content/reference/core-renderer.md:139-176`).

### 5. Visibility and materialization — fact; separation inference

The authoritative projection documentation distinguishes:

| Tier | Materialization | Gate |
| --- | --- | --- |
| Visual | Canvas2D/WebGL/WebGPU/SVG pixels | culling and render traversal |
| Semantic/coarse | one DOM node holding block text | `contentSemanticMargin` |
| Interaction/fine | line/cell carriers and a11y mirrors | `contentProjectionMargin` and line windows |

The same documentation states that `contentSemanticBudget` spreads coarse materialization across syncs, while an infinite interaction margin can materialize all carriers and reach O(total document glyphs) (`content/learn/deep-dive/03-semantic-projection.md:19-62,79-100`). Scene reference options repeat the independent margins and budget (`content/reference/core-scene.md:47-53,100-140`).

**Inference:** visual visibility and semantic materialization are separate state dimensions. A retained VMT node can remain the logical source while a projection is released or deferred; a coarse text node can remain while fine carriers are windowed. This is a bounded architectural reading, not a formal state-machine proof.

### 6. WebGL backend — fact

`WebGLPointRenderer` describes a GPU layer for batched circles, rectangles, sprites, and glyphs, and `createWebGLPointRenderer` returns `null` when WebGL2 or shader setup is unavailable (`packages/core/src/renderer/WebGLPointRenderer.ts:1-80,671-709`). The core renderer reference documents one WebGL2 canvas with batched programs and fallback to the normal renderer for primitives whose transforms cannot be represented exactly (`content/reference/core-renderer.md:369-419`).

The Scene options documentation records that the WebGL layer is stacked over the 2D canvas, so cross-layer painter order does not interleave (`content/reference/core-scene.md:38-41`). This is an important limitation when interpreting “same scene” backend claims.

### 7. WebGPU backend — fact

`WebGPUParticleSystemManager` creates compute/render pipelines and bind groups, allocates storage and uniform buffers per particle entity, dispatches `ceil(maxParticles / 256)` workgroups, and records six vertices per particle instance (`packages/core/src/renderer/WebGPUParticleSystemManager.ts:204-320,322-409`). Scene reference documentation describes `particleBackend: auto | webgpu | cpu`, with CPU fallback when WebGPU initialization fails (`content/reference/core-scene.md:38-41`).

The evidence supports a compute-to-render particle path and an explicit fallback policy. It does not establish a benchmark result, universal GPU availability, or superiority over Canvas2D/WebGL.

### 8. Backend and projection contracts — fact; invariant candidate as inference

`ProjectionPolicy` defines `canvas`, `dom`, and `auto`, with capability rows, fallback reasons, no-DOM short-circuiting, and hysteresis voting (`packages/core/src/tree/scene/ProjectionPolicy.ts:1-20,38-70,230-326`). `ProjectionBackend` defines `mount`, `update(node, worldMatrix)`, and `unmount`, and explicitly names canvas, DOM, a11y, and content representations (`packages/core/src/tree/scene/ProjectionBackend.ts:3-65`).

**Fact:** these contracts exist in core source.
**Inference:** agreement on world geometry, visibility, and lifecycle is a candidate cross-projection invariant.
**Limitation:** this report does not verify the invariant across every backend or policy transition.

## Candidate mathematical views

1. **Affine transformation composition over a rooted entity tree** — asks how local state composes to world state and how singularity affects inverse queries. Evidence: `Entity.ts:32-52`, `math-foundations.md:72-114`. Claim type: inference.
2. **Tiered partial materialization over a retained scene tree** — asks which visual, semantic, and interaction representations exist under viewport and engagement policy. Evidence: `03-semantic-projection.md:19-62`, `Entity.ts:88-185`, `ProjectionPolicy.ts:230-326`. Claim type: hypothesis.

These are candidate views, not proofs or canonical mathematical models.

## Candidate relationships

- **Analogy, candidate-only:** retained entity tree plus partial visual/semantic materializations may be structurally comparable to systems that separate logical state from materialized views. No target system was inspected, so this asserts no relation, influence, or superiority.
- **Hypothesis, candidate-only:** a shared affine geometry contract may be tested in future work as a way to reduce visual/semantic projection drift. This report does not establish sufficiency or implementation-wide conformance.

## Limitations and review guardrails

- Documentation measurements are quoted as documentation evidence; no browser, GPU, or accessibility experiment was run.
- Source comments describe intended behavior and are not independent runtime verification.
- No historical influence or superiority is inferred from common terms or structural resemblance.
- The JSON and this report are research artifacts only. They are non-canonical, review-required, and promotion-not-determined.
- Promotion to `data/systems`, creation of relations, or publication through API/MCP is outside this task and was not performed.

## Evidence index

The machine-readable evidence index, including commit IDs, exact source paths, line ranges, excerpts, and SHA-256 digests, is in `data/analyses/external/mth-0207-vectojs.json`.

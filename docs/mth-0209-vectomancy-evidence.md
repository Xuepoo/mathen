# MTH-0209 Vectomancy evidence

## Boundary

This is a research-only, non-canonical record for Vectomancy at fixed commit
`6615ffd656cdc2f21b4480a60473dc80d050e530`. The source repository was inspected
read-only. The companion JSON contains evidence IDs, source digests, claim
types, scope, provenance, limitations, candidate relationships, and review
status.

The report does not promote a card, create a relation, or establish general
performance or mathematical correctness. Every interpretation is separated from
direct source facts as `inference`, `hypothesis`, or `analogy`.

## CLI decomposition

`README.md:62-100` and `cli/src/cli.rs:45-311` define `image`, feature-gated
`video`, `text`, and `render` subcommands. Image accepts files/directories and
selects `fourier`, `spline`, or `chaikin`; render reads a JSON
`MathExpressionAST`. `cli/src/main.rs:42-55` loads configuration and rejects a
missing subcommand.

The image branch accepts PNG/JPG/JPEG/SVG at the CLI boundary, while the parser
facade also handles WEBP (`src/parser/mod.rs:10-36`). Raster inputs become
`ParserOutput::Paths`; SVG inputs become `ParserOutput::Segments`. The branch
then applies path filtering/simplification and selects a tagged AST variant.

## Image and vector pipelines

The raster crate (`crates/vectomancy-raster/src/lib.rs:349-451`) implements this
observed sequence:

1. Decode image bytes and record dimensions.
2. Convert to luminance.
3. Compute horizontal and vertical Sobel responses in parallel and combine their
   magnitudes.
4. Apply Otsu thresholding.
5. Thin the binary grid with Zhang-Suen iterations.
6. Trace endpoint paths and remaining closed/isolated components.
7. Optionally average RGB samples along each path.

The SVG parser (`src/parser/vector.rs:18-157`) uses `usvg`, traverses nested
groups and path nodes, maps absolute transforms, preserves line/quadratic/cubic
and close segments, and optionally converts stroke/fill colors to normalized
RGB. The workspace SVG crate has the corresponding memory/file boundary at
`crates/vectomancy-svg/src/lib.rs:13-140`.

These are facts about implemented stages. They do not establish that skeleton
extraction is complete, that branch traversal is globally optimal, or that
output geometry is visually faithful for arbitrary inputs.

## Text pipeline

`text/src/parser.rs:5-168` accepts font bytes, converts WOFF2 to TTF when
detected, scales outlines, applies kerning and letter spacing, handles escaped
newlines and control characters, supplies a fallback glyph for missing
characters, and emits `BezierSegment` paths with calculated dimensions.

`cli/src/main.rs:934-1131` requires a font from `--font` or text config, builds
spline equations, and defaults to `text_output.json`. It also accepts solid
hex color or a three-part gradient specification. The CLI test at
`cli/tests/cli_tests.rs:74-117` uses the checked-in fixture font and asserts a
successful non-empty output file. That test does not validate the geometry or
font coverage.

## Video pipeline

`video/src/lib.rs:169-246` initializes FFmpeg, selects the best video stream,
decodes on a spawned thread, clones frames into a bounded channel, and converts
frames to RGB24 using `sws_scale` (`video/src/lib.rs:57-147`). The CLI receives
frames in order, batches up to `num_threads.clamp(1, 8)`, and processes each
frame in scoped worker threads (`cli/src/main.rs:633-855`). Each worker runs the
raster/math path and emits `frame_%04d.<ext>`.

If the requested video output has a video extension, the CLI stages PNG frames
in a temporary directory and invokes external `ffmpeg` at 30 fps
(`cli/src/main.rs:864-930`). GIF uses palette filters; WebM uses VP9 and may
use alpha; other listed containers use H.264. Audio is probed and, except for
GIF, mapped to AAC with `-shortest` when present. These source-level contracts
do not prove codec availability, successful execution, throughput, or audio
synchronization.

## Mathematics and representation changes

### Simplification and path ordering

The Ramer-Douglas-Peucker implementation (`src/math/mod.rs:30-60`) recursively
uses perpendicular distance to an epsilon threshold. SVG Fourier preparation
samples segment data at 100 points and calls a KD-tree nearest-neighbor walk
followed by bounded 2-opt reversals (`cli/src/main.rs:339-360`,
`crates/vectomancy-transform/src/tsp.rs:5-72`). This is a heuristic ordering
procedure; no global TSP optimality is claimed.

### Fourier / FFT

`src/math/mod.rs:201-320` and `crates/vectomancy-transform/src/fourier.rs:10-79`
map points to complex values, run a forward FFT, derive amplitude, signed
frequency, and phase, sort by amplitude, and optionally select terms by
accumulated squared amplitude. Adaptive selection retains the DC component and
stops at the configured energy target or term cap. Non-adaptive selection drops
terms at or below amplitude `0.001` and takes the cap.

The model contract is `FourierTerm { amplitude, frequency, phase }`.
`templates/python.tera` and the emitter lower these terms to cosine/sine sums;
the Desmos template uses a parameter domain from `0` to approximately `2π`.
The code and tests establish the representation and selection algorithm, not a
formal Fourier approximation guarantee or reconstruction correctness.

### Splines

`crates/vectomancy-transform/src/spline.rs:4-170` lowers line, quadratic, cubic,
and close segments to `SplineEquation` polynomial coefficients with
`start_t`/`end_t`. Simplification rounds coefficients to four decimal places.
The transform test checks that a MoveTo/LineTo pair yields one equation. This
is local behavior evidence, not a proof of continuity, exactness after
rounding, or general numerical correctness.

### Chaikin

`crates/vectomancy-geometry/src/algorithms/chaikin.rs:3-61` and
`src/math/mod.rs:323-352` use the explicit `0.75/0.25` and `0.25/0.75`
corner-cutting points. Closed and open polylines have separate handling; the
facade preserves endpoints for open paths. A geometry test checks one case.
The test and formulas do not justify broad claims about smoothing quality or
mathematical correctness.

## AST, data encoding, and outputs

`src/models/mod.rs:454-488` defines a tagged JSON enum:

- `Fourier { strokes: Vec<ColoredPath<Vec<FourierTerm>>>, bounding_box }`;
- `Spline { equations: Vec<ColoredPath<Vec<SplineEquation>>>, bounding_box }`;
- `Polyline { paths: Vec<ColoredPath<Vec<Point2D>>>, bounding_box }`.

`ColoredPath` serializes its optional color style under `color_rgb`. The model
deserializer supports solid colors and current/legacy gradients and sanitizes
non-finite color values. Before output, `src/emitter/mod.rs:18-137` rejects
non-finite coordinates, coefficients, Fourier fields, colors, invalid bounding
boxes, and overlapping or reversed spline intervals.

JSON output is pretty-printed AST. Script output serializes the selected data,
compresses JSON with zlib, and Base64-encodes it
(`src/emitter/mod.rs:395-407`, `crates/vectomancy-export/src/lib.rs:8-21`).
Python decodes and plots the payload; HTML uses Canvas; Desmos emits parametric
expressions and loads them in batches of 50. SVG has a dedicated emitter path.
The exporter test decodes a zlib/Base64 payload and checks the original JSON,
while CLI tests check that image/text JSON files are created and non-empty.
External script execution is not established by these tests.

## CPU, GPU, and threading

The CLI constructs a global Rayon pool from `--threads` or config, clamps a
nonzero value to available parallelism, and treats zero as all available cores
(`cli/src/main.rs:87-105`). Raster Sobel and path work use Rayon. Batch CPU FFT
uses `par_iter` (`src/math/mod.rs:410-423`).

The GPU path is feature-gated and uses a cached `wgpu` context with compute
pipelines (`src/math/wgpu_math.rs:23-128`). It uses a power-of-two buffer,
interpolates input samples, dispatches bit-reversal and butterfly stages, and
maps results back (`src/math/wgpu_math.rs:131-327`). The math facade warns and
falls back to CPU if GPU FFT fails (`src/math/mod.rs:208-246`). Native image
rendering has a separate cached wgpu render context
(`src/emitter/native.rs:17-104`).

README/manual prose mentions speed and CPU/GPU equivalence. This artifact does
not promote those statements to facts: the inspected tests contain no
reproducible general benchmark establishing them.

## Configuration and output selection

`src/config.rs:27-109` defines image, video, and text TOML sections. `Config::load`
uses an explicit `--config` path first, otherwise the platform config directory
for `vectomancy`, and returns defaults on missing/unreadable/invalid files.
CLI values generally override section values. Video falls back to image config
for selected fields (`cli/src/main.rs:532-599`).

Image output format chooses extensions (`png`, `jpg`, `webp`, `py`, `html`,
`json`, `svg`) and uses a supplied file path only for a single input; otherwise
it creates an output directory and derives `<stem>_vectomancy.<ext>`
(`cli/src/main.rs:432-460`). Text infers format from output extension and uses
`text_output.json` by default. Render infers source dimensions from the AST
bounding box and defaults to a sibling output with the selected extension.

The configuration guide documents a precedence hierarchy and parameter set, but
its complete example includes unsectioned keys while the inspected Rust config
struct exposes `image`, `video`, and `text` sections. The report preserves this
as a documented-vs-implemented limitation instead of silently treating the
example as executable contract.

## Claim and review status

The JSON record separates direct `fact` evidence from `inference`, `hypothesis`,
and `analogy`. One analogy compares the AST boundary structurally to a compiler
intermediate representation; it does not claim compiler lineage or influence.
One research hypothesis proposes Vectomancy as a candidate mathematical
neighborhood example. It remains a candidate and must not be written to
relations or canonical cards from this artifact.

Status: **research-only**, **non-canonical**, **review-required**,
**promotion-not-determined**.

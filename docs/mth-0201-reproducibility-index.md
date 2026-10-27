# MTH-0201 research reproducibility index

MTH-0201 is a deterministic, research-only index of the current Architecture
Exploration Methodology evidence wave. The machine-readable package is
[`data/reproducibility/mth-0201-reproducibility-index.json`](../data/reproducibility/mth-0201-reproducibility-index.json).
Its contract and builder are
[`schemas/reproducibility-index.schema.json`](../schemas/reproducibility-index.schema.json)
and
[`scripts/build_mth0201_reproducibility_index.py`](../scripts/build_mth0201_reproducibility_index.py).

## Coverage and digest policy

The index covers MTH-0169, MTH-0172, MTH-0174, MTH-0175, MTH-0176, MTH-0177,
MTH-0178, MTH-0185, MTH-0186, MTH-0187, MTH-0188, MTH-0193, MTH-0194,
MTH-0195, MTH-0196, MTH-0197, and MTH-0198. Every expected path is recorded
with a raw-byte SHA-256 digest when it is present on the baseline. Historical
or superseded artifacts absent from the baseline remain explicit `not-present`
or `partial` records; they are not reconstructed from old commits.

MTH-0196 is represented by the checked-in statistical and agent-review scoring
artifacts rather than a duplicate artifact. The index also records exact
available regeneration, validation, test, and audit commands for each item.
Commands marked unavailable explain why they cannot be run from this baseline.

## Reproducibility and interpretation boundary

The builder is offline and deterministic. It records environment assumptions,
whether a result is measured, observed, not measured, not evaluated, or only
protocol-defined, and the limitations written by each evidence surface. The
index itself is `research_only: true`, `canonical: false`, and
`promotion_decision: "not-determined"`.

Agent records retain `human_review: false`; no human stratum is synthesized.
Where the underlying contract has a human stratum, it remains explicitly empty
and `not-evaluated`. Direct-LLM conditions remain `not-evaluated` unless the
required exact provider, model, prompt/input digests, runtime provenance, and
secret-safe output are present. SQLite observations remain detached,
`canonical: false`, and under review. No promotion, inference, or claim of
generalization is made by this package.

## Regeneration and validation

```bash
uv run python scripts/build_mth0201_reproducibility_index.py
uv run python scripts/build_mth0201_reproducibility_index.py \
  --validate data/reproducibility/mth-0201-reproducibility-index.json
PYTHONPATH=src uv run python -m unittest \
  tests.test_mth0201_reproducibility_index -v
uv run ruff format --check scripts/build_mth0201_reproducibility_index.py \
  tests/test_mth0201_reproducibility_index.py
uv run ruff check scripts/build_mth0201_reproducibility_index.py \
  tests/test_mth0201_reproducibility_index.py
```

Regenerating an underlying observation that records wall-clock timing creates a
new observation; it must not silently replace the checked-in result. The
MTH-0198 browser and Lighthouse commands additionally require local services,
system Chromium, and a production preview.

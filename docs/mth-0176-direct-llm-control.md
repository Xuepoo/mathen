# MTH-0176 direct-LLM control boundary

This artifact defines a research-only control record for comparing a direct
LLM architecture-design path with evidence-bounded methods. It is a manifest
and validator, not an LLM adapter or an experiment result. The implementation
is isolated in `scripts/direct_llm_control.py` and
`schemas/direct-llm-control.schema.json`.

## Required provenance

Every record retains:

- the exact provider name and exact model identifier;
- a digest of the rendered prompt and the input/evidence bundle;
- runtime kind/version, runner version, source revision, and execution
  environment;
- the integer seed and complete decoding-parameter object; and
- output status, digest when output exists, record count, and an explicit
  `secret_safe: true` assertion.

The manifest never accepts API keys, authorization material, passwords,
tokens, or other secret-bearing fields. Raw prompts and outputs are not stored
by this boundary. Digests are `sha256:` values over canonical bytes.

## Evidence and result boundary

Candidate records are optional. When present, each candidate and claim must
cite non-empty evidence IDs from the input bundle; claim types are explicitly
`fact`, `inference`, `hypothesis`, or `analogy`. Candidates always carry
`proven: false`. These records do not establish truth, compatibility,
causality, originality, or historical influence.

The result boundary requires `canonical: false`, human review before
promotion, and `storage_scope: research` or `draft`. No API, MCP, D1
migration, relation, canonical card, or existing benchmark status is changed.

## Safe dry-run

No local model/runtime is assumed. The runner therefore provides a dry-run
that performs no network request and writes a valid `not-evaluated` manifest
with no candidates and an absent output:

```bash
uv run python scripts/direct_llm_control.py dry-run \
  --provider unavailable \
  --model unavailable \
  --output data/benchmark/mth-0176-direct-llm-control.json

uv run python scripts/direct_llm_control.py validate \
  data/benchmark/mth-0176-direct-llm-control.json
```

If a prompt or fixed input bundle is available, pass each path to `--prompt`
or `--input-bundle`; only its digest is recorded. This command still does not
invoke a model. A future local runner may produce an evaluated manifest only
when exact provider/model, runtime provenance, prompt/input digests, sampling
parameters, a secret-safe output digest, and evidence-local candidate records
are all available. Missing required output/provenance remains
`not-evaluated`, rather than a fabricated result.

## Validation rules

The validator rejects unknown fields, malformed digests, duplicate IDs,
non-local evidence, absent output marked as evaluated, output without a digest,
proven candidates, canonical boundaries, and secret-bearing fields. It is
intentionally independent of production APIs and does not mutate canonical
data.

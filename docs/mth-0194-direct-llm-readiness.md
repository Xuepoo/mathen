# MTH-0194 direct-LLM local readiness

`data/analyses/mth-0194-direct-llm-readiness.json` is a research-only,
not-evaluated control record. It answers only whether an approved local
direct-LLM runtime was ready to run; it does not run inference or claim that a
model is absent from the machine.

The bounded inspector, `scripts/direct_llm_readiness.py`, checks a fixed list
of local executable names, Python module availability, matching process names,
candidate systemd unit state, and aggregate metadata for common model-cache and
configuration locations. It does **not** read environment or configuration
values, record paths or model
identifiers, load a module, invoke an inference executable, contact an
endpoint, or use `Mathen API_ACCESS_TOKEN` as an LLM credential. Environment
variable names are recorded only as inspection metadata; secret values are
never read into the artifact.

The audit found no approved local runtime: the checked serving executables and
Python inference modules were unavailable, no matching inference process was
observed, and candidate service units were inactive. A Hugging Face cache was
present, but cache presence is not runtime approval and no model identifier is
recorded. Provider and exact model are therefore `null`; prompt and output
are not rendered or stored; all readiness metrics are `null`.

Reproduce the inspection from the repository root with:

```bash
uv run python scripts/direct_llm_readiness.py inspect \
  --root . \
  --output data/analyses/mth-0194-direct-llm-readiness.json
uv run python scripts/direct_llm_readiness.py validate \
  data/analyses/mth-0194-direct-llm-readiness.json
```

The record is not canonical, remains in research scope, and requires human
review before any future promotion. A future evaluated control must add an
explicitly approved provider/runtime, exact model provenance, prompt and
output digests, and reviewed evidence; this artifact does not authorize that
execution.

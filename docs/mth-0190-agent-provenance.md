# MTH-0190 bounded agent provenance

The MTH-0180, MTH-0181, MTH-0186, and MTH-0187 agent-review pilot records, the
MTH-0183 collected observations, and MTH-0188 scoring metadata retain the
following explicit bounded provenance:

```json
{
  "execution_actor": "llm-based-agent",
  "provider": "not-recorded",
  "model": "not-recorded"
}
```

These fields describe the executing LLM-based agent only. Provider and model
runtime provenance was not recorded. They do not relabel any record as a
specific provider/model and do not imply a model run. The direct-LLM MTH-0182
record remains a separate `model-run` with status `not-evaluated`.

All historical labels, candidate/evidence/source/negative-knowledge digests,
observed timing, agent-pilot-only agreement, and promotion boundaries remain
unchanged. The deterministic builders write these fields and validate them on
every regeneration.

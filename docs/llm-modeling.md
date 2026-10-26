# LLM-assisted modeling

Mathen's LLM adapter turns a fixed-commit modeling bundle into an unreviewed
Architecture Card draft. It is provider-neutral: the adapter uses the Python
standard-library `urllib` client and the OpenAI Chat Completions request shape,
so it can target compatible local or hosted services.

Mathen treats the LLM as a broad research instrument rather than an autonomous
architecture authority. The human–LLM complement, cross-community search
questions, and planned evaluation criteria are documented in
[`research-instrument.md`](research-instrument.md).

## Workflow

Build deterministic bundles first, then run the model command:

```bash
uv run mathen prepare-modeling --write-prompts
uv run mathen model --system git
```

By default, outputs are written below `data/drafts/llm/`. Existing files are
protected; pass `--force` when intentionally regenerating a draft. The command
never writes to `data/systems/`, which contains reviewed canonical cards.

Before writing a file, the adapter requires that the response contains one JSON
object, the card ID matches the bundle's system ID, every referenced evidence
ID exists in the bundle, every returned evidence record exactly matches the
supplied record, and the card passes Mathen's semantic card validation. These
checks establish an evidence boundary, but they do not make generated claims
true. Human review remains required before promotion to `data/systems/`.

Each generated draft is accompanied by a `<system-id>.protocol.json` record.
This is an audit envelope, not a card and not evidence: it records the selected
provider, exact model identifier, pinned source revision, and SHA-256 digests of
the rendered prompt and input bundle. It never records API keys, authorization
headers, or raw secret-bearing configuration. The envelope starts with review
status `pending` and must be completed by a human reviewer before any deliberate
canonical promotion.

## Evidence-bounded research protocol

The modeling bundle's protocol version is `mth-0112-v1`. A run must preserve:

- **Provenance:** provider, exact model, prompt digest, evidence-bundle digest,
  source commit, and deterministic-inspector provenance. Deployment URLs are
  configuration, not research identity.
- **Candidate boundary:** features and mathematical views are candidate
  abstractions. Every claim keeps `claim_type` (`fact`, `inference`,
  `hypothesis`, or `analogy`), review status, and local `evidence_ids`.
- **Cross-domain analogies:** a resemblance must be labeled `analogy` and state
  the shared structure and its boundary. It must not imply equivalence,
  dependency, composition, substitutability, or historical influence without
  direct evidence.
- **Analogy mapping contract:** when a cross-domain comparison is useful, use
  the standalone versioned contract in
  [`schemas/cross-domain-analogy.schema.json`](../schemas/cross-domain-analogy.schema.json).
  It requires source/target concepts, mapping type and scale, shared and
  preserved properties, explicitly non-preserved properties, scope,
  counterexamples, local evidence, and an explicit non-equivalence statement.
- **Uncertainty and disagreement:** missing evidence is recorded as unknown or
  out of scope; conflicting evidence or reviewer disagreement is recorded in
  the protocol envelope rather than silently resolved by the model.
- **Human boundary:** automated output remains under `data/drafts/` and is never
  proof or canonical knowledge. Promotion to `data/systems/` is a deliberate
  human review operation.

The protocol evaluates batches along four separate dimensions: **breadth** of
the requested coverage, **citation quality** and locality, **error rate** (such
as unsupported or misclassified claims), and **reviewer usefulness** (whether
the draft reduces review effort without hiding uncertainty). These dimensions
should be reported separately against a reviewed reference or reviewer audit;
they are not collapsed into an ungrounded confidence score.

LLMs are broad structural-discovery instruments, not autonomous architecture
oracles. Humans provide problem reframing, curiosity, direction, and final
review; graphs and vectors expose candidate paths; an LLM retrieves, explains,
or proposes mappings; typed mathematical contracts and experiments validate
them. The typed composition contract preserves discovery method and provenance,
source/target communities and path, shared/preserved/weakened/unverified
properties, uncertainty, counterexamples, and disagreement. Vector similarity,
graph position, LLM interpretation, and validated relations remain separate
fields. Distant cross-community candidates are intentionally allowed, but stay
candidates with `proven: false` until validation.

## Configuration

The command accepts explicit flags or environment variables. Explicit flags
take precedence:

| Setting      | Flag         | Environment variable  |
| ------------ | ------------ | --------------------- |
| API key      | `--api-key`  | `OPENAI_API_KEY`      |
| Model name   | `--model`    | `MATHEN_LLM_MODEL`    |
| API base URL | `--base-url` | `MATHEN_LLM_BASE_URL` |

The default base URL is `https://api.openai.com/v1`. The request timeout can be
changed with `--timeout` and defaults to 120 seconds. Unit tests use a fake
completion client and never contact an external API.

## Selecting bundles and reviewing output

The optional positional argument selects a bundle file or directory:

```bash
uv run mathen model data/modeling --system sqlite --model gpt-4.1-mini
```

Inspect generated JSON, validate it explicitly, and review evidence and claim
types before promotion:

```bash
uv run mathen validate data/drafts/llm
```

Promotion is a deliberate review operation and is outside the automated model
command.

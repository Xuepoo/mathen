# LLM-assisted modeling

Mathen's LLM adapter turns a fixed-commit modeling bundle into an unreviewed
Architecture Card draft. It is provider-neutral: the adapter uses the Python
standard-library `urllib` client and the OpenAI Chat Completions request shape,
so it can target compatible local or hosted services.

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

## Configuration

The command accepts explicit flags or environment variables. Explicit flags
take precedence:

| Setting | Flag | Environment variable |
| --- | --- | --- |
| API key | `--api-key` | `OPENAI_API_KEY` |
| Model name | `--model` | `MATHEN_LLM_MODEL` |
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

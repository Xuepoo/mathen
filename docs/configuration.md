# Mathen CLI configuration

The Python package exposes the `mathen` command. It works against the checked-in
`data/` tree when run from a source checkout and uses per-user directories after
installation.

## Configuration locations

Mathen reads TOML from the following locations by default:

| Platform | Configuration                                                           | Data                                               | Cache                                         |
| -------- | ----------------------------------------------------------------------- | -------------------------------------------------- | --------------------------------------------- |
| Linux    | `$XDG_CONFIG_HOME/mathen/config.toml` or `~/.config/mathen/config.toml` | `$XDG_DATA_HOME/mathen` or `~/.local/share/mathen` | `$XDG_CACHE_HOME/mathen` or `~/.cache/mathen` |
| macOS    | `~/Library/Application Support/Mathen/config.toml`                      | `~/Library/Application Support/Mathen`             | `~/Library/Caches/Mathen`                     |
| Windows  | `%APPDATA%/mathen/config.toml`                                          | `%LOCALAPPDATA%/mathen`                            | `%LOCALAPPDATA%/mathen/cache`                 |

The `MATHEN_CONFIG`, `MATHEN_CONFIG_DIR`, `MATHEN_DATA_DIR`, and
`MATHEN_CACHE_DIR` environment variables provide explicit overrides. A config
path can also be selected with the global `--config` option.

## First-time setup

```bash
mathen version
mathen config init
mathen config show
mathen config path
```

The generated file contains paths and LLM settings. API keys are redacted by
`config show`; use environment variables for secrets when possible.

```bash
mathen config set llm.base_url https://api.openai.com/v1
mathen config set llm.model gpt-4.1-mini
mathen config set llm.api_key_env OPENAI_API_KEY
export OPENAI_API_KEY=...
mathen model --system git
```

An OpenAI-compatible provider can be selected with `llm.provider`. Provider
values override the corresponding top-level LLM defaults. The precedence for
model execution is explicit CLI flags, standard environment variables, the
selected provider, then the top-level TOML values:

```text
--api-key / --model / --base-url
MATHEN_LLM_BASE_URL, MATHEN_LLM_MODEL, OPENAI_API_KEY
[llm.providers.<name>], then [llm] in config.toml
```

Multiple OpenAI-compatible providers can be declared and selected with
`llm.provider`:

```toml
[llm]
provider = "local"

[llm.providers.openai]
base_url = "https://api.openai.com/v1"
model = "gpt-4.1-mini"
api_key_env = "OPENAI_API_KEY"

[llm.providers.local]
base_url = "http://localhost:11434/v1"
model = "qwen3"
api_key = "local"
```

Hosted MCP and reviewed-card synchronization can also be configured:

```toml
[mcp]
url = "https://mathen.example.com/api/mcp"
token_env = "MATHEN_API_TOKEN"

[sync]
source = "https://github.com/example/mathen/archive/refs/heads/main.tar.gz"
ref = "main"
```

Replace the example host and archive repository with your deployment and trusted
reviewed-card source. The default sync archive remains the upstream Mathen
repository's `main` archive; it is defined once by `SyncSettings` and reused by
the generated starter configuration. The MCP endpoint is unset by default, so
offline commands do not depend on a hosted deployment.

Non-empty `MATHEN_MCP_URL`, `MATHEN_SYNC_SOURCE`, and `MATHEN_SYNC_REF`
environment variables override the corresponding TOML values and built-in
defaults, including with `--no-config`. Blank values are ignored. Overrides are
runtime-only: `config init`, `config set`, and `config unset` do not persist
environment endpoint values. `sync.ref` is provenance metadata, not an archive
URL rewrite; when changing revisions, set both the source URL and ref.

```bash
export MATHEN_MCP_URL=https://mathen.example.com/api/mcp
export MATHEN_SYNC_SOURCE=https://cards.example.com/reviewed-v1.tar.gz
export MATHEN_SYNC_REF=v1
```

These URLs are public configuration, not credentials. Keep bearer tokens in
`MATHEN_API_TOKEN` (or the configured token environment variable), not in URLs.
The stdio MCP server separately uses `MATHEN_API_URL` for an API origin or `/api`
base URL and keeps filesystem mode when that variable is unset.

`mathen data sync` downloads only reviewed cards from the configured archive,
validates every card and cross-card reference, and replaces the configured card
directory atomically. It refuses to replace the repository's canonical
`data/systems` directory. `mathen data status` reports the card count, source,
digest, and whether the local copy still matches its synchronization metadata.
The synchronization archive is treated as untrusted input: unsafe paths,
duplicate card names, and oversized entries are rejected.

`mathen doctor` performs local-only diagnostics. It does not contact the LLM or
MCP endpoint, and it reports the selected provider without printing credentials.
Use `mathen mcp path` to inspect the endpoint and `mathen mcp check` to send an
authenticated JSON-RPC `initialize` request using `MATHEN_API_TOKEN` (or the
configured token environment variable).

## Available commands

```text
mathen validate [PATH]
mathen list [PATH]
mathen show CARD_ID [PATH]
mathen analyze [MANIFEST]
mathen prepare-modeling [MANIFEST]
mathen model [BUNDLE_DIR]
mathen relation-candidates [PATH]
mathen data {status,sync}
mathen mcp {path,check}
mathen doctor
mathen config {init,show,path,set,unset}
mathen version
```

Analysis outputs remain drafts and the model command is restricted to the
configured draft directory. Reviewed cards are never overwritten by LLM output.

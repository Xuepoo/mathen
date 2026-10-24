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

An OpenAI-compatible provider can be selected by changing `llm.base_url`. The
precedence for model execution is explicit CLI flags, environment variables,
then the TOML file:

```text
--api-key / --model / --base-url
MATHEN_LLM_BASE_URL, MATHEN_LLM_MODEL, OPENAI_API_KEY
[llm] in config.toml
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
url = "https://mathen.xuepoo.xyz/mcp"
token_env = "MATHEN_API_TOKEN"

[sync]
source = "https://github.com/Xuepoo/mathen/archive/refs/heads/main.tar.gz"
ref = "main"
```

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
mathen doctor
mathen config {init,show,path,set,unset}
mathen version
```

Analysis outputs remain drafts and the model command is restricted to the
configured draft directory. Reviewed cards are never overwritten by LLM output.

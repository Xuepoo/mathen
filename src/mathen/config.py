"""Cross-platform Mathen configuration and user data locations."""

from __future__ import annotations

import json
import os
import platform
import stat
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping


class ConfigError(ValueError):
    """Raised when a Mathen configuration cannot be loaded or written."""


@dataclass(frozen=True)
class PlatformPaths:
    """User-scoped configuration, data, and cache directories."""

    config_dir: Path
    data_dir: Path
    cache_dir: Path

    @property
    def config_file(self) -> Path:
        return self.config_dir / "config.toml"


@dataclass(frozen=True)
class PathSettings:
    """Paths used by Mathen's analysis and modeling commands."""

    data_dir: Path
    cards_dir: Path
    drafts_dir: Path
    analyses_dir: Path
    bundles_dir: Path
    manifest: Path
    cache_dir: Path


@dataclass(frozen=True)
class LLMSettings:
    """OpenAI-compatible LLM connection settings."""

    base_url: str = "https://api.openai.com/v1"
    model: str | None = None
    api_key: str | None = None
    api_key_env: str = "OPENAI_API_KEY"
    timeout: float = 120.0


@dataclass(frozen=True)
class MathenConfig:
    """Resolved configuration after applying defaults and a TOML file."""

    path: Path
    paths: PathSettings
    llm: LLMSettings
    loaded: bool = False


def platform_paths() -> PlatformPaths:
    """Return standard per-user directories on Linux, macOS, and Windows.

    ``MATHEN_CONFIG_DIR``, ``MATHEN_DATA_DIR``, and ``MATHEN_CACHE_DIR`` are
    supported for packaging, tests, and explicit machine-local overrides.
    """

    home = Path.home()
    system = platform.system()
    if system == "Windows":
        config_dir = (
            Path(os.environ.get("APPDATA", home / "AppData/Roaming")) / "mathen"
        )
        data_dir = (
            Path(os.environ.get("LOCALAPPDATA", home / "AppData/Local")) / "mathen"
        )
        cache_dir = data_dir / "cache"
    elif system == "Darwin":
        config_dir = home / "Library" / "Application Support" / "Mathen"
        data_dir = config_dir
        cache_dir = home / "Library" / "Caches" / "Mathen"
    else:
        config_dir = (
            Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "mathen"
        )
        data_dir = (
            Path(os.environ.get("XDG_DATA_HOME", home / ".local/share")) / "mathen"
        )
        cache_dir = Path(os.environ.get("XDG_CACHE_HOME", home / ".cache")) / "mathen"

    return PlatformPaths(
        config_dir=Path(os.environ.get("MATHEN_CONFIG_DIR", config_dir)).expanduser(),
        data_dir=Path(os.environ.get("MATHEN_DATA_DIR", data_dir)).expanduser(),
        cache_dir=Path(os.environ.get("MATHEN_CACHE_DIR", cache_dir)).expanduser(),
    )


def default_project_data_dir() -> Path:
    """Use checkout data when running from the repository, otherwise user data."""

    repository_data = Path(__file__).parents[2] / "data"
    if repository_data.is_dir():
        return repository_data
    return platform_paths().data_dir


def default_config() -> MathenConfig:
    """Build defaults without reading a configuration file."""

    data_dir = default_project_data_dir()
    user_paths = platform_paths()
    return MathenConfig(
        path=user_paths.config_file,
        paths=PathSettings(
            data_dir=data_dir,
            cards_dir=data_dir / "systems",
            drafts_dir=data_dir / "drafts",
            analyses_dir=data_dir / "analyses",
            bundles_dir=data_dir / "modeling",
            manifest=data_dir / "repositories" / "representative.json",
            cache_dir=(
                Path(__file__).parents[2] / ".cache" / "mathen" / "repos"
                if (Path(__file__).parents[2] / ".cache").exists()
                else user_paths.cache_dir / "repos"
            ),
        ),
        llm=LLMSettings(),
    )


def discover_config_path(explicit: Path | None = None) -> Path:
    """Resolve an explicit, environment, or standard configuration path."""

    if explicit is not None:
        return explicit.expanduser()
    configured = os.environ.get("MATHEN_CONFIG")
    if configured:
        return Path(configured).expanduser()
    return platform_paths().config_file


def load_config(
    path: Path | None = None,
    *,
    use_file: bool = True,
) -> MathenConfig:
    """Load TOML configuration, returning defaults when no file exists."""

    defaults = default_config()
    config_path = discover_config_path(path)
    if not use_file or not config_path.exists():
        return MathenConfig(
            path=config_path,
            paths=defaults.paths,
            llm=defaults.llm,
            loaded=False,
        )
    try:
        with config_path.open("rb") as file:
            raw = tomllib.load(file)
    except OSError as error:
        raise ConfigError(f"{config_path}: cannot read config: {error}") from error
    except tomllib.TOMLDecodeError as error:
        raise ConfigError(f"{config_path}: invalid TOML: {error}") from error
    if not isinstance(raw, dict):
        raise ConfigError(f"{config_path}: top-level TOML value must be a table")
    return _merge_config(defaults, config_path, raw)


def initialize_config(path: Path | None = None, *, force: bool = False) -> Path:
    """Create a commented starter configuration with private permissions."""

    config_path = discover_config_path(path)
    if config_path.exists() and not force:
        raise ConfigError(f"{config_path} already exists; use --force to replace it")
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_template(default_config()), encoding="utf-8")
    _restrict_permissions(config_path)
    return config_path


def set_config_value(
    key: str,
    value: str,
    path: Path | None = None,
) -> Path:
    """Set one supported dotted configuration key and preserve other values."""

    config_path = discover_config_path(path)
    config = load_config(config_path)
    raw = config_to_dict(config)
    parts = key.split(".")
    if len(parts) != 2 or parts[0] not in {"paths", "llm"}:
        raise ConfigError("config keys must use the paths.* or llm.* form")
    allowed = {
        "paths": set(PathSettings.__dataclass_fields__),
        "llm": set(LLMSettings.__dataclass_fields__),
    }[parts[0]]
    if parts[1] not in allowed:
        raise ConfigError(f"unsupported config key: {key}")
    section = raw.setdefault(parts[0], {})
    section[parts[1]] = _parse_value(value, parts[1])
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_dump_toml(raw), encoding="utf-8")
    _restrict_permissions(config_path)
    return config_path


def unset_config_value(key: str, path: Path | None = None) -> Path:
    """Remove one supported dotted configuration key from the TOML file."""

    config_path = discover_config_path(path)
    if not config_path.exists():
        raise ConfigError(f"{config_path} does not exist")
    config = load_config(config_path)
    raw = config_to_dict(config)
    parts = key.split(".")
    if len(parts) != 2 or parts[0] not in raw or parts[1] not in raw[parts[0]]:
        raise ConfigError(f"config key is not set: {key}")
    del raw[parts[0]][parts[1]]
    config_path.write_text(_dump_toml(raw), encoding="utf-8")
    _restrict_permissions(config_path)
    return config_path


def config_to_dict(
    config: MathenConfig, *, redact_secrets: bool = False
) -> dict[str, Any]:
    """Return a JSON/TOML-friendly view of resolved settings."""

    api_key = config.llm.api_key
    if redact_secrets and api_key:
        api_key = "***"
    return {
        "paths": {
            "data_dir": str(config.paths.data_dir),
            "cards_dir": str(config.paths.cards_dir),
            "drafts_dir": str(config.paths.drafts_dir),
            "analyses_dir": str(config.paths.analyses_dir),
            "bundles_dir": str(config.paths.bundles_dir),
            "manifest": str(config.paths.manifest),
            "cache_dir": str(config.paths.cache_dir),
        },
        "llm": {
            "base_url": config.llm.base_url,
            "model": config.llm.model,
            "api_key": api_key,
            "api_key_env": config.llm.api_key_env,
            "timeout": config.llm.timeout,
        },
    }


def _merge_config(
    defaults: MathenConfig, path: Path, raw: Mapping[str, Any]
) -> MathenConfig:
    paths = _section(raw, "paths")
    llm = _section(raw, "llm")
    default_paths = config_to_dict(defaults)["paths"]
    default_llm = config_to_dict(defaults)["llm"]
    for key, value in paths.items():
        if key not in default_paths:
            raise ConfigError(f"{path}: unsupported paths key: {key}")
        if not isinstance(value, str):
            raise ConfigError(f"{path}: paths.{key} must be a string")
        default_paths[key] = _expand_path(value)
    for key, value in llm.items():
        if key not in default_llm:
            raise ConfigError(f"{path}: unsupported llm key: {key}")
        if (
            key in {"model", "api_key", "api_key_env"}
            and value is not None
            and not isinstance(value, str)
        ):
            raise ConfigError(f"{path}: llm.{key} must be a string or null")
        if key == "timeout" and (
            not isinstance(value, (int, float)) or isinstance(value, bool)
        ):
            raise ConfigError(f"{path}: llm.timeout must be a number")
        if key == "base_url" and not isinstance(value, str):
            raise ConfigError(f"{path}: llm.base_url must be a string")
        default_llm[key] = value
    timeout = float(default_llm["timeout"])
    if timeout <= 0:
        raise ConfigError(f"{path}: llm.timeout must be positive")
    return MathenConfig(
        path=path,
        paths=PathSettings(
            **{key: Path(value) for key, value in default_paths.items()}
        ),
        llm=LLMSettings(**default_llm),
        loaded=True,
    )


def _section(raw: Mapping[str, Any], name: str) -> dict[str, Any]:
    value = raw.get(name, {})
    if not isinstance(value, dict):
        raise ConfigError(f"{name} must be a TOML table")
    return dict(value)


def _expand_path(value: str) -> str:
    return str(Path(os.path.expandvars(value)).expanduser())


def _parse_value(value: str, key: str) -> Any:
    if key == "timeout":
        try:
            parsed = float(value)
        except ValueError as error:
            raise ConfigError("llm.timeout must be a number") from error
        if parsed <= 0:
            raise ConfigError("llm.timeout must be positive")
        return parsed
    if key == "model" and value.lower() in {"none", "null"}:
        return None
    return value


def _template(config: MathenConfig) -> str:
    return """# Mathen user configuration. Paths may use ~ and environment variables.
# API keys can be stored here, but environment variables are preferred.

[paths]
data_dir = {data_dir}
cards_dir = {cards_dir}
drafts_dir = {drafts_dir}
analyses_dir = {analyses_dir}
bundles_dir = {bundles_dir}
manifest = {manifest}
cache_dir = {cache_dir}

[llm]
base_url = "https://api.openai.com/v1"
# model = "your-model-name"
# api_key = "your-api-key"
api_key_env = "OPENAI_API_KEY"
timeout = 120.0
""".format(
        **{
            key: _toml_string(str(value))
            for key, value in config_to_dict(config)["paths"].items()
        }
    )


def _dump_toml(raw: Mapping[str, Any]) -> str:
    lines: list[str] = []
    for section_name in ("paths", "llm"):
        section = raw.get(section_name, {})
        if not isinstance(section, Mapping):
            continue
        lines.append(f"[{section_name}]")
        for key, value in section.items():
            if value is None:
                continue
            lines.append(f"{key} = {_toml_value(value)}")
        lines.append("")
    return "\n".join(lines)


def _toml_value(value: Any) -> str:
    if isinstance(value, str):
        return _toml_string(value)
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, (int, float)):
        return str(value)
    raise ConfigError(f"unsupported TOML value: {value!r}")


def _toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _restrict_permissions(path: Path) -> None:
    if sys.platform != "win32":
        path.chmod(stat.S_IRUSR | stat.S_IWUSR)

#!/usr/bin/env python3
"""Inspect local direct-LLM readiness without loading or invoking a model.

The inspector only checks executable names, import metadata, process names,
service state, and aggregate cache metadata. It never reads environment
values, records model identifiers, contacts a network endpoint, or stores a
prompt/output. The resulting record is research-only and not an inference
result.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Mapping

SCHEMA_VERSION = "1.0"
INSPECTOR_VERSION = "mth-0194-v1"
RECORD_ID = "mth-0194-direct-llm-readiness"
EXECUTABLES = (
    "ollama",
    "llama-cli",
    "llama-server",
    "llamafile",
    "vllm",
    "text-generation-launcher",
    "lmstudio",
    "lms",
    "local-ai",
    "llamactl",
    "mlx_lm",
)
PYTHON_MODULES = (
    "ollama",
    "llama_cpp",
    "vllm",
    "transformers",
    "mlx_lm",
    "ctransformers",
)
CACHE_LOCATIONS = {
    "ollama_data": "~/.ollama",
    "huggingface_cache": "~/.cache/huggingface",
    "llama_cpp_cache": "~/.cache/llama.cpp",
    "lm_studio_cache": "~/.cache/lm-studio",
    "lmstudio_cache": "~/.cache/lmstudio",
    "vllm_cache": "~/.cache/vllm",
}
CONFIGURATION_LOCATIONS = {
    "ollama_config": "~/.config/ollama",
    "lm_studio_config": "~/.config/lm-studio",
    "lmstudio_config": "~/.config/lmstudio",
    "vllm_config": "~/.config/vllm",
    "huggingface_config": "~/.config/huggingface",
}
SERVICE_UNITS = ("ollama.service", "llama-server.service", "local-ai.service")
ENVIRONMENT_NAMES = tuple(
    sorted(
        name
        for name in os.environ
        if not any(
            part in name.upper()
            for part in ("KEY", "TOKEN", "PASSWORD", "SECRET", "AUTH")
        )
        and any(
            part in name.upper()
            for part in (
                "HF",
                "HUGGINGFACE",
                "INFERENCE",
                "LLAMA",
                "MODEL",
                "OLLAMA",
                "VLLM",
            )
        )
    )
)


class ReadinessValidationError(ValueError):
    """Raised when a readiness record violates its research boundary."""


def _digest(value: Any) -> str:
    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def _git_revision(root: Path) -> str:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        return "unavailable"
    revision = result.stdout.strip()
    return revision if result.returncode == 0 and revision else "unavailable"


def _module_available(name: str) -> bool:
    try:
        return importlib.util.find_spec(name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def _process_names() -> list[str]:
    names = set()
    for entry in Path("/proc").glob("[0-9]*"):
        try:
            name = (entry / "comm").read_text(encoding="utf-8").strip()
        except (OSError, UnicodeError):
            continue
        normalized = name.casefold()
        if any(
            token in normalized
            for token in ("ollama", "llama", "vllm", "lmstudio", "local-ai")
        ):
            names.add(name)
    return sorted(names)


def _service_status(name: str) -> str:
    systemctl = shutil.which("systemctl")
    if systemctl is None:
        return "unknown"
    try:
        result = subprocess.run(
            [systemctl, "is-active", name], check=False, capture_output=True, text=True
        )
    except OSError:
        return "unknown"
    status = result.stdout.strip()
    if status in {"active", "inactive", "failed"}:
        return status
    if result.returncode == 5:
        return "not-installed"
    return "unknown"


def _cache_metadata(label: str, display_path: str) -> dict[str, Any]:
    path = Path(display_path).expanduser()
    if not path.exists():
        return {
            "label": label,
            "present": False,
            "file_count": 0,
            "directory_count": 0,
            "bytes": 0,
            "identifiers_recorded": False,
        }
    files = 0
    directories = 0
    total_bytes = 0
    try:
        for child in path.rglob("*"):
            if child.is_dir():
                directories += 1
            elif child.is_file():
                files += 1
                try:
                    total_bytes += child.stat().st_size
                except OSError:
                    pass
    except OSError:
        pass
    return {
        "label": label,
        "present": True,
        "file_count": files,
        "directory_count": directories,
        "bytes": total_bytes,
        "identifiers_recorded": False,
    }


def build_record(root: Path) -> dict[str, Any]:
    executable_records = [
        {
            "name": name,
            "available": shutil.which(name) is not None,
            "path_recorded": False,
            "version_probe": "not-run",
        }
        for name in EXECUTABLES
    ]
    module_records = [
        {"name": name, "available": _module_available(name)} for name in PYTHON_MODULES
    ]
    service_records = [
        {"name": name, "status": _service_status(name)} for name in SERVICE_UNITS
    ]
    runtime_available = any(item["available"] for item in executable_records) or any(
        item["available"] for item in module_records
    )
    runtime_inventory = {
        "approved_runtime_available": runtime_available,
        "executables": executable_records,
        "python_modules": module_records,
        "processes": _process_names(),
        "service_units": service_records,
    }
    cache_inventory = {
        "model_identifiers_recorded": False,
        "locations": [
            _cache_metadata(label, path) for label, path in CACHE_LOCATIONS.items()
        ],
    }
    configuration_inventory = {
        "secret_values_read": False,
        "locations": [
            _cache_metadata(label, path)
            for label, path in CONFIGURATION_LOCATIONS.items()
        ],
    }
    inspection = {
        "inspector": "scripts/direct_llm_readiness.py",
        "inspector_version": INSPECTOR_VERSION,
        "repository_revision": _git_revision(root),
        "python_version": platform.python_version(),
        "platform": platform.platform(aliased=True),
        "network_requests": False,
        "checked_names": {
            "executables": list(EXECUTABLES),
            "python_modules": list(PYTHON_MODULES),
            "cache_locations": list(CACHE_LOCATIONS),
            "configuration_locations": list(CONFIGURATION_LOCATIONS),
            "service_units": list(SERVICE_UNITS),
            "environment_variables": list(ENVIRONMENT_NAMES),
        },
    }
    provenance_basis = {
        "inspection": inspection,
        "runtime_inventory": runtime_inventory,
        "cache_inventory": cache_inventory,
        "configuration_inventory": configuration_inventory,
    }
    return {
        "manifest_kind": "direct_llm_readiness",
        "schema_version": SCHEMA_VERSION,
        "record_id": RECORD_ID,
        "purpose": (
            "Audit whether an approved local direct-LLM runtime is ready "
            "without running inference."
        ),
        "inspection": inspection,
        "runtime_inventory": runtime_inventory,
        "cache_inventory": cache_inventory,
        "configuration_inventory": configuration_inventory,
        "provenance": {
            "provider": None,
            "exact_model_id": None,
            "prompt": {"status": "not-rendered", "raw_stored": False, "digest": None},
            "output": {"status": "not-rendered", "raw_stored": False, "digest": None},
            "inspection_digest": _digest(provenance_basis),
        },
        "metrics": {
            "latency_ms": None,
            "throughput_tokens_per_second": None,
            "quality": None,
            "coverage": None,
            "error_rate": None,
        },
        "result_boundary": {
            "status": "not-evaluated",
            "canonical": False,
            "promotion_requires_human_review": True,
            "storage_scope": "research",
            "reason": (
                "No approved local runtime was available; no provider or model "
                "was recorded, no prompt or output was rendered, and no "
                "inference request was made."
            ),
        },
    }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ReadinessValidationError(message)


def validate_record(value: Mapping[str, Any]) -> None:
    """Validate the secret-safe, not-evaluated readiness boundary."""
    _require(isinstance(value, Mapping), "record must be an object")
    _require(
        value.get("manifest_kind") == "direct_llm_readiness", "invalid manifest_kind"
    )
    _require(
        value.get("schema_version") == SCHEMA_VERSION, "unsupported schema_version"
    )
    _require(
        value.get("provenance", {}).get("provider") is None, "provider must remain null"
    )
    _require(
        value.get("provenance", {}).get("exact_model_id") is None,
        "exact_model_id must remain null",
    )
    provenance = value.get("provenance", {})
    for field in ("prompt", "output"):
        artifact = provenance.get(field, {})
        _require(
            artifact.get("status") == "not-rendered",
            f"{field} must remain not-rendered",
        )
        _require(
            artifact.get("raw_stored") is False, f"{field} raw_stored must remain false"
        )
        _require(artifact.get("digest") is None, f"{field} digest must remain null")
    _require(
        value.get("runtime_inventory", {}).get("approved_runtime_available") is False,
        "runtime must not be marked available",
    )
    _require(
        value.get("cache_inventory", {}).get("model_identifiers_recorded") is False,
        "model identifiers must not be recorded",
    )
    _require(
        value.get("configuration_inventory", {}).get("secret_values_read") is False,
        "configuration secret values must not be read",
    )
    metrics = value.get("metrics", {})
    _require(
        metrics and all(item is None for item in metrics.values()),
        "readiness metrics must be null",
    )
    boundary = value.get("result_boundary", {})
    _require(boundary.get("status") == "not-evaluated", "status must be not-evaluated")
    _require(boundary.get("canonical") is False, "canonical must remain false")
    _require(
        boundary.get("promotion_requires_human_review") is True,
        "human review boundary required",
    )
    _require(
        boundary.get("storage_scope") == "research",
        "storage scope must remain research",
    )


def _write(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    inspect_parser = subparsers.add_parser("inspect", help="write a readiness record")
    inspect_parser.add_argument("--root", type=Path, default=Path.cwd())
    inspect_parser.add_argument("--output", type=Path, required=True)
    validate_parser = subparsers.add_parser(
        "validate", help="validate a readiness record"
    )
    validate_parser.add_argument("path", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "inspect":
            record = build_record(args.root)
            validate_record(record)
            _write(args.output, record)
            print(f"wrote readiness record: {args.output}")
        else:
            value = json.loads(args.path.read_text(encoding="utf-8"))
            validate_record(value)
            print(f"valid: {args.path}")
    except (OSError, json.JSONDecodeError, ReadinessValidationError) as error:
        print(f"invalid: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

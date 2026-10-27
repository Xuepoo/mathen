#!/usr/bin/env python3
"""Validate a research-only direct-LLM control manifest.

This module deliberately stops at an audit boundary.  It does not select a
provider, contact an endpoint, load a model, or store model output.  The
``dry-run`` command creates a not-evaluated manifest when no runtime is
available; a future local runner may use the same manifest contract.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping

ROOT = Path(__file__).parents[1]
SCHEMA_VERSION = "1.0"
MANIFEST_KIND = "direct_llm_control"
DIGEST_PREFIX = "sha256:"
DEFAULT_RUN_ID = "mth-0176-direct-llm-control-dry-run"
DEFAULT_PROTOCOL_VERSION = "mth-0176-v1"
DEFAULT_BENCHMARK_VERSION = "mth-0118-v1"


class DirectLLMControlValidationError(ValueError):
    """Raised when a direct-LLM control manifest violates its boundary."""


def digest_bytes(value: bytes) -> str:
    """Return a stable, secret-safe digest for bytes."""

    return DIGEST_PREFIX + hashlib.sha256(value).hexdigest()


def digest_json(value: Any) -> str:
    """Digest canonical JSON without exposing its contents."""

    return digest_bytes(
        json.dumps(
            value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
    )


def _digest_path(path: Path) -> str:
    """Digest a file or deterministic directory bundle."""

    if path.is_file():
        return digest_bytes(path.read_bytes())
    if path.is_dir():
        entries = []
        for child in sorted(item for item in path.rglob("*") if item.is_file()):
            entries.append(
                {
                    "path": child.relative_to(path).as_posix(),
                    "digest": digest_bytes(child.read_bytes()),
                }
            )
        return digest_json(entries)
    raise DirectLLMControlValidationError(f"bundle path does not exist: {path}")


def _object(label: str, value: Any) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DirectLLMControlValidationError(f"{label} must be an object")
    return value


def _allowed(label: str, value: Mapping[str, Any], fields: set[str]) -> None:
    unknown = set(value) - fields
    if unknown:
        raise DirectLLMControlValidationError(
            f"{label} has unknown fields: {sorted(unknown)}"
        )


def _required(label: str, value: Mapping[str, Any], fields: set[str]) -> None:
    missing = fields - set(value)
    if missing:
        raise DirectLLMControlValidationError(
            f"{label} is missing fields: {sorted(missing)}"
        )


def _text(value: Mapping[str, Any], field: str, label: str) -> str:
    item = value.get(field)
    if not isinstance(item, str) or not item:
        raise DirectLLMControlValidationError(
            f"{label}.{field} must be a non-empty string"
        )
    return item


def _digest(
    value: Mapping[str, Any], field: str, label: str, *, nullable: bool = False
) -> str | None:
    item = value.get(field)
    if nullable and item is None:
        return None
    if not isinstance(item, str) or len(item) != len(DIGEST_PREFIX) + 64:
        raise DirectLLMControlValidationError(
            f"{label}.{field} must be a sha256 digest"
        )
    if not item.startswith(DIGEST_PREFIX):
        raise DirectLLMControlValidationError(
            f"{label}.{field} must be a sha256 digest"
        )
    try:
        int(item[len(DIGEST_PREFIX) :], 16)
    except ValueError as error:
        raise DirectLLMControlValidationError(
            f"{label}.{field} must be a sha256 digest"
        ) from error
    return item


def _string_list(value: Mapping[str, Any], field: str, label: str) -> list[str]:
    items = value.get(field)
    if not isinstance(items, list) or any(
        not isinstance(item, str) or not item for item in items
    ):
        raise DirectLLMControlValidationError(
            f"{label}.{field} must be a list of strings"
        )
    if len(items) != len(set(items)):
        raise DirectLLMControlValidationError(f"{label}.{field} must be unique")
    return items


def _reject_secret_keys(value: Any, location: str = "manifest") -> None:
    """Reject common secret-bearing keys anywhere in a supplied manifest."""

    secret_keys = {
        "api_key",
        "apikey",
        "authorization",
        "password",
        "secret",
        "token",
        "access_token",
        "refresh_token",
        "bearer_token",
    }
    if isinstance(value, Mapping):
        for key, item in value.items():
            normalized = str(key).casefold().replace("-", "_")
            if normalized != "secret_safe" and normalized in secret_keys:
                raise DirectLLMControlValidationError(
                    f"{location} contains secret-bearing field: {key}"
                )
            _reject_secret_keys(item, f"{location}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            _reject_secret_keys(item, f"{location}[{index}]")


def _validate_candidate(candidate: Any, index: int, evidence_ids: set[str]) -> None:
    label = f"candidates[{index}]"
    item = _object(label, candidate)
    _required(label, item, {"id", "evidence_ids", "claims", "proven"})
    _allowed(label, item, {"id", "evidence_ids", "claims", "proven"})
    _text(item, "id", label)
    candidate_evidence = set(_string_list(item, "evidence_ids", label))
    if not candidate_evidence:
        raise DirectLLMControlValidationError(f"{label}.evidence_ids must not be empty")
    if not candidate_evidence.issubset(evidence_ids):
        raise DirectLLMControlValidationError(
            f"{label}.evidence_ids must be local to input_bundle.evidence_ids"
        )
    if item.get("proven") is not False:
        raise DirectLLMControlValidationError(f"{label}.proven must remain false")
    claims = item.get("claims")
    if not isinstance(claims, list):
        raise DirectLLMControlValidationError(f"{label}.claims must be a list")
    claim_ids: set[str] = set()
    for claim_index, claim in enumerate(claims):
        claim_label = f"{label}.claims[{claim_index}]"
        claim_item = _object(claim_label, claim)
        _required(claim_label, claim_item, {"id", "claim_type", "text", "evidence_ids"})
        _allowed(claim_label, claim_item, {"id", "claim_type", "text", "evidence_ids"})
        claim_id = _text(claim_item, "id", claim_label)
        if claim_id in claim_ids:
            raise DirectLLMControlValidationError(f"duplicate claim id: {claim_id}")
        claim_ids.add(claim_id)
        if claim_item.get("claim_type") not in {
            "fact",
            "inference",
            "hypothesis",
            "analogy",
        }:
            raise DirectLLMControlValidationError(
                f"{claim_label}.claim_type is invalid"
            )
        _text(claim_item, "text", claim_label)
        claim_evidence = set(_string_list(claim_item, "evidence_ids", claim_label))
        if not claim_evidence:
            raise DirectLLMControlValidationError(
                f"{claim_label}.evidence_ids must not be empty"
            )
        if not claim_evidence.issubset(candidate_evidence):
            raise DirectLLMControlValidationError(
                f"{claim_label}.evidence_ids must be local to its candidate"
            )


def validate_manifest(value: Mapping[str, Any]) -> None:
    """Validate provenance, output safety, and evidence locality."""

    if not isinstance(value, Mapping):
        raise DirectLLMControlValidationError("manifest must be an object")
    _reject_secret_keys(value)
    required = {
        "manifest_kind",
        "schema_version",
        "run_id",
        "protocol_version",
        "benchmark_version",
        "input_bundle",
        "prompt",
        "provider",
        "runtime",
        "sampling",
        "output",
        "candidates",
        "result_boundary",
        "outcome",
    }
    _required("manifest", value, required)
    _allowed("manifest", value, required)
    if value.get("manifest_kind") != MANIFEST_KIND:
        raise DirectLLMControlValidationError(
            "manifest_kind must be direct_llm_control"
        )
    if value.get("schema_version") != SCHEMA_VERSION:
        raise DirectLLMControlValidationError("unsupported schema_version")
    for field in ("run_id", "protocol_version", "benchmark_version"):
        _text(value, field, "manifest")

    bundle = _object("input_bundle", value["input_bundle"])
    _required("input_bundle", bundle, {"id", "digest", "evidence_ids"})
    _allowed("input_bundle", bundle, {"id", "digest", "evidence_ids"})
    _text(bundle, "id", "input_bundle")
    _digest(bundle, "digest", "input_bundle")
    evidence_ids = set(_string_list(bundle, "evidence_ids", "input_bundle"))

    prompt = _object("prompt", value["prompt"])
    _required("prompt", prompt, {"id", "digest"})
    _allowed("prompt", prompt, {"id", "digest"})
    _text(prompt, "id", "prompt")
    _digest(prompt, "digest", "prompt")

    provider = _object("provider", value["provider"])
    _required("provider", provider, {"name", "exact_model_id"})
    _allowed("provider", provider, {"name", "exact_model_id"})
    _text(provider, "name", "provider")
    _text(provider, "exact_model_id", "provider")

    runtime = _object("runtime", value["runtime"])
    runtime_fields = {
        "runtime_kind",
        "runtime_version",
        "runner_version",
        "source_revision",
        "execution_environment",
    }
    _required("runtime", runtime, runtime_fields)
    _allowed("runtime", runtime, runtime_fields)
    for field in runtime_fields:
        _text(runtime, field, "runtime")

    sampling = _object("sampling", value["sampling"])
    _required("sampling", sampling, {"seed", "decoding_parameters"})
    _allowed("sampling", sampling, {"seed", "decoding_parameters"})
    if not isinstance(sampling.get("seed"), int) or isinstance(
        sampling.get("seed"), bool
    ):
        raise DirectLLMControlValidationError("sampling.seed must be an integer")
    _object("sampling.decoding_parameters", sampling.get("decoding_parameters"))

    output = _object("output", value["output"])
    _required("output", output, {"status", "digest", "secret_safe", "record_count"})
    _allowed(
        "output",
        output,
        {"status", "digest", "secret_safe", "record_count", "storage_ref"},
    )
    status = output.get("status")
    if status not in {"absent", "available", "redacted"}:
        raise DirectLLMControlValidationError("output.status is invalid")
    output_digest = _digest(output, "digest", "output", nullable=True)
    if status == "absent" and output_digest is not None:
        raise DirectLLMControlValidationError("absent output must not have a digest")
    if status in {"available", "redacted"} and output_digest is None:
        raise DirectLLMControlValidationError("evaluated output requires a digest")
    if output.get("secret_safe") is not True:
        raise DirectLLMControlValidationError("output.secret_safe must remain true")
    if (
        not isinstance(output.get("record_count"), int)
        or isinstance(output.get("record_count"), bool)
        or output["record_count"] < 0
    ):
        raise DirectLLMControlValidationError(
            "output.record_count must be a non-negative integer"
        )
    if (
        "storage_ref" in output
        and output["storage_ref"] is not None
        and (not isinstance(output["storage_ref"], str) or not output["storage_ref"])
    ):
        raise DirectLLMControlValidationError(
            "output.storage_ref must be a non-empty string or null"
        )
    if status in {"available", "redacted"}:
        provenance_values = {
            "provider.name": provider["name"],
            "provider.exact_model_id": provider["exact_model_id"],
            "prompt.id": prompt["id"],
            "runtime.runtime_kind": runtime["runtime_kind"],
            "runtime.runtime_version": runtime["runtime_version"],
            "runtime.source_revision": runtime["source_revision"],
        }
        unavailable = {
            key: item
            for key, item in provenance_values.items()
            if item.casefold() in {"unavailable", "not-run", "not-evaluated"}
        }
        if unavailable:
            raise DirectLLMControlValidationError(
                "evaluated output requires exact runtime provenance; unavailable "
                f"fields: {sorted(unavailable)}"
            )

    candidates = value["candidates"]
    if not isinstance(candidates, list):
        raise DirectLLMControlValidationError("candidates must be a list")
    candidate_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        candidate_id = _object(f"candidates[{index}]", candidate).get("id")
        if isinstance(candidate_id, str) and candidate_id in candidate_ids:
            raise DirectLLMControlValidationError(
                f"duplicate candidate id: {candidate_id}"
            )
        if isinstance(candidate_id, str):
            candidate_ids.add(candidate_id)
        _validate_candidate(candidate, index, evidence_ids)

    boundary = _object("result_boundary", value["result_boundary"])
    _required(
        "result_boundary",
        boundary,
        {"canonical", "promotion_requires_human_review", "storage_scope"},
    )
    _allowed(
        "result_boundary",
        boundary,
        {"canonical", "promotion_requires_human_review", "storage_scope"},
    )
    if boundary.get("canonical") is not False:
        raise DirectLLMControlValidationError(
            "result_boundary.canonical must remain false"
        )
    if boundary.get("promotion_requires_human_review") is not True:
        raise DirectLLMControlValidationError(
            "result_boundary.promotion_requires_human_review must remain true"
        )
    if boundary.get("storage_scope") not in {"research", "draft"}:
        raise DirectLLMControlValidationError(
            "result_boundary.storage_scope is invalid"
        )

    outcome = _object("outcome", value["outcome"])
    _required("outcome", outcome, {"status", "reason"})
    _allowed("outcome", outcome, {"status", "reason"})
    if outcome.get("status") not in {
        "accepted",
        "rejected",
        "undetermined",
        "falsified",
        "not-evaluated",
    }:
        raise DirectLLMControlValidationError("outcome.status is invalid")
    _text(outcome, "reason", "outcome")
    if status == "absent":
        if outcome.get("status") != "not-evaluated":
            raise DirectLLMControlValidationError("absent output must be not-evaluated")
        if candidates:
            raise DirectLLMControlValidationError(
                "absent output cannot contain candidates"
            )


def dry_run_manifest(
    *,
    provider: str = "unavailable",
    model: str = "unavailable",
    prompt_digest: str | None = None,
    input_bundle_digest: str | None = None,
    run_id: str = DEFAULT_RUN_ID,
    seed: int = 0,
) -> dict[str, Any]:
    """Build a safe no-runtime manifest without making a model request."""

    prompt_digest = prompt_digest or digest_bytes(
        b"mth-0176 direct-llm control prompt unavailable"
    )
    input_bundle_digest = input_bundle_digest or digest_json(
        {"status": "not-evaluated"}
    )
    manifest = {
        "manifest_kind": MANIFEST_KIND,
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "protocol_version": DEFAULT_PROTOCOL_VERSION,
        "benchmark_version": DEFAULT_BENCHMARK_VERSION,
        "input_bundle": {
            "id": "mth-0176-input-bundle-not-evaluated",
            "digest": input_bundle_digest,
            "evidence_ids": [],
        },
        "prompt": {"id": "mth-0176-prompt-not-evaluated", "digest": prompt_digest},
        "provider": {"name": provider, "exact_model_id": model},
        "runtime": {
            "runtime_kind": "unavailable",
            "runtime_version": "not-run",
            "runner_version": "mth-0176-v1",
            "source_revision": "not-run",
            "execution_environment": "research-only-dry-run",
        },
        "sampling": {"seed": seed, "decoding_parameters": {}},
        "output": {
            "status": "absent",
            "digest": None,
            "secret_safe": True,
            "record_count": 0,
            "storage_ref": None,
        },
        "candidates": [],
        "result_boundary": {
            "canonical": False,
            "promotion_requires_human_review": True,
            "storage_scope": "research",
        },
        "outcome": {
            "status": "not-evaluated",
            "reason": "No local model/runtime was available; no output was produced.",
        },
    }
    validate_manifest(manifest)
    return manifest


def _load(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise DirectLLMControlValidationError(
            f"{path}: unable to read JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise DirectLLMControlValidationError(f"{path}: manifest must be an object")
    return value


def _write_json(path: Path, value: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate_parser = subparsers.add_parser("validate", help="validate a manifest")
    validate_parser.add_argument("path", type=Path)
    dry_parser = subparsers.add_parser(
        "dry-run", help="write a safe not-evaluated manifest"
    )
    dry_parser.add_argument("--output", type=Path, required=True)
    dry_parser.add_argument("--provider", default="unavailable")
    dry_parser.add_argument("--model", default="unavailable")
    dry_parser.add_argument("--prompt", type=Path)
    dry_parser.add_argument("--input-bundle", type=Path)
    dry_parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    try:
        if args.command == "validate":
            validate_manifest(_load(args.path))
            print(f"valid: {args.path}")
        else:
            prompt_digest = _digest_path(args.prompt) if args.prompt else None
            input_digest = (
                _digest_path(args.input_bundle) if args.input_bundle else None
            )
            manifest = dry_run_manifest(
                provider=args.provider,
                model=args.model,
                prompt_digest=prompt_digest,
                input_bundle_digest=input_digest,
                seed=args.seed,
            )
            _write_json(args.output, manifest)
            print(f"wrote not-evaluated manifest: {args.output}")
    except DirectLLMControlValidationError as error:
        print(f"invalid: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Scale-aware, evidence-backed architecture microstructures.

Microstructures are deliberately a separate document type from reviewed
Architecture Cards.  They describe a reusable architectural unit at a stated
scale without promoting that unit into the canonical system catalog.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MICROSTRUCTURE_SCHEMA_VERSION = "1.0"
MICROSTRUCTURE_LEVELS = frozenset(
    {"primitive", "mechanism", "subsystem", "system", "ecosystem"}
)
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)
EVIDENCE_KINDS = frozenset(
    {"official-doc", "paper", "source-code", "experiment", "secondary"}
)
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "id",
    "name",
    "summary",
    "scale",
    "role",
    "state",
    "events",
    "operations",
    "inputs",
    "outputs",
    "preconditions",
    "postconditions",
    "invariants",
    "boundaries",
    "resource_effects",
    "failure_modes",
    "validity_scope",
    "claim_type",
    "claim_status",
    "evidence_ids",
    "evidence",
}
_REQUIRED_TOP_LEVEL_FIELDS = _TOP_LEVEL_FIELDS
_COMMON_CLAIM_FIELDS = {"claim_type", "claim_status", "evidence_ids"}


class MicrostructureValidationError(ValueError):
    """Raised when a microstructure violates its semantic contract."""


@dataclass(frozen=True, slots=True)
class Microstructure:
    """Immutable in-memory representation of a validated microstructure.

    The element dictionaries intentionally retain their JSON shape.  This
    keeps the first contract extensible while validation remains strict about
    the fields that have defined semantics.
    """

    schema_version: str
    id: str
    name: str
    summary: str
    scale: dict[str, Any]
    role: dict[str, Any]
    state: tuple[dict[str, Any], ...]
    events: tuple[dict[str, Any], ...]
    operations: tuple[dict[str, Any], ...]
    inputs: tuple[dict[str, Any], ...]
    outputs: tuple[dict[str, Any], ...]
    preconditions: tuple[dict[str, Any], ...]
    postconditions: tuple[dict[str, Any], ...]
    invariants: tuple[dict[str, Any], ...]
    boundaries: tuple[dict[str, Any], ...]
    resource_effects: tuple[dict[str, Any], ...]
    failure_modes: tuple[dict[str, Any], ...]
    validity_scope: dict[str, Any]
    claim_type: str
    claim_status: str
    evidence_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "Microstructure":
        """Validate and construct a microstructure from JSON-compatible data."""

        validate_microstructure(value)
        return cls(
            schema_version=value["schema_version"],
            id=value["id"],
            name=value["name"],
            summary=value["summary"],
            scale=copy.deepcopy(value["scale"]),
            role=copy.deepcopy(value["role"]),
            state=tuple(copy.deepcopy(value["state"])),
            events=tuple(copy.deepcopy(value["events"])),
            operations=tuple(copy.deepcopy(value["operations"])),
            inputs=tuple(copy.deepcopy(value["inputs"])),
            outputs=tuple(copy.deepcopy(value["outputs"])),
            preconditions=tuple(copy.deepcopy(value["preconditions"])),
            postconditions=tuple(copy.deepcopy(value["postconditions"])),
            invariants=tuple(copy.deepcopy(value["invariants"])),
            boundaries=tuple(copy.deepcopy(value["boundaries"])),
            resource_effects=tuple(copy.deepcopy(value["resource_effects"])),
            failure_modes=tuple(copy.deepcopy(value["failure_modes"])),
            validity_scope=copy.deepcopy(value["validity_scope"]),
            claim_type=value["claim_type"],
            claim_status=value["claim_status"],
            evidence_ids=tuple(value["evidence_ids"]),
            evidence=tuple(copy.deepcopy(value["evidence"])),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "scale": copy.deepcopy(self.scale),
            "role": copy.deepcopy(self.role),
            "state": [copy.deepcopy(item) for item in self.state],
            "events": [copy.deepcopy(item) for item in self.events],
            "operations": [copy.deepcopy(item) for item in self.operations],
            "inputs": [copy.deepcopy(item) for item in self.inputs],
            "outputs": [copy.deepcopy(item) for item in self.outputs],
            "preconditions": [copy.deepcopy(item) for item in self.preconditions],
            "postconditions": [copy.deepcopy(item) for item in self.postconditions],
            "invariants": [copy.deepcopy(item) for item in self.invariants],
            "boundaries": [copy.deepcopy(item) for item in self.boundaries],
            "resource_effects": [copy.deepcopy(item) for item in self.resource_effects],
            "failure_modes": [copy.deepcopy(item) for item in self.failure_modes],
            "validity_scope": copy.deepcopy(self.validity_scope),
            "claim_type": self.claim_type,
            "claim_status": self.claim_status,
            "evidence_ids": list(self.evidence_ids),
            "evidence": [copy.deepcopy(item) for item in self.evidence],
        }


def load_microstructure(path: Path) -> Microstructure:
    """Load, validate, and model one microstructure JSON document."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise MicrostructureValidationError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise MicrostructureValidationError(f"{path}: microstructure must be an object")
    try:
        return Microstructure.from_dict(value)
    except MicrostructureValidationError as error:
        raise MicrostructureValidationError(f"{path}: {error}") from error


def discover_microstructures(path: Path) -> list[Path]:
    """Return JSON microstructure files in deterministic order."""

    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(
        candidate for candidate in path.rglob("*.json") if candidate.is_file()
    )


def validate_microstructure(
    microstructure: dict[str, Any], path: Path | None = None
) -> None:
    """Validate structural, evidence, and cross-reference invariants."""

    label = str(path) if path else str(microstructure.get("id", "microstructure"))
    if not isinstance(microstructure, dict):
        raise MicrostructureValidationError(f"{label}: must be an object")
    missing = _REQUIRED_TOP_LEVEL_FIELDS - microstructure.keys()
    if missing:
        raise MicrostructureValidationError(
            f"{label}: missing fields: {sorted(missing)}"
        )
    unexpected = microstructure.keys() - _TOP_LEVEL_FIELDS
    if unexpected:
        raise MicrostructureValidationError(
            f"{label}: unexpected fields: {sorted(unexpected)}"
        )

    _require_string(label, "schema_version", microstructure["schema_version"])
    if microstructure["schema_version"] != MICROSTRUCTURE_SCHEMA_VERSION:
        raise MicrostructureValidationError(
            f"{label}: unsupported schema_version: {microstructure['schema_version']}"
        )
    for field in ("id", "name", "summary"):
        _require_string(label, field, microstructure[field])
    _require_id(label, "id", microstructure["id"])
    evidence = microstructure["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise MicrostructureValidationError(f"{label}: evidence must be non-empty")
    evidence_ids: set[str] = set()
    for index, item in enumerate(evidence):
        evidence_label = f"evidence[{index}]"
        _validate_evidence(label, evidence_label, item)
        evidence_id = item["id"]
        if evidence_id in evidence_ids:
            raise MicrostructureValidationError(
                f"{label}: duplicate evidence id: {evidence_id}"
            )
        evidence_ids.add(evidence_id)

    _validate_claim_fields(label, microstructure, "microstructure", evidence_ids)

    _validate_scale(label, microstructure["scale"], evidence_ids)
    _validate_claim_fields(label, microstructure["role"], "role", evidence_ids)
    _validate_validity_scope(label, microstructure["validity_scope"], evidence_ids)

    collections = {
        "state": (
            "state",
            {"id", "name", "description"},
            {"id", "name", "description", "initial", "terminal"},
        ),
        "events": (
            "event",
            {"id", "name", "description", "source_state", "target_state"},
            {"id", "name", "description", "source_state", "target_state"},
        ),
        "operations": (
            "operation",
            {
                "id",
                "name",
                "description",
                "input_ids",
                "output_ids",
                "precondition_ids",
                "postcondition_ids",
            },
            {
                "id",
                "name",
                "description",
                "input_ids",
                "output_ids",
                "precondition_ids",
                "postcondition_ids",
            },
        ),
        "inputs": (
            "input",
            {"id", "name", "description", "type", "source"},
            {"id", "name", "description", "type", "source"},
        ),
        "outputs": (
            "output",
            {"id", "name", "description", "type", "destination"},
            {"id", "name", "description", "type", "destination"},
        ),
        "preconditions": (
            "precondition",
            {"id", "name", "description"},
            {"id", "name", "description"},
        ),
        "postconditions": (
            "postcondition",
            {"id", "name", "description"},
            {"id", "name", "description"},
        ),
        "invariants": (
            "invariant",
            {"id", "name", "description"},
            {"id", "name", "description"},
        ),
        "boundaries": (
            "boundary",
            {"id", "name", "description", "kind", "inside", "outside"},
            {"id", "name", "description", "kind", "inside", "outside"},
        ),
        "resource_effects": (
            "resource effect",
            {"id", "name", "description", "resource", "effect"},
            {"id", "name", "description", "resource", "effect"},
        ),
        "failure_modes": (
            "failure mode",
            {"id", "name", "description", "trigger", "effect", "recovery"},
            {"id", "name", "description", "trigger", "effect", "recovery"},
        ),
    }
    ids: dict[str, set[str]] = {}
    all_ids: set[str] = set()
    for field, (kind, required, allowed) in collections.items():
        values = microstructure[field]
        if not isinstance(values, list):
            raise MicrostructureValidationError(f"{label}: {field} must be a list")
        ids[field] = set()
        for index, item in enumerate(values):
            item_label = f"{field}[{index}]"
            _validate_element(
                label, item_label, item, kind, required, allowed, evidence_ids
            )
            item_id = item["id"]
            if item_id in all_ids:
                raise MicrostructureValidationError(
                    f"{label}: duplicate element id: {item_id}"
                )
            ids[field].add(item_id)
            all_ids.add(item_id)

    state_ids = ids["state"]
    for index, event in enumerate(microstructure["events"]):
        for field in ("source_state", "target_state"):
            if field in event and event[field] not in state_ids:
                raise MicrostructureValidationError(
                    f"{label}: events[{index}].{field} references unknown state: "
                    f"{event[field]}"
                )
    _validate_operation_references(label, microstructure["operations"], ids)


def _validate_scale(label: str, value: Any, evidence_ids: set[str]) -> None:
    if not isinstance(value, dict):
        raise MicrostructureValidationError(f"{label}: scale must be an object")
    allowed = {"level", "unit", "description", *_COMMON_CLAIM_FIELDS}
    _validate_object_fields(
        label, "scale", value, {"level", "unit", "description"}, allowed
    )
    if value["level"] not in MICROSTRUCTURE_LEVELS:
        raise MicrostructureValidationError(
            f"{label}: invalid scale.level: {value['level']}"
        )
    for field in ("unit", "description"):
        _require_string(label, f"scale.{field}", value[field])
    _validate_claim_fields(label, value, "scale", evidence_ids)


def _validate_validity_scope(label: str, value: Any, evidence_ids: set[str]) -> None:
    if not isinstance(value, dict):
        raise MicrostructureValidationError(
            f"{label}: validity_scope must be an object"
        )
    scope_fields = {
        "systems",
        "versions",
        "deployment_origins",
        "conditions",
        "exclusions",
        *_COMMON_CLAIM_FIELDS,
    }
    _validate_object_fields(
        label,
        "validity_scope",
        value,
        {"systems", "versions", "deployment_origins", "conditions", "exclusions"},
        scope_fields,
    )
    for field in (
        "systems",
        "versions",
        "deployment_origins",
        "conditions",
        "exclusions",
    ):
        values = value[field]
        if not isinstance(values, list) or not all(
            isinstance(item, str) and item for item in values
        ):
            raise MicrostructureValidationError(
                f"{label}: validity_scope.{field} must be a list of non-empty strings"
            )
    _validate_claim_fields(label, value, "validity_scope", evidence_ids)


def _validate_element(
    label: str,
    item_label: str,
    value: Any,
    kind: str,
    required_fields: set[str],
    allowed_fields: set[str],
    evidence_ids: set[str],
) -> None:
    if not isinstance(value, dict):
        raise MicrostructureValidationError(f"{label}: {item_label} must be an object")
    allowed = allowed_fields | _COMMON_CLAIM_FIELDS
    _validate_object_fields(label, item_label, value, required_fields, allowed)
    for field in ("id", "name", "description"):
        _require_string(label, f"{item_label}.{field}", value[field])
    _require_id(label, f"{item_label}.id", value["id"])
    if kind == "state":
        for field in ("initial", "terminal"):
            if field in value and not isinstance(value[field], bool):
                raise MicrostructureValidationError(
                    f"{label}: {item_label}.{field} must be boolean"
                )
    _validate_claim_fields(label, value, item_label, evidence_ids)


def _validate_operation_references(
    label: str, operations: list[dict[str, Any]], ids: dict[str, set[str]]
) -> None:
    references = {
        "input_ids": "inputs",
        "output_ids": "outputs",
        "precondition_ids": "preconditions",
        "postcondition_ids": "postconditions",
    }
    for index, operation in enumerate(operations):
        for field, target in references.items():
            values = operation.get(field, [])
            if not isinstance(values, list) or not all(
                isinstance(value, str) for value in values
            ):
                raise MicrostructureValidationError(
                    f"{label}: operations[{index}].{field} must be a list of ids"
                )
            unknown = set(values) - ids[target]
            if unknown:
                raise MicrostructureValidationError(
                    f"{label}: operations[{index}].{field} references unknown "
                    f"{target}: {sorted(unknown)}"
                )


def _validate_claim_fields(
    label: str, value: Any, item_label: str, evidence_ids: set[str]
) -> None:
    if not isinstance(value, dict):
        raise MicrostructureValidationError(f"{label}: {item_label} must be an object")
    missing = _COMMON_CLAIM_FIELDS - value.keys()
    if missing:
        raise MicrostructureValidationError(
            f"{label}: {item_label} missing claim fields: {sorted(missing)}"
        )
    if value["claim_type"] not in CLAIM_TYPES:
        raise MicrostructureValidationError(
            f"{label}: invalid {item_label} claim_type: {value['claim_type']}"
        )
    if value["claim_status"] not in CLAIM_STATUSES:
        raise MicrostructureValidationError(
            f"{label}: invalid {item_label} claim_status: {value['claim_status']}"
        )
    references = value["evidence_ids"]
    if (
        not isinstance(references, list)
        or not references
        or not all(isinstance(reference, str) and reference for reference in references)
    ):
        raise MicrostructureValidationError(
            f"{label}: {item_label}.evidence_ids must be a non-empty list"
        )
    if len(set(references)) != len(references):
        raise MicrostructureValidationError(
            f"{label}: {item_label}.evidence_ids contains duplicates"
        )
    if evidence_ids:
        unknown = set(references) - evidence_ids
        if unknown:
            raise MicrostructureValidationError(
                f"{label}: {item_label} references unknown evidence ids: "
                f"{sorted(unknown)}"
            )


def _validate_evidence(label: str, item_label: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise MicrostructureValidationError(f"{label}: {item_label} must be an object")
    allowed = {"id", "kind", "title", "uri", "accessed", "notes"}
    _validate_object_fields(
        label, item_label, value, {"id", "kind", "title", "uri"}, allowed
    )
    _require_id(label, f"{item_label}.id", value["id"])
    if value["kind"] not in EVIDENCE_KINDS:
        raise MicrostructureValidationError(f"{label}: invalid {item_label}.kind")
    for field in ("title", "uri"):
        _require_string(label, f"{item_label}.{field}", value[field])


def _validate_object_fields(
    label: str,
    item_label: str,
    value: dict[str, Any],
    required: set[str],
    allowed: set[str],
) -> None:
    missing = required - value.keys()
    if missing:
        raise MicrostructureValidationError(
            f"{label}: {item_label} missing fields: {sorted(missing)}"
        )
    unexpected = value.keys() - allowed
    if unexpected:
        raise MicrostructureValidationError(
            f"{label}: {item_label} has unexpected fields: {sorted(unexpected)}"
        )


def _require_string(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not value:
        raise MicrostructureValidationError(
            f"{label}: {field} must be a non-empty string"
        )


def _require_id(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise MicrostructureValidationError(f"{label}: {field} must be a lowercase id")


__all__ = [
    "CLAIM_STATUSES",
    "CLAIM_TYPES",
    "MICROSTRUCTURE_LEVELS",
    "MICROSTRUCTURE_SCHEMA_VERSION",
    "Microstructure",
    "MicrostructureValidationError",
    "discover_microstructures",
    "load_microstructure",
    "validate_microstructure",
]

"""Evidence-bounded, cross-domain structural analogy mappings.

Analogy mappings are deliberately separate from Architecture Cards and from
canonical relations.  They record a bounded resemblance between concepts in
different domains; they do not assert equivalence, substitutability,
composition, dependency, or historical influence.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

ANALOGY_SCHEMA_VERSION = "1.0"
ANALOGY_MAPPING_TYPES = frozenset(
    {"structural", "functional", "relational", "process", "behavioral"}
)
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)
EVIDENCE_KINDS = frozenset(
    {"official-doc", "paper", "source-code", "experiment", "secondary"}
)
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_COMMON_CLAIM_FIELDS = {"claim_type", "claim_status", "evidence_ids"}


class AnalogyValidationError(ValueError):
    """Raised when a cross-domain analogy violates its evidence contract."""


@dataclass(frozen=True, slots=True)
class AnalogyMapping:
    """Immutable representation of a validated analogy mapping."""

    schema_version: str
    id: str
    name: str
    summary: str
    source_domain: dict[str, Any]
    target_domain: dict[str, Any]
    source_concepts: tuple[dict[str, Any], ...]
    target_concepts: tuple[dict[str, Any], ...]
    correspondences: tuple[dict[str, Any], ...]
    mapping_type: str
    scale: dict[str, Any]
    shared_properties: tuple[dict[str, Any], ...]
    preserved_properties: tuple[dict[str, Any], ...]
    non_preserved_properties: tuple[dict[str, Any], ...]
    scope: dict[str, Any]
    counterexamples: tuple[dict[str, Any], ...]
    non_equivalence: dict[str, Any]
    claim_type: str
    claim_status: str
    evidence_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "AnalogyMapping":
        """Validate and construct a mapping from JSON-compatible data."""

        validate_analogy(value)
        return cls(
            schema_version=value["schema_version"],
            id=value["id"],
            name=value["name"],
            summary=value["summary"],
            source_domain=copy.deepcopy(value["source_domain"]),
            target_domain=copy.deepcopy(value["target_domain"]),
            source_concepts=tuple(copy.deepcopy(value["source_concepts"])),
            target_concepts=tuple(copy.deepcopy(value["target_concepts"])),
            correspondences=tuple(copy.deepcopy(value["correspondences"])),
            mapping_type=value["mapping_type"],
            scale=copy.deepcopy(value["scale"]),
            shared_properties=tuple(copy.deepcopy(value["shared_properties"])),
            preserved_properties=tuple(copy.deepcopy(value["preserved_properties"])),
            non_preserved_properties=tuple(
                copy.deepcopy(value["non_preserved_properties"])
            ),
            scope=copy.deepcopy(value["scope"]),
            counterexamples=tuple(copy.deepcopy(value["counterexamples"])),
            non_equivalence=copy.deepcopy(value["non_equivalence"]),
            claim_type=value["claim_type"],
            claim_status=value["claim_status"],
            evidence_ids=tuple(value["evidence_ids"]),
            evidence=tuple(copy.deepcopy(value["evidence"])),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        result = copy.deepcopy(self.__dict__) if hasattr(self, "__dict__") else {}
        if not result:
            result = {
                field: copy.deepcopy(getattr(self, field))
                for field in self.__dataclass_fields__
            }
        for field in (
            "evidence_ids",
            "source_concepts",
            "target_concepts",
            "correspondences",
            "shared_properties",
            "preserved_properties",
            "non_preserved_properties",
            "counterexamples",
            "evidence",
        ):
            result[field] = list(result[field])
        return result


def load_analogy(path: Path) -> AnalogyMapping:
    """Load and validate one analogy mapping JSON document."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise AnalogyValidationError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(value, dict):
        raise AnalogyValidationError(f"{path}: analogy must be an object")
    try:
        return AnalogyMapping.from_dict(value)
    except AnalogyValidationError as error:
        raise AnalogyValidationError(f"{path}: {error}") from error


def discover_analogies(path: Path) -> list[Path]:
    """Return analogy mapping files in deterministic order."""

    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(candidate for candidate in path.glob("*.json") if candidate.is_file())


def validate_analogy(analogy: dict[str, Any], path: Path | None = None) -> None:
    """Validate structure, evidence locality, and concept correspondences."""

    label = str(path) if path else str(analogy.get("id", "analogy"))
    if not isinstance(analogy, dict):
        raise AnalogyValidationError(f"{label}: must be an object")
    fields = {
        "schema_version",
        "id",
        "name",
        "summary",
        "source_domain",
        "target_domain",
        "source_concepts",
        "target_concepts",
        "correspondences",
        "mapping_type",
        "scale",
        "shared_properties",
        "preserved_properties",
        "non_preserved_properties",
        "scope",
        "counterexamples",
        "non_equivalence",
        "claim_type",
        "claim_status",
        "evidence_ids",
        "evidence",
    }
    _object_fields(label, "analogy", analogy, fields, fields)
    for field in ("schema_version", "id", "name", "summary"):
        _string(label, field, analogy[field])
    _id(label, "id", analogy["id"])
    if analogy["schema_version"] != ANALOGY_SCHEMA_VERSION:
        raise AnalogyValidationError(
            f"{label}: unsupported schema_version: {analogy['schema_version']}"
        )
    evidence_ids = _validate_evidence_collection(label, analogy["evidence"])
    _claims(label, analogy, "analogy", evidence_ids, expected_type="analogy")

    _domain(label, "source_domain", analogy["source_domain"], evidence_ids)
    _domain(label, "target_domain", analogy["target_domain"], evidence_ids)
    source_ids = _concepts(
        label, "source_concepts", analogy["source_concepts"], evidence_ids
    )
    target_ids = _concepts(
        label, "target_concepts", analogy["target_concepts"], evidence_ids
    )
    if analogy["mapping_type"] not in ANALOGY_MAPPING_TYPES:
        raise AnalogyValidationError(f"{label}: invalid mapping_type")
    _scale(label, analogy["scale"], evidence_ids)
    _properties(label, "shared_properties", analogy["shared_properties"], evidence_ids)
    _properties(
        label, "preserved_properties", analogy["preserved_properties"], evidence_ids
    )
    _properties(
        label,
        "non_preserved_properties",
        analogy["non_preserved_properties"],
        evidence_ids,
    )
    _scope(label, analogy["scope"], evidence_ids)
    _counterexamples(label, analogy["counterexamples"], evidence_ids)
    non_equivalence = analogy["non_equivalence"]
    if not isinstance(non_equivalence, dict):
        raise AnalogyValidationError(f"{label}: non_equivalence must be an object")
    _object_fields(
        label,
        "non_equivalence",
        non_equivalence,
        {"statement", "reasons", "substitutability"} | _COMMON_CLAIM_FIELDS,
        {"statement", "reasons", "substitutability"} | _COMMON_CLAIM_FIELDS,
    )
    _string(label, "non_equivalence.statement", non_equivalence["statement"])
    _string(
        label, "non_equivalence.substitutability", non_equivalence["substitutability"]
    )
    _string_list(label, "non_equivalence.reasons", non_equivalence["reasons"])
    _claims(label, non_equivalence, "non_equivalence", evidence_ids)

    correspondences = analogy["correspondences"]
    if not isinstance(correspondences, list) or not correspondences:
        raise AnalogyValidationError(f"{label}: correspondences must be non-empty")
    correspondence_ids: set[str] = set()
    for index, correspondence in enumerate(correspondences):
        item = f"correspondences[{index}]"
        if not isinstance(correspondence, dict):
            raise AnalogyValidationError(f"{label}: {item} must be an object")
        allowed = {
            "id",
            "source_concept_ids",
            "target_concept_ids",
            "relation",
            "rationale",
            *_COMMON_CLAIM_FIELDS,
        }
        _object_fields(
            label,
            item,
            correspondence,
            {
                "id",
                "source_concept_ids",
                "target_concept_ids",
                "relation",
                "rationale",
            },
            allowed,
        )
        _id(label, f"{item}.id", correspondence["id"])
        if correspondence["id"] in correspondence_ids:
            raise AnalogyValidationError(f"{label}: duplicate correspondence id")
        correspondence_ids.add(correspondence["id"])
        for field, known in (
            ("source_concept_ids", source_ids),
            ("target_concept_ids", target_ids),
        ):
            values = correspondence[field]
            if not isinstance(values, list) or not values:
                raise AnalogyValidationError(
                    f"{label}: {item}.{field} must be non-empty"
                )
            unknown = set(values) - known
            if unknown:
                raise AnalogyValidationError(
                    f"{label}: {item}.{field} references unknown concepts: "
                    f"{sorted(unknown)}"
                )
        _string(label, f"{item}.relation", correspondence["relation"])
        _string(label, f"{item}.rationale", correspondence["rationale"])
        _claims(label, correspondence, item, evidence_ids)


def _domain(label: str, item: str, value: Any, evidence_ids: set[str]) -> None:
    _object_fields(
        label,
        item,
        value,
        {"name", "description"},
        {"name", "description", *_COMMON_CLAIM_FIELDS},
    )
    _string(label, f"{item}.name", value["name"])
    _string(label, f"{item}.description", value["description"])
    _claims(label, value, item, evidence_ids)


def _concepts(label: str, field: str, values: Any, evidence_ids: set[str]) -> set[str]:
    if not isinstance(values, list) or not values:
        raise AnalogyValidationError(f"{label}: {field} must be non-empty")
    ids: set[str] = set()
    for index, value in enumerate(values):
        item = f"{field}[{index}]"
        _object_fields(
            label,
            item,
            value,
            {"id", "name", "description"},
            {"id", "name", "description", "role", *_COMMON_CLAIM_FIELDS},
        )
        _id(label, f"{item}.id", value["id"])
        if value["id"] in ids:
            raise AnalogyValidationError(f"{label}: duplicate concept id")
        ids.add(value["id"])
        _string(label, f"{item}.name", value["name"])
        _string(label, f"{item}.description", value["description"])
        if "role" in value:
            _string(label, f"{item}.role", value["role"])
        _claims(label, value, item, evidence_ids)
    return ids


def _scale(label: str, value: Any, evidence_ids: set[str]) -> None:
    _object_fields(
        label,
        "scale",
        value,
        {"source", "target", "description"},
        {"source", "target", "description", *_COMMON_CLAIM_FIELDS},
    )
    for field in ("source", "target", "description"):
        _string(label, f"scale.{field}", value[field])
    _claims(label, value, "scale", evidence_ids)


def _properties(label: str, field: str, values: Any, evidence_ids: set[str]) -> None:
    if not isinstance(values, list) or not values:
        raise AnalogyValidationError(f"{label}: {field} must be non-empty")
    for index, value in enumerate(values):
        item = f"{field}[{index}]"
        _object_fields(
            label,
            item,
            value,
            {"id", "name", "description"},
            {"id", "name", "description", "boundary", *_COMMON_CLAIM_FIELDS},
        )
        _id(label, f"{item}.id", value["id"])
        _string(label, f"{item}.name", value["name"])
        _string(label, f"{item}.description", value["description"])
        if "boundary" in value:
            _string(label, f"{item}.boundary", value["boundary"])
        _claims(label, value, item, evidence_ids)


def _scope(label: str, value: Any, evidence_ids: set[str]) -> None:
    fields = {
        "source_versions",
        "target_versions",
        "deployment_origins",
        "conditions",
        "exclusions",
    }
    _object_fields(label, "scope", value, fields, fields | _COMMON_CLAIM_FIELDS)
    for field in fields:
        _string_list(label, f"scope.{field}", value[field])
    _claims(label, value, "scope", evidence_ids)


def _counterexamples(label: str, values: Any, evidence_ids: set[str]) -> None:
    if not isinstance(values, list) or not values:
        raise AnalogyValidationError(f"{label}: counterexamples must be non-empty")
    for index, value in enumerate(values):
        item = f"counterexamples[{index}]"
        _object_fields(
            label,
            item,
            value,
            {"id", "description", "implication"},
            {"id", "description", "implication", *_COMMON_CLAIM_FIELDS},
        )
        _id(label, f"{item}.id", value["id"])
        _string(label, f"{item}.description", value["description"])
        _string(label, f"{item}.implication", value["implication"])
        _claims(label, value, item, evidence_ids)


def _validate_evidence_collection(label: str, values: Any) -> set[str]:
    if not isinstance(values, list) or not values:
        raise AnalogyValidationError(f"{label}: evidence must be non-empty")
    ids: set[str] = set()
    for index, value in enumerate(values):
        item = f"evidence[{index}]"
        _object_fields(
            label,
            item,
            value,
            {"id", "kind", "title", "uri"},
            {"id", "kind", "title", "uri", "accessed", "notes"},
        )
        _id(label, f"{item}.id", value["id"])
        if value["id"] in ids:
            raise AnalogyValidationError(f"{label}: duplicate evidence id")
        ids.add(value["id"])
        if value["kind"] not in EVIDENCE_KINDS:
            raise AnalogyValidationError(f"{label}: invalid {item}.kind")
        _string(label, f"{item}.title", value["title"])
        _string(label, f"{item}.uri", value["uri"])
    return ids


def _claims(
    label: str,
    value: Any,
    item: str,
    evidence_ids: set[str],
    expected_type: str | None = None,
) -> None:
    if not isinstance(value, dict):
        raise AnalogyValidationError(f"{label}: {item} must be an object")
    missing = _COMMON_CLAIM_FIELDS - value.keys()
    if missing:
        raise AnalogyValidationError(
            f"{label}: {item} missing claim fields: {sorted(missing)}"
        )
    if value["claim_type"] not in CLAIM_TYPES:
        raise AnalogyValidationError(f"{label}: invalid {item}.claim_type")
    if expected_type and value["claim_type"] != expected_type:
        raise AnalogyValidationError(
            f"{label}: {item}.claim_type must be {expected_type}"
        )
    if value["claim_status"] not in CLAIM_STATUSES:
        raise AnalogyValidationError(f"{label}: invalid {item}.claim_status")
    references = value["evidence_ids"]
    if (
        not isinstance(references, list)
        or not references
        or not all(isinstance(item, str) and item for item in references)
    ):
        raise AnalogyValidationError(f"{label}: {item}.evidence_ids must be non-empty")
    if len(set(references)) != len(references):
        raise AnalogyValidationError(
            f"{label}: {item}.evidence_ids contains duplicates"
        )
    unknown = set(references) - evidence_ids
    if unknown:
        raise AnalogyValidationError(
            f"{label}: {item} references unknown evidence ids: {sorted(unknown)}"
        )


def _object_fields(
    label: str, item: str, value: Any, required: set[str], allowed: set[str]
) -> None:
    if not isinstance(value, dict):
        raise AnalogyValidationError(f"{label}: {item} must be an object")
    missing = required - value.keys()
    if missing:
        raise AnalogyValidationError(
            f"{label}: {item} missing fields: {sorted(missing)}"
        )
    unexpected = value.keys() - allowed
    if unexpected:
        raise AnalogyValidationError(
            f"{label}: {item} has unexpected fields: {sorted(unexpected)}"
        )


def _string(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise AnalogyValidationError(f"{label}: {field} must be a non-empty string")


def _string_list(label: str, field: str, value: Any) -> None:
    if (
        not isinstance(value, list)
        or not value
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise AnalogyValidationError(
            f"{label}: {field} must be a non-empty list of strings"
        )


def _id(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise AnalogyValidationError(f"{label}: {field} must be a lowercase id")


__all__ = [
    "ANALOGY_MAPPING_TYPES",
    "ANALOGY_SCHEMA_VERSION",
    "AnalogyMapping",
    "AnalogyValidationError",
    "discover_analogies",
    "load_analogy",
    "validate_analogy",
]

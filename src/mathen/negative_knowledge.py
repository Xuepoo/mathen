"""Evidence-bounded records of failed, misleading, or superseded claims.

Negative knowledge is deliberately a standalone review artifact.  It can point
at cards, compositions, experiments, or analogy mappings, but it never mutates
or promotes a canonical Architecture Card.  Every record is bounded by an
explicit scope and evidence set; the validator rejects unbounded universal
language so that one counterexample is not silently generalized.
"""

from __future__ import annotations

import copy
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

NEGATIVE_KNOWLEDGE_SCHEMA_VERSION = "1.0"
NEGATIVE_KNOWLEDGE_KINDS = frozenset(
    {
        "invalid-composition",
        "misleading-similarity",
        "scope-violation",
        "failed-hypothesis",
        "falsified-experiment",
        "retraction",
        "supersession",
    }
)
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)
EVIDENCE_KINDS = frozenset(
    {"official-doc", "paper", "source-code", "experiment", "secondary"}
)
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_BROAD_LANGUAGE = re.compile(
    r"\b(?:all|any|every|always|never|none|no\s+system|universally|in\s+every)\b",
    re.IGNORECASE,
)


class NegativeKnowledgeValidationError(ValueError):
    """Raised when a negative-knowledge record violates its contract."""


@dataclass(frozen=True, slots=True)
class NegativeKnowledgeRecord:
    """Immutable representation of one validated bounded negative claim."""

    schema_version: str
    id: str
    name: str
    summary: str
    kind: str
    negative_claim: str
    bounded: bool
    scope: dict[str, Any]
    counterexamples: tuple[dict[str, Any], ...]
    claim_type: str
    claim_status: str
    evidence_ids: tuple[str, ...]
    evidence: tuple[dict[str, Any], ...]
    composition: dict[str, Any] | None = None
    related_claim_ids: tuple[str, ...] = ()
    replacement_id: str | None = None
    notes: str | None = None

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "NegativeKnowledgeRecord":
        """Validate and construct a record from JSON-compatible data."""

        validate_negative_knowledge(value)
        return cls(
            schema_version=value["schema_version"],
            id=value["id"],
            name=value["name"],
            summary=value["summary"],
            kind=value["kind"],
            negative_claim=value["negative_claim"],
            bounded=value["bounded"],
            scope=copy.deepcopy(value["scope"]),
            counterexamples=tuple(copy.deepcopy(value["counterexamples"])),
            claim_type=value["claim_type"],
            claim_status=value["claim_status"],
            evidence_ids=tuple(value["evidence_ids"]),
            evidence=tuple(copy.deepcopy(value["evidence"])),
            composition=copy.deepcopy(value.get("composition")),
            related_claim_ids=tuple(value.get("related_claim_ids", [])),
            replacement_id=value.get("replacement_id"),
            notes=value.get("notes"),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        result = {
            "schema_version": self.schema_version,
            "id": self.id,
            "name": self.name,
            "summary": self.summary,
            "kind": self.kind,
            "negative_claim": self.negative_claim,
            "bounded": self.bounded,
            "scope": copy.deepcopy(self.scope),
            "counterexamples": copy.deepcopy(list(self.counterexamples)),
            "claim_type": self.claim_type,
            "claim_status": self.claim_status,
            "evidence_ids": list(self.evidence_ids),
            "evidence": copy.deepcopy(list(self.evidence)),
        }
        for field, value in (
            ("composition", self.composition),
            ("replacement_id", self.replacement_id),
            ("notes", self.notes),
        ):
            if value is not None:
                result[field] = copy.deepcopy(value)
        if self.related_claim_ids:
            result["related_claim_ids"] = list(self.related_claim_ids)
        return result


def load_negative_knowledge(path: Path) -> NegativeKnowledgeRecord:
    """Load and validate one standalone negative-knowledge JSON document."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise NegativeKnowledgeValidationError(
            f"{path}: invalid JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise NegativeKnowledgeValidationError(f"{path}: record must be an object")
    try:
        return NegativeKnowledgeRecord.from_dict(value)
    except NegativeKnowledgeValidationError as error:
        raise NegativeKnowledgeValidationError(f"{path}: {error}") from error


def discover_negative_knowledge(path: Path) -> list[Path]:
    """Return negative-knowledge files in deterministic order."""

    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(candidate for candidate in path.glob("*.json") if candidate.is_file())


def validate_negative_knowledge(
    value: dict[str, Any], path: Path | None = None
) -> None:
    """Validate evidence locality, bounded scope, and lifecycle semantics."""

    label = str(path) if path else str(value.get("id", "negative-knowledge"))
    if not isinstance(value, dict):
        raise NegativeKnowledgeValidationError(f"{label}: must be an object")
    required = {
        "schema_version",
        "id",
        "name",
        "summary",
        "kind",
        "negative_claim",
        "bounded",
        "scope",
        "counterexamples",
        "claim_type",
        "claim_status",
        "evidence_ids",
        "evidence",
    }
    allowed = required | {
        "composition",
        "related_claim_ids",
        "replacement_id",
        "notes",
    }
    _object_fields(label, "record", value, required, allowed)
    for field in ("schema_version", "id", "name", "summary", "negative_claim"):
        _string(label, field, value[field])
    _id(label, "id", value["id"])
    if value["schema_version"] != NEGATIVE_KNOWLEDGE_SCHEMA_VERSION:
        raise NegativeKnowledgeValidationError(
            f"{label}: unsupported schema_version: {value['schema_version']}"
        )
    if value["kind"] not in NEGATIVE_KNOWLEDGE_KINDS:
        raise NegativeKnowledgeValidationError(f"{label}: invalid kind")
    if value["bounded"] is not True:
        raise NegativeKnowledgeValidationError(
            f"{label}: bounded must be true; negative claims cannot be universal"
        )
    _bounded_text(label, "negative_claim", value["negative_claim"])

    evidence_ids = _validate_evidence_collection(label, value["evidence"])
    _claim_fields(label, "record", value, evidence_ids)
    _scope(label, value["scope"])
    _counterexamples(label, value["counterexamples"], evidence_ids)

    if value["kind"] == "invalid-composition":
        _composition(label, value.get("composition"))
    elif "composition" in value:
        _composition(label, value["composition"])

    related = value.get("related_claim_ids", [])
    if "related_claim_ids" in value:
        _ids(label, "related_claim_ids", related, min_items=1)
    replacement = value.get("replacement_id")
    if replacement is not None:
        _id(label, "replacement_id", replacement)
    if value["kind"] in {"retraction", "supersession"} and not related:
        raise NegativeKnowledgeValidationError(
            f"{label}: {value['kind']} requires related_claim_ids"
        )
    if value["kind"] == "supersession" and replacement is None:
        raise NegativeKnowledgeValidationError(
            f"{label}: supersession requires replacement_id"
        )
    if value["kind"] == "falsified-experiment" and not any(
        item["kind"] == "experiment" for item in value["evidence"]
    ):
        raise NegativeKnowledgeValidationError(
            f"{label}: falsified-experiment requires experiment evidence"
        )
    if "notes" in value:
        _string(label, "notes", value["notes"])


def validate_negative_knowledge_collection(
    records: Iterable[NegativeKnowledgeRecord | dict[str, Any]],
) -> None:
    """Validate local records and resolve lifecycle links within a collection."""

    values: list[dict[str, Any]] = []
    record_by_id: dict[str, dict[str, Any]] = {}
    for record in records:
        value = (
            record.to_dict() if isinstance(record, NegativeKnowledgeRecord) else record
        )
        validate_negative_knowledge(value)
        record_id = value["id"]
        if record_id in record_by_id:
            raise NegativeKnowledgeValidationError(
                f"duplicate negative-knowledge id: {record_id}"
            )
        record_by_id[record_id] = value
        values.append(value)

    for value in values:
        record_id = value["id"]
        for related_id in value.get("related_claim_ids", []):
            if related_id not in record_by_id:
                raise NegativeKnowledgeValidationError(
                    f"{record_id}: related_claim_ids references unknown "
                    f"negative-knowledge record: {related_id}"
                )
        replacement_id = value.get("replacement_id")
        if replacement_id is not None and replacement_id not in record_by_id:
            raise NegativeKnowledgeValidationError(
                f"{record_id}: replacement_id references unknown "
                f"negative-knowledge record: {replacement_id}"
            )


def _scope(label: str, value: Any) -> None:
    required = {
        "systems",
        "versions",
        "deployment_origins",
        "conditions",
        "exclusions",
    }
    _object_fields(label, "scope", value, required, required)
    for field in required:
        _string_list(label, f"scope.{field}", value[field])


def _counterexamples(label: str, values: Any, evidence_ids: set[str]) -> None:
    if not isinstance(values, list) or not values:
        raise NegativeKnowledgeValidationError(
            f"{label}: counterexamples must be non-empty"
        )
    seen: set[str] = set()
    for index, value in enumerate(values):
        item = f"counterexamples[{index}]"
        fields = {
            "id",
            "description",
            "implication",
            "claim_type",
            "claim_status",
            "evidence_ids",
        }
        _object_fields(label, item, value, fields, fields)
        _id(label, f"{item}.id", value["id"])
        if value["id"] in seen:
            raise NegativeKnowledgeValidationError(f"{label}: duplicate {item}.id")
        seen.add(value["id"])
        _bounded_text(label, f"{item}.description", value["description"])
        _bounded_text(label, f"{item}.implication", value["implication"])
        _claim_fields(label, item, value, evidence_ids)


def _composition(label: str, value: Any) -> None:
    fields = {"inputs", "operation", "failure_mode"}
    _object_fields(label, "composition", value, fields, fields)
    _string_list(label, "composition.inputs", value["inputs"], min_items=2)
    _string(label, "composition.operation", value["operation"])
    _string(label, "composition.failure_mode", value["failure_mode"])


def _validate_evidence_collection(label: str, values: Any) -> set[str]:
    if not isinstance(values, list) or not values:
        raise NegativeKnowledgeValidationError(f"{label}: evidence must be non-empty")
    ids: set[str] = set()
    fields = {"id", "kind", "title", "uri"}
    allowed = fields | {"accessed", "notes"}
    for index, value in enumerate(values):
        item = f"evidence[{index}]"
        _object_fields(label, item, value, fields, allowed)
        _id(label, f"{item}.id", value["id"])
        if value["id"] in ids:
            raise NegativeKnowledgeValidationError(f"{label}: duplicate evidence id")
        ids.add(value["id"])
        if value["kind"] not in EVIDENCE_KINDS:
            raise NegativeKnowledgeValidationError(f"{label}: invalid {item}.kind")
        _string(label, f"{item}.title", value["title"])
        _string(label, f"{item}.uri", value["uri"])
    return ids


def _claim_fields(label: str, item: str, value: Any, evidence_ids: set[str]) -> None:
    if value.get("claim_type") not in CLAIM_TYPES:
        raise NegativeKnowledgeValidationError(f"{label}: invalid {item}.claim_type")
    if value.get("claim_status") not in CLAIM_STATUSES:
        raise NegativeKnowledgeValidationError(f"{label}: invalid {item}.claim_status")
    _evidence_refs(label, item, value.get("evidence_ids"), evidence_ids)


def _evidence_refs(
    label: str, item: str, references: Any, evidence_ids: set[str]
) -> None:
    if (
        not isinstance(references, list)
        or not references
        or not all(isinstance(reference, str) and reference for reference in references)
    ):
        raise NegativeKnowledgeValidationError(
            f"{label}: {item}.evidence_ids must be non-empty"
        )
    if len(set(references)) != len(references):
        raise NegativeKnowledgeValidationError(
            f"{label}: {item}.evidence_ids contains duplicates"
        )
    unknown = set(references) - evidence_ids
    if unknown:
        raise NegativeKnowledgeValidationError(
            f"{label}: {item} references unknown evidence ids: {sorted(unknown)}"
        )


def _object_fields(
    label: str, item: str, value: Any, required: set[str], allowed: set[str]
) -> None:
    if not isinstance(value, dict):
        raise NegativeKnowledgeValidationError(f"{label}: {item} must be an object")
    missing = required - value.keys()
    if missing:
        raise NegativeKnowledgeValidationError(
            f"{label}: {item} missing fields: {sorted(missing)}"
        )
    unexpected = value.keys() - allowed
    if unexpected:
        raise NegativeKnowledgeValidationError(
            f"{label}: {item} has unexpected fields: {sorted(unexpected)}"
        )


def _string(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not value.strip():
        raise NegativeKnowledgeValidationError(
            f"{label}: {field} must be a non-empty string"
        )


def _bounded_text(label: str, field: str, value: str) -> None:
    _string(label, field, value)
    if _BROAD_LANGUAGE.search(value):
        raise NegativeKnowledgeValidationError(
            f"{label}: {field} contains broad universal language; state a bounded claim"
        )


def _string_list(label: str, field: str, value: Any, *, min_items: int = 1) -> None:
    if (
        not isinstance(value, list)
        or len(value) < min_items
        or not all(isinstance(item, str) and item.strip() for item in value)
    ):
        raise NegativeKnowledgeValidationError(
            f"{label}: {field} must be a non-empty list of strings"
        )


def _ids(label: str, field: str, values: Any, *, min_items: int = 0) -> None:
    if not isinstance(values, list):
        raise NegativeKnowledgeValidationError(
            f"{label}: {field} must be a list of ids"
        )
    if len(values) < min_items:
        raise NegativeKnowledgeValidationError(
            f"{label}: {field} must contain at least {min_items} id"
        )
    if not values:
        return
    for value in values:
        _id(label, field, value)
    if len(set(values)) != len(values):
        raise NegativeKnowledgeValidationError(f"{label}: {field} contains duplicates")


def _id(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise NegativeKnowledgeValidationError(
            f"{label}: {field} must be a lowercase id"
        )


__all__ = [
    "CLAIM_STATUSES",
    "CLAIM_TYPES",
    "NEGATIVE_KNOWLEDGE_KINDS",
    "NEGATIVE_KNOWLEDGE_SCHEMA_VERSION",
    "NegativeKnowledgeRecord",
    "NegativeKnowledgeValidationError",
    "discover_negative_knowledge",
    "load_negative_knowledge",
    "validate_negative_knowledge_collection",
    "validate_negative_knowledge",
]

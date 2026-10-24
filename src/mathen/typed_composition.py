"""Evidence-bounded typed semantics for proposed compositions.

This module is intentionally additive to the older ``composition`` contract.
It describes interfaces and effects; it does not execute components, infer an
adapter from names, or turn a candidate into a proof of compatibility.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

TYPED_COMPOSITION_SCHEMA_VERSION = "1.0"
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)
PROPERTY_RELATIONS = frozenset(
    {"shared", "preserves", "refines", "weakens", "strengthens", "unverified"}
)


class TypedCompositionValidationError(ValueError):
    """Raised when a typed composition contract is malformed."""


@dataclass(frozen=True, slots=True)
class TypedFeatureSpec:
    """Explicit, evidence-linked semantics for one composition component."""

    id: str
    provides: frozenset[str] = frozenset()
    requires: frozenset[str] = frozenset()
    consumes: frozenset[str] = frozenset()
    adapters: tuple[str, ...] = ()
    boundaries: tuple[str, ...] = ()
    preserves: tuple[str, ...] = ()
    shared: tuple[str, ...] = ()
    refines: tuple[str, ...] = ()
    weakens: tuple[str, ...] = ()
    strengthens: tuple[str, ...] = ()
    unverified: tuple[str, ...] = ()
    preconditions: tuple[str, ...] = ()
    postconditions: tuple[str, ...] = ()
    resource_effects: tuple[str, ...] = ()
    failure_modes: tuple[str, ...] = ()
    conflicts: frozenset[str] = frozenset()
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class TypedCompositionSemantics:
    """Immutable model of a validated ``composition.typed_semantics`` object."""

    value: dict[str, Any]

    @classmethod
    def from_dict(
        cls, value: Mapping[str, Any], *, evidence_ids: set[str] | None = None
    ) -> "TypedCompositionSemantics":
        validate_typed_composition(value, evidence_ids=evidence_ids)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        return copy.deepcopy(self.value)


def load_typed_composition(path: Path) -> TypedCompositionSemantics:
    """Load and validate one standalone typed composition contract."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise TypedCompositionValidationError(
            f"{path}: invalid JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise TypedCompositionValidationError(f"{path}: contract must be an object")
    try:
        return TypedCompositionSemantics.from_dict(value)
    except TypedCompositionValidationError as error:
        raise TypedCompositionValidationError(f"{path}: {error}") from error


def validate_typed_composition(
    value: Mapping[str, Any], *, evidence_ids: set[str] | None = None
) -> None:
    """Validate shape, references, and local evidence for typed semantics.

    The validator checks declared references only.  It deliberately does not
    decide whether two arbitrary strings denote compatible interfaces.
    """

    if not isinstance(value, Mapping):
        raise TypedCompositionValidationError("typed_semantics must be an object")
    required = {
        "schema_version",
        "components",
        "adapters",
        "boundaries",
        "property_effects",
        "preconditions",
        "postconditions",
        "resource_effects",
        "failure_modes",
        "examples",
        "counterexamples",
        "uncertainties",
        "disagreements",
        "discovery",
        "validity_scope",
        "claim_status",
        "evidence_ids",
        "proven",
    }
    missing = required - value.keys()
    if missing:
        raise TypedCompositionValidationError(f"missing fields: {sorted(missing)}")
    if value["schema_version"] != TYPED_COMPOSITION_SCHEMA_VERSION:
        raise TypedCompositionValidationError("unsupported schema_version")
    if value["proven"] is not False:
        raise TypedCompositionValidationError(
            "proven must remain false until validation"
        )
    if "proven" in value and value["proven"] is not False:
        raise TypedCompositionValidationError(
            "proven must remain false until validation"
        )
    _claim_fields("typed_semantics", value, evidence_ids)

    discovery = value["discovery"]
    _object("discovery", discovery)
    for field in ("method", "source_community", "target_community", "candidate_status"):
        _text("discovery", discovery.get(field))
    if discovery["candidate_status"] != "candidate":
        raise TypedCompositionValidationError(
            "discovery.candidate_status must be candidate"
        )
    _string_list("discovery", discovery.get("provenance", []), "provenance")
    _string_list("discovery", discovery.get("path", []), "path")

    components = _list(value, "components")
    component_ids: set[str] = set()
    for index, component in enumerate(components):
        label = f"components[{index}]"
        _object(label, component)
        _text(label, component.get("id"))
        if component["id"] in component_ids:
            raise TypedCompositionValidationError(
                f"duplicate component id: {component['id']}"
            )
        component_ids.add(component["id"])
        _text(label, component.get("role"))
        for field in ("requires", "provides", "consumes", "adapters", "boundaries"):
            _string_list(label, component.get(field, []), field)
        _claim_fields(label, component, evidence_ids)

    for index, item in enumerate(_list(value, "adapters")):
        _reference_object(
            f"adapters[{index}]", item, component_ids, ("source", "target")
        )
    for index, item in enumerate(_list(value, "boundaries")):
        _reference_object(
            f"boundaries[{index}]", item, component_ids, ("inside", "outside")
        )

    property_ids: set[str] = set()
    for index, item in enumerate(_list(value, "property_effects")):
        label = f"property_effects[{index}]"
        _object(label, item)
        _text(label, item.get("id"))
        if item["id"] in property_ids:
            raise TypedCompositionValidationError(
                f"duplicate property effect id: {item['id']}"
            )
        property_ids.add(item["id"])
        _text(label, item.get("property"))
        if item.get("relation") not in PROPERTY_RELATIONS:
            raise TypedCompositionValidationError(f"{label}: invalid relation")
        _claim_fields(label, item, evidence_ids)

    for field in (
        "preconditions",
        "postconditions",
        "resource_effects",
        "failure_modes",
    ):
        for index, item in enumerate(_list(value, field)):
            label = f"{field}[{index}]"
            _object(label, item)
            _text(label, item.get("id"))
            _text(label, item.get("description"))
            _claim_fields(label, item, evidence_ids)

    for field in ("examples", "counterexamples"):
        for index, item in enumerate(_list(value, field)):
            label = f"{field}[{index}]"
            _object(label, item)
            _text(label, item.get("id"))
            _text(label, item.get("description"))
            _claim_fields(label, item, evidence_ids)
    for field in ("uncertainties", "disagreements"):
        for index, item in enumerate(_list(value, field)):
            label = f"{field}[{index}]"
            _object(label, item)
            _text(label, item.get("id"))
            _text(label, item.get("description"))
            _claim_fields(label, item, evidence_ids)
    scope = value["validity_scope"]
    _object("validity_scope", scope)
    for field in (
        "systems",
        "versions",
        "deployment_origins",
        "conditions",
        "exclusions",
    ):
        _string_list("validity_scope", scope.get(field, []), field)


def _list(value: Mapping[str, Any], field: str) -> list[Any]:
    result = value.get(field)
    if not isinstance(result, list):
        raise TypedCompositionValidationError(f"{field} must be a list")
    return result


def _object(label: str, value: Any) -> None:
    if not isinstance(value, Mapping):
        raise TypedCompositionValidationError(f"{label} must be an object")


def _text(label: str, value: Any) -> None:
    if not isinstance(value, str) or not value:
        raise TypedCompositionValidationError(f"{label} needs a non-empty string")


def _string_list(label: str, value: Any, field: str) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item for item in value
    ):
        raise TypedCompositionValidationError(
            f"{label}.{field} must be a list of strings"
        )


def _claim_fields(
    label: str, value: Mapping[str, Any], evidence_ids: set[str] | None
) -> None:
    if value.get("claim_type") not in CLAIM_TYPES:
        raise TypedCompositionValidationError(f"{label}: invalid claim_type")
    if value.get("claim_status") not in CLAIM_STATUSES:
        raise TypedCompositionValidationError(f"{label}: invalid claim_status")
    ids = value.get("evidence_ids")
    _string_list(label, ids, "evidence_ids")
    if not ids:
        raise TypedCompositionValidationError(
            f"{label}: evidence_ids must not be empty"
        )
    if evidence_ids is not None:
        unknown = sorted(set(ids) - evidence_ids)
        if unknown:
            raise TypedCompositionValidationError(
                f"{label}: unknown evidence ids: {unknown}"
            )


def _reference_object(
    label: str,
    value: Any,
    component_ids: set[str],
    references: tuple[str, str],
) -> None:
    _object(label, value)
    _text(label, value.get("id"))
    for field in references:
        ref = value.get(field)
        _text(label, ref)
        if ref not in component_ids:
            raise TypedCompositionValidationError(
                f"{label}: unknown component {field}: {ref}"
            )
    _text(label, value.get("description"))
    _claim_fields(label, value, None)


def typed_spec_from_mapping(value: Mapping[str, Any]) -> TypedFeatureSpec:
    """Normalize an explicit solver spec without deriving semantics from text."""

    def strings(field: str) -> tuple[str, ...]:
        raw = value.get(field, ())
        if isinstance(raw, (str, bytes)):
            raise ValueError(f"{field} must be an iterable of strings")
        try:
            items = tuple(raw)
        except TypeError as error:
            raise ValueError(f"{field} must be an iterable of strings") from error
        if any(not isinstance(item, str) or not item for item in items):
            raise ValueError(f"{field} must contain non-empty strings")
        return tuple(sorted(set(items)))

    identifier = value.get("id")
    if not isinstance(identifier, str) or not identifier:
        raise ValueError("typed feature id must be a non-empty string")
    return TypedFeatureSpec(
        id=identifier,
        provides=frozenset(strings("provides")),
        requires=frozenset(strings("requires")),
        consumes=frozenset(strings("consumes")),
        adapters=strings("adapters"),
        boundaries=strings("boundaries"),
        preserves=strings("preserves"),
        shared=strings("shared"),
        refines=strings("refines"),
        weakens=strings("weakens"),
        strengthens=strings("strengthens"),
        unverified=strings("unverified"),
        preconditions=strings("preconditions"),
        postconditions=strings("postconditions"),
        resource_effects=strings("resource_effects"),
        failure_modes=strings("failure_modes"),
        conflicts=frozenset(strings("conflicts")),
        evidence_ids=strings("evidence_ids"),
    )

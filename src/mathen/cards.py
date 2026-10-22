"""Loading and validating Architecture Cards."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = {
    "id",
    "name",
    "summary",
    "scope",
    "features",
    "mathematical_views",
    "trade_offs",
    "evidence",
}
CLAIM_TYPES = {"fact", "inference", "hypothesis", "analogy"}
CLAIM_STATUSES = {"proposed", "under-review", "accepted", "rejected", "deprecated"}
RELATION_TYPES = {"uses", "extends", "composes", "resembles", "influenced-by"}


class CardValidationError(ValueError):
    """Raised when an Architecture Card violates project invariants."""


def load_card(path: Path) -> dict[str, Any]:
    """Load one JSON card and perform semantic validation."""

    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise CardValidationError(f"{path}: invalid JSON: {error}") from error
    if not isinstance(data, dict):
        raise CardValidationError(f"{path}: card must be a JSON object")
    validate_card(data, path)
    return data


def validate_card(card: dict[str, Any], path: Path | None = None) -> None:
    """Validate semantic rules not covered by the JSON Schema dependency."""

    label = str(path) if path else card.get("id", "card")
    missing = REQUIRED_TOP_LEVEL - card.keys()
    if missing:
        raise CardValidationError(f"{label}: missing fields: {sorted(missing)}")
    if not isinstance(card["id"], str) or not card["id"].islower():
        raise CardValidationError(f"{label}: id must be lowercase")

    evidence = card["evidence"]
    if not isinstance(evidence, list) or not evidence:
        raise CardValidationError(f"{label}: evidence must be a non-empty list")
    evidence_ids = {item.get("id") for item in evidence if isinstance(item, dict)}

    feature_ids: set[str] = set()
    for feature in card["features"]:
        if not isinstance(feature, dict):
            raise CardValidationError(f"{label}: every feature must be an object")
        feature_id = feature.get("id")
        if feature_id in feature_ids:
            raise CardValidationError(f"{label}: duplicate feature id: {feature_id}")
        feature_ids.add(feature_id)
        if feature.get("claim_type") not in CLAIM_TYPES:
            raise CardValidationError(
                f"{label}: invalid feature claim type: {feature_id}"
            )
        _check_optional_claim_status(label, feature_id, feature.get("claim_status"))
        _check_evidence_ids(
            label, feature_id, feature.get("evidence_ids"), evidence_ids
        )

    for view in card["mathematical_views"]:
        if view.get("claim_type") not in CLAIM_TYPES:
            raise CardValidationError(f"{label}: invalid mathematical view claim type")
        _check_optional_claim_status(
            label, view.get("model", "view"), view.get("claim_status")
        )
        _check_evidence_ids(
            label, view.get("model", "view"), view.get("evidence_ids"), evidence_ids
        )

    for trade_off in card["trade_offs"]:
        if trade_off.get("feature_id") not in feature_ids:
            raise CardValidationError(
                f"{label}: trade-off references unknown feature: "
                f"{trade_off.get('feature_id')}"
            )

    if "temporal_context" in card:
        temporal = _require_object(label, "temporal_context", card["temporal_context"])
        _check_claim_status(label, "temporal_context", temporal.get("claim_status"))
        _check_evidence_ids(
            label, "temporal_context", temporal.get("evidence_ids"), evidence_ids
        )
        for field in ("supersedes", "superseded_by"):
            references = temporal.get(field, [])
            if not isinstance(references, list) or not all(
                isinstance(reference, str) and reference for reference in references
            ):
                raise CardValidationError(f"{label}: {field} must be a list of ids")

    for index, relation in enumerate(card.get("relations", [])):
        relation_label = f"relation[{index}]"
        relation = _require_object(label, relation_label, relation)
        if relation.get("type") not in RELATION_TYPES:
            raise CardValidationError(f"{label}: invalid {relation_label} type")
        if not isinstance(relation.get("target"), str) or not relation["target"]:
            raise CardValidationError(f"{label}: {relation_label} needs a target")
        if relation.get("claim_type") not in CLAIM_TYPES:
            raise CardValidationError(f"{label}: invalid {relation_label} claim type")
        _check_claim_status(label, relation_label, relation.get("claim_status"))
        _check_evidence_ids(
            label, relation_label, relation.get("evidence_ids"), evidence_ids
        )

    if "composition" in card:
        _validate_composition(label, card["composition"], evidence_ids)


def _validate_composition(
    label: str, composition: Any, evidence_ids: set[str | None]
) -> None:
    composition = _require_object(label, "composition", composition)
    inputs = composition.get("inputs")
    if not isinstance(inputs, list) or not inputs:
        raise CardValidationError(f"{label}: composition needs inputs")
    input_ids: set[str] = set()
    for index, item in enumerate(inputs):
        input_label = f"composition.inputs[{index}]"
        item = _require_object(label, input_label, item)
        system_id = item.get("system_id")
        if not isinstance(system_id, str) or not system_id:
            raise CardValidationError(f"{label}: {input_label} needs a system_id")
        if system_id in input_ids:
            raise CardValidationError(
                f"{label}: duplicate composition input: {system_id}"
            )
        input_ids.add(system_id)
        if not isinstance(item.get("role"), str) or not item["role"]:
            raise CardValidationError(f"{label}: {input_label} needs a role")
        _check_claim_status(label, input_label, item.get("claim_status"))
        _check_evidence_ids(label, input_label, item.get("evidence_ids"), evidence_ids)

    for field in ("constraints", "preserved_properties", "conflicts"):
        claims = composition.get(field)
        if not isinstance(claims, list):
            raise CardValidationError(f"{label}: composition.{field} must be a list")
        for index, claim in enumerate(claims):
            claim_label = f"composition.{field}[{index}]"
            claim = _require_object(label, claim_label, claim)
            if (
                not isinstance(claim.get("description"), str)
                or not claim["description"]
            ):
                raise CardValidationError(f"{label}: {claim_label} needs a description")
            if claim.get("claim_type") not in CLAIM_TYPES:
                raise CardValidationError(f"{label}: invalid {claim_label} claim type")
            _check_claim_status(label, claim_label, claim.get("claim_status"))
            _check_evidence_ids(
                label, claim_label, claim.get("evidence_ids"), evidence_ids
            )

    _check_claim_status(label, "composition", composition.get("claim_status"))
    _check_evidence_ids(
        label, "composition", composition.get("evidence_ids"), evidence_ids
    )


def _require_object(label: str, field: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CardValidationError(f"{label}: {field} must be an object")
    return value


def _check_claim_status(label: str, item_id: str, status: Any) -> None:
    if status not in CLAIM_STATUSES:
        raise CardValidationError(f"{label}: invalid {item_id} claim status")


def _check_optional_claim_status(label: str, item_id: str, status: Any) -> None:
    if status is not None:
        _check_claim_status(label, item_id, status)


def _check_evidence_ids(
    label: str, item_id: str, references: Any, evidence_ids: set[str | None]
) -> None:
    if not isinstance(references, list) or not references:
        raise CardValidationError(f"{label}: {item_id} needs evidence_ids")
    unknown = set(references) - evidence_ids
    if unknown:
        raise CardValidationError(f"{label}: unknown evidence ids: {sorted(unknown)}")


def discover_cards(root: Path) -> list[Path]:
    """Return cards in deterministic order."""

    return sorted(root.glob("*.json"))

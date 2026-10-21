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
        _check_evidence_ids(
            label, feature_id, feature.get("evidence_ids"), evidence_ids
        )

    for view in card["mathematical_views"]:
        if view.get("claim_type") not in CLAIM_TYPES:
            raise CardValidationError(f"{label}: invalid mathematical view claim type")
        _check_evidence_ids(
            label, view.get("model", "view"), view.get("evidence_ids"), evidence_ids
        )

    for trade_off in card["trade_offs"]:
        if trade_off.get("feature_id") not in feature_ids:
            raise CardValidationError(
                f"{label}: trade-off references unknown feature: "
                f"{trade_off.get('feature_id')}"
            )


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

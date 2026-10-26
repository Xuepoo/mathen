"""Loading and validating Architecture Cards."""

from __future__ import annotations

import json
import math
import re
from collections.abc import Iterable
from pathlib import Path
from typing import Any

from .mathviews import MathematicalViewValidationError, validate_math_view_contract
from .typed_composition import (
    TypedCompositionValidationError,
    validate_typed_composition,
)

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
FEATURE_RELATION_TYPES = {
    "implements",
    "refines",
    "requires",
    "supports",
    "conflicts-with",
    "composes",
    "resembles",
}
ID_PATTERN = re.compile(r"^[a-z0-9-]+$")
EXPERIMENT_REQUIRED_FIELDS = (
    "protocol",
    "system_commit",
    "environment",
    "command",
    "dataset",
    "repetitions",
    "metrics",
    "artifacts",
)


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
    for index, item in enumerate(evidence):
        _validate_evidence(label, index, item)
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
        if not isinstance(view, dict):
            raise CardValidationError(
                f"{label}: every mathematical view must be an object"
            )
        if view.get("claim_type") not in CLAIM_TYPES:
            raise CardValidationError(f"{label}: invalid mathematical view claim type")
        _check_optional_claim_status(
            label, view.get("model", "view"), view.get("claim_status")
        )
        _check_evidence_ids(
            label, view.get("model", "view"), view.get("evidence_ids"), evidence_ids
        )
        if "contract" in view:
            try:
                validate_math_view_contract(view["contract"], evidence_ids=evidence_ids)
            except MathematicalViewValidationError as error:
                raise CardValidationError(
                    f"{label}: mathematical view contract is invalid: {error}"
                ) from error

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

    if "feature_relations" in card:
        _validate_feature_relations(
            label, card["feature_relations"], feature_ids, evidence_ids
        )


def validate_card_collection(
    cards: Iterable[dict[str, Any]], require_feature_relation_targets: bool = True
) -> None:
    """Validate cross-card references after each card passes local validation."""

    cards = list(cards)
    card_by_id: dict[str, dict[str, Any]] = {}
    for card in cards:
        validate_card(card)
        card_id = card.get("id")
        if isinstance(card_id, str):
            if card_id in card_by_id:
                raise CardValidationError(f"duplicate card id: {card_id}")
            card_by_id[card_id] = card

    if not require_feature_relation_targets:
        return

    for card in cards:
        source_id = card.get("id", "card")
        for index, relation in enumerate(card.get("feature_relations", [])):
            target_system_id = relation["target_system_id"]
            target_card = card_by_id.get(target_system_id)
            if target_card is None:
                raise CardValidationError(
                    f"{source_id}: feature_relation[{index}] references unknown "
                    f"target system: {target_system_id}"
                )
            target_features = {
                feature.get("id")
                for feature in target_card.get("features", [])
                if isinstance(feature, dict)
            }
            if relation["target_feature_id"] not in target_features:
                raise CardValidationError(
                    f"{source_id}: feature_relation[{index}] references unknown "
                    "target feature: "
                    f"{target_system_id}:{relation['target_feature_id']}"
                )


def _validate_feature_relations(
    label: str,
    relations: Any,
    feature_ids: set[str],
    evidence_ids: set[str | None],
) -> None:
    if not isinstance(relations, list):
        raise CardValidationError(f"{label}: feature_relations must be a list")

    seen: set[tuple[str, str, str, str]] = set()
    required = {
        "source_feature_id",
        "target_system_id",
        "target_feature_id",
        "type",
        "claim_type",
        "claim_status",
        "evidence_ids",
    }
    allowed = required | {"notes"}
    for index, relation in enumerate(relations):
        relation_label = f"feature_relation[{index}]"
        relation = _require_object(label, relation_label, relation)
        missing = required - relation.keys()
        if missing:
            raise CardValidationError(
                f"{label}: {relation_label} missing fields: {sorted(missing)}"
            )
        unexpected = relation.keys() - allowed
        if unexpected:
            raise CardValidationError(
                f"{label}: {relation_label} has unexpected fields: {sorted(unexpected)}"
            )
        source_feature_id = relation["source_feature_id"]
        if not isinstance(source_feature_id, str) or not ID_PATTERN.fullmatch(
            source_feature_id
        ):
            raise CardValidationError(
                f"{label}: invalid {relation_label} source feature id"
            )
        if source_feature_id not in feature_ids:
            raise CardValidationError(
                f"{label}: {relation_label} references unknown source feature: "
                f"{source_feature_id}"
            )
        target_system_id = relation["target_system_id"]
        target_feature_id = relation["target_feature_id"]
        for field, value in (
            ("target system", target_system_id),
            ("target feature", target_feature_id),
        ):
            if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
                raise CardValidationError(
                    f"{label}: invalid {relation_label} {field} id"
                )
        if relation["type"] not in FEATURE_RELATION_TYPES:
            raise CardValidationError(f"{label}: invalid {relation_label} type")
        if relation["claim_type"] not in CLAIM_TYPES:
            raise CardValidationError(f"{label}: invalid {relation_label} claim type")
        _check_claim_status(label, relation_label, relation["claim_status"])
        if "notes" in relation and not isinstance(relation["notes"], str):
            raise CardValidationError(
                f"{label}: {relation_label} notes must be a string"
            )
        relation_evidence_ids = relation["evidence_ids"]
        if not isinstance(relation_evidence_ids, list) or not relation_evidence_ids:
            raise CardValidationError(f"{label}: {relation_label} needs evidence_ids")
        if not all(
            isinstance(evidence_id, str) for evidence_id in relation_evidence_ids
        ):
            raise CardValidationError(
                f"{label}: {relation_label} evidence_ids must contain strings"
            )
        _check_evidence_ids(label, relation_label, relation_evidence_ids, evidence_ids)
        identity = (
            source_feature_id,
            target_system_id,
            target_feature_id,
            relation["type"],
        )
        if identity in seen:
            raise CardValidationError(f"{label}: duplicate {relation_label} identity")
        seen.add(identity)


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

    for field in (
        "constraints",
        "preserved_properties",
        "conflicts",
        "validation_gaps",
    ):
        if field not in composition:
            continue
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
    if "typed_semantics" in composition:
        try:
            validate_typed_composition(
                composition["typed_semantics"], evidence_ids=evidence_ids
            )
        except TypedCompositionValidationError as error:
            raise CardValidationError(
                f"{label}: typed composition semantics are invalid: {error}"
            ) from error


def _require_object(label: str, field: str, value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise CardValidationError(f"{label}: {field} must be an object")
    return value


def _validate_evidence(label: str, index: int, evidence: Any) -> None:
    if not isinstance(evidence, dict):
        raise CardValidationError(f"{label}: evidence[{index}] must be an object")
    if evidence.get("kind") != "experiment":
        return

    evidence_label = f"evidence[{index}]"
    missing = [field for field in EXPERIMENT_REQUIRED_FIELDS if field not in evidence]
    if missing:
        raise CardValidationError(
            f"{label}: {evidence_label} missing experiment fields: {missing}"
        )
    for field in ("protocol", "system_commit", "command"):
        if not isinstance(evidence[field], str) or not evidence[field].strip():
            raise CardValidationError(
                f"{label}: {evidence_label}.{field} must be a non-empty string"
            )
    for field in ("environment", "dataset"):
        value = evidence[field]
        if not (isinstance(value, str) and value.strip() or isinstance(value, dict)):
            raise CardValidationError(
                f"{label}: {evidence_label}.{field} must be a string or object"
            )

    repetitions = evidence["repetitions"]
    if isinstance(repetitions, bool) or not isinstance(repetitions, int):
        raise CardValidationError(
            f"{label}: {evidence_label}.repetitions must be a positive integer"
        )
    if repetitions < 1:
        raise CardValidationError(
            f"{label}: {evidence_label}.repetitions must be a positive integer"
        )

    metrics = evidence["metrics"]
    if not isinstance(metrics, dict):
        raise CardValidationError(
            f"{label}: {evidence_label}.metrics must be an object"
        )
    for name, value in metrics.items():
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise CardValidationError(
                f"{label}: {evidence_label}.metrics.{name} must be a number"
            )
        if isinstance(value, float) and not math.isfinite(value):
            raise CardValidationError(
                f"{label}: {evidence_label}.metrics.{name} must be finite"
            )

    artifacts = evidence["artifacts"]
    if not isinstance(artifacts, list):
        raise CardValidationError(f"{label}: {evidence_label}.artifacts must be a list")
    for artifact in artifacts:
        if not (
            isinstance(artifact, dict) or isinstance(artifact, str) and artifact.strip()
        ):
            raise CardValidationError(
                f"{label}: {evidence_label}.artifacts entries must be strings "
                "or objects"
            )


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
    if len(references) != len(set(references)):
        raise CardValidationError(f"{label}: {item_id} has duplicate evidence ids")
    unknown = set(references) - evidence_ids
    if unknown:
        raise CardValidationError(f"{label}: unknown evidence ids: {sorted(unknown)}")


def discover_cards(root: Path) -> list[Path]:
    """Return Architecture Cards, excluding protocol audit sidecars."""

    return sorted(
        path for path in root.glob("*.json") if not path.name.endswith(".protocol.json")
    )

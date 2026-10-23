"""Generate deterministic, review-only relation candidates from Architecture Cards."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Iterable

from .cards import discover_cards, load_card

ANALYSIS_VERSION = "g6-relation-candidates-v1"
MENTION_SCORE = 70
RELATED_SYSTEM_SCORE = 30
RELATION_CUE = re.compile(
    r"\b(?:use(?:s|d|ing)?|depend(?:s|ed|ency)?|integrat(?:e|es|ed|ion)|"
    r"built|based|provided|powered|implemented|runs?)\b"
)


class RelationCandidateError(ValueError):
    """Raised when relation-candidate input cannot be processed."""


def generate_relation_candidate_report(
    cards: Iterable[dict[str, Any]],
) -> dict[str, Any]:
    """Build a stable report without changing any card.

    Candidates are keyed by the directed ``(source, target)`` pair.  A
    source-local target mention is considered only when the text belongs to a
    claim carrying evidence IDs that are present in that source card.  Legacy
    ``related_systems`` entries are retained as navigation signals, but they do
    not supply evidence IDs or a relation type.
    """

    ordered_cards = sorted(cards, key=lambda card: str(card.get("id", "")))
    by_id: dict[str, dict[str, Any]] = {}
    for card in ordered_cards:
        card_id = card.get("id")
        if not isinstance(card_id, str) or not card_id:
            raise RelationCandidateError("every card needs a non-empty string id")
        if card_id in by_id:
            raise RelationCandidateError(f"duplicate card id: {card_id}")
        by_id[card_id] = card

    existing_relations: list[dict[str, Any]] = []
    existing_pairs: set[tuple[str, str]] = set()
    for source_id in sorted(by_id):
        card = by_id[source_id]
        relations = card.get("relations", [])
        if not isinstance(relations, list):
            continue
        for relation in relations:
            if not isinstance(relation, dict):
                continue
            target = relation.get("target")
            relation_type = relation.get("type")
            if not isinstance(target, str) or not target:
                continue
            if not isinstance(relation_type, str) or not relation_type:
                continue
            existing_pairs.add((source_id, target))
            existing_relations.append(
                {
                    "source": source_id,
                    "target": target,
                    "type": relation_type,
                    "claim_status": relation.get("claim_status"),
                    "evidence_ids": _local_evidence_ids(card, relation),
                }
            )

    candidates: dict[tuple[str, str], dict[str, Any]] = {}
    target_ids = sorted(
        set(by_id)
        | {target for card in by_id.values() for target in _related_targets(card)}
        | {target for relation in existing_relations for target in [relation["target"]]}
    )

    for source_id in sorted(by_id):
        card = by_id[source_id]
        related_targets = _related_targets(card)
        mention_evidence = _source_local_target_mentions(card, by_id, target_ids)
        signal_targets = set(related_targets) | set(mention_evidence)
        for target in sorted(signal_targets):
            if target == source_id or (source_id, target) in existing_pairs:
                continue
            reasons: list[str] = []
            evidence_candidates: set[str] = set()
            if target in related_targets:
                reasons.append("related_systems")
            if target in mention_evidence:
                reasons.append("source_local_target_mention")
                evidence_candidates.update(mention_evidence[target])
            target_exists = target in by_id
            if not target_exists:
                reasons.append("missing_target")
            score = 0
            if target in mention_evidence:
                score += MENTION_SCORE
            if target in related_targets:
                score += RELATED_SYSTEM_SCORE
            candidates[(source_id, target)] = {
                "source": source_id,
                "target": target,
                "target_exists": target_exists,
                "status": "needs-review" if target_exists else "missing-target",
                "reasons": reasons,
                "score": score,
                "evidence_candidates": sorted(evidence_candidates),
            }

    return {
        "analysis_version": ANALYSIS_VERSION,
        "card_count": len(by_id),
        "card_ids": sorted(by_id),
        "existing_relations": sorted(
            existing_relations,
            key=lambda relation: (
                relation["source"],
                relation["target"],
                relation["type"],
            ),
        ),
        "candidates": [
            candidates[key]
            for key in sorted(candidates, key=lambda pair: (pair[0], pair[1]))
        ],
        "scoring": {
            "source_local_target_mention": MENTION_SCORE,
            "related_systems": RELATED_SYSTEM_SCORE,
            "maximum": MENTION_SCORE + RELATED_SYSTEM_SCORE,
        },
    }


def write_relation_candidate_report(cards_path: Path, output_path: Path) -> Path:
    """Load cards and write one deterministic JSON report."""

    card_paths = discover_cards(cards_path) if cards_path.is_dir() else [cards_path]
    if not card_paths:
        raise RelationCandidateError(f"no cards found in {cards_path}")
    report = generate_relation_candidate_report(
        load_card(card_path) for card_path in card_paths
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output_path


def _related_targets(card: dict[str, Any]) -> set[str]:
    related = card.get("related_systems", [])
    if not isinstance(related, list):
        return set()
    return {
        target
        for target in related
        if isinstance(target, str) and target and target != card.get("id")
    }


def _local_evidence_ids(card: dict[str, Any], claim: dict[str, Any]) -> list[str]:
    evidence = {
        item.get("id")
        for item in card.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    references = claim.get("evidence_ids", [])
    if not isinstance(references, list):
        return []
    return sorted(
        reference
        for reference in references
        if isinstance(reference, str) and reference in evidence
    )


def _source_local_target_mentions(
    card: dict[str, Any],
    cards_by_id: dict[str, dict[str, Any]],
    target_ids: Iterable[str],
) -> dict[str, set[str]]:
    evidence_ids = {
        item.get("id")
        for item in card.get("evidence", [])
        if isinstance(item, dict) and isinstance(item.get("id"), str)
    }
    aliases = {
        target: _aliases(target, cards_by_id.get(target))
        for target in target_ids
        if target != card.get("id")
    }
    mentions: dict[str, set[str]] = {}
    for text, claim_evidence in _evidence_bound_texts(card):
        local_evidence = claim_evidence & evidence_ids
        if not local_evidence:
            continue
        for target, target_aliases in aliases.items():
            if any(
                _contains_relation_bound_target(text, alias) for alias in target_aliases
            ):
                mentions.setdefault(target, set()).update(local_evidence)
    return mentions


def _aliases(target: str, target_card: dict[str, Any] | None) -> set[str]:
    """Return exact target labels; no token or shared-vocabulary inference."""

    aliases = {target, target.replace("-", " ")}
    if target_card and isinstance(target_card.get("name"), str):
        aliases.add(target_card["name"])
    return {alias.casefold().strip() for alias in aliases if alias.strip()}


def _contains_phrase(text: str, phrase: str) -> bool:
    escaped = re.escape(phrase)
    return re.search(rf"(?<![\w-]){escaped}(?![\w-])", text.casefold()) is not None


def _contains_relation_bound_target(text: str, target: str) -> bool:
    normalized = text.casefold()
    target_match = re.search(rf"(?<![\w-]){re.escape(target)}(?![\w-])", normalized)
    if target_match is None:
        return False
    start = max(0, target_match.start() - 80)
    end = min(len(normalized), target_match.end() + 80)
    return RELATION_CUE.search(normalized[start:end]) is not None


def _evidence_bound_texts(card: dict[str, Any]) -> Iterable[tuple[str, set[str]]]:
    """Yield claim text only from objects carrying source-local evidence IDs."""

    for feature in card.get("features", []):
        if isinstance(feature, dict):
            yield from _claim_texts(feature)
    for view in card.get("mathematical_views", []):
        if isinstance(view, dict):
            yield from _claim_texts(view)
    composition = card.get("composition")
    if isinstance(composition, dict):
        yield from _claim_texts(composition)
        for item in composition.get("inputs", []):
            if isinstance(item, dict):
                yield from _claim_texts(item)
        for field in (
            "constraints",
            "preserved_properties",
            "conflicts",
            "validation_gaps",
        ):
            for claim in composition.get(field, []):
                if isinstance(claim, dict):
                    yield from _claim_texts(claim)
    temporal = card.get("temporal_context")
    if isinstance(temporal, dict):
        yield from _claim_texts(temporal)


def _claim_texts(claim: dict[str, Any]) -> Iterable[tuple[str, set[str]]]:
    references = claim.get("evidence_ids")
    if not isinstance(references, list):
        return
    local_references = {
        reference for reference in references if isinstance(reference, str)
    }
    if not local_references:
        return
    text_values: list[str] = []
    for key, value in claim.items():
        if key not in {
            "description",
            "question",
            "assumptions",
            "notes",
            "role",
        }:
            continue
        if isinstance(value, str):
            text_values.append(value)
        elif isinstance(value, list):
            text_values.extend(item for item in value if isinstance(item, str))
    if text_values:
        yield " ".join(text_values), local_references

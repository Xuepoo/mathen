"""Build a read-only audit of typed system relations.

This module measures the reviewed catalogue as it is represented.  It does not
infer, accept, reject, or write relations.  In particular, degree and
component metrics describe catalogue connectivity and review coverage; they do
not measure ecosystem centrality, importance, influence, completeness, or
superiority.
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict, deque
from pathlib import Path
from typing import Any, Iterable

from .cards import (
    CLAIM_STATUSES,
    CLAIM_TYPES,
    RELATION_TYPES,
    discover_cards,
    load_card,
)

ANALYSIS_VERSION = "mth-0148-relation-audit-v1"
MAX_HIGH_DEGREE_ROWS = 20


class GraphAuditError(ValueError):
    """Raised when graph-audit input cannot be indexed safely."""


def generate_relation_audit_report(cards: Iterable[dict[str, Any]]) -> dict[str, Any]:
    """Return deterministic review-coverage and closure metrics for *cards*.

    Only explicit card ``relations`` are typed system edges.  Legacy
    ``related_systems`` values are reported separately and may be included in
    a clearly-labelled combined navigation graph, but never supply relation
    evidence or a relation type.
    """

    ordered_cards = sorted(cards, key=lambda card: str(card.get("id", "")))
    by_id: dict[str, dict[str, Any]] = {}
    for card in ordered_cards:
        card_id = card.get("id")
        if not isinstance(card_id, str) or not card_id:
            raise GraphAuditError("every card needs a non-empty string id")
        if card_id in by_id:
            raise GraphAuditError(f"duplicate card id: {card_id}")
        by_id[card_id] = card

    relation_rows: list[dict[str, Any]] = []
    closure_issues: list[dict[str, Any]] = []
    typed_edges: set[tuple[str, str]] = set()
    typed_by_pair: dict[tuple[str, str], set[str]] = defaultdict(set)
    status_counts: Counter[str] = Counter()
    type_counts: Counter[str] = Counter()
    claim_counts: Counter[str] = Counter()
    feature_relation_types: Counter[str] = Counter()
    relation_scope_context_count = 0

    for source_id in sorted(by_id):
        card = by_id[source_id]
        evidence_ids = {
            item.get("id")
            for item in card.get("evidence", [])
            if isinstance(item, dict) and isinstance(item.get("id"), str)
        }
        relations = card.get("relations", [])
        if not isinstance(relations, list):
            closure_issues.append(
                {"kind": "invalid-relations-container", "source": source_id}
            )
            continue
        for index, relation in enumerate(relations):
            location = f"{source_id}.relations[{index}]"
            if not isinstance(relation, dict):
                closure_issues.append(
                    {"kind": "invalid-relation", "location": location}
                )
                continue
            target = relation.get("target")
            relation_type = relation.get("type")
            claim_type = relation.get("claim_type")
            claim_status = relation.get("claim_status")
            evidence = relation.get("evidence_ids")
            if not isinstance(target, str) or not target:
                closure_issues.append({"kind": "missing-target", "location": location})
                continue
            evidence_list = evidence if isinstance(evidence, list) else []
            missing_evidence = sorted(
                value
                for value in evidence_list
                if isinstance(value, str) and value not in evidence_ids
            )
            if target not in by_id:
                closure_issues.append(
                    {
                        "kind": "missing-target-card",
                        "source": source_id,
                        "target": target,
                    }
                )
            if not evidence_list:
                closure_issues.append({"kind": "empty-evidence", "location": location})
            if missing_evidence:
                closure_issues.append(
                    {
                        "kind": "missing-source-evidence",
                        "location": location,
                        "evidence_ids": missing_evidence,
                    }
                )
            if (
                not isinstance(relation_type, str)
                or relation_type not in RELATION_TYPES
            ):
                closure_issues.append(
                    {
                        "kind": "unsupported-relation-type",
                        "location": location,
                        "type": relation_type,
                    }
                )
            if not isinstance(claim_type, str) or claim_type not in CLAIM_TYPES:
                closure_issues.append(
                    {
                        "kind": "invalid-claim-type",
                        "location": location,
                        "claim_type": claim_type,
                    }
                )
            if not isinstance(claim_status, str) or claim_status not in CLAIM_STATUSES:
                closure_issues.append(
                    {
                        "kind": "invalid-claim-status",
                        "location": location,
                        "claim_status": claim_status,
                    }
                )
            relation_rows.append(
                {
                    "source": source_id,
                    "target": target,
                    "type": relation_type,
                    "claim_type": claim_type,
                    "claim_status": claim_status,
                    "evidence_ids": sorted(
                        value for value in evidence_list if isinstance(value, str)
                    ),
                }
            )
            if "scope_context" in relation:
                relation_scope_context_count += 1
            if target in by_id and relation_type in RELATION_TYPES:
                typed_edges.add((source_id, target))
                typed_by_pair[(source_id, target)].add(relation_type)
            if isinstance(relation_type, str):
                type_counts[relation_type] += 1
            if isinstance(claim_type, str):
                claim_counts[claim_type] += 1
            if isinstance(claim_status, str):
                status_counts[claim_status] += 1

        feature_relations = card.get("feature_relations", [])
        if isinstance(feature_relations, list):
            for relation in feature_relations:
                if isinstance(relation, dict) and isinstance(relation.get("type"), str):
                    feature_relation_types[relation["type"]] += 1

    legacy_edges: list[tuple[str, str]] = []
    for source_id in sorted(by_id):
        related = by_id[source_id].get("related_systems", [])
        if not isinstance(related, list):
            continue
        for target in related:
            if isinstance(target, str) and target in by_id and target != source_id:
                legacy_edges.append((source_id, target))

    typed_degrees = _degrees(by_id, typed_edges)
    combined_edges = typed_edges | set(legacy_edges)
    combined_degrees = _degrees(by_id, combined_edges)
    typed_components = _components(sorted(by_id), typed_edges)
    combined_components = _components(sorted(by_id), combined_edges)
    pair_conflicts = [
        {
            "source": source,
            "target": target,
            "types": sorted(types),
        }
        for (source, target), types in sorted(typed_by_pair.items())
        if len(types) > 1
    ]

    systems_with_typed_edge = {node for edge in typed_edges for node in edge}
    typed_isolates = sorted(set(by_id) - systems_with_typed_edge)
    combined_isolates = sorted(
        set(by_id) - {node for edge in combined_edges for node in edge}
    )
    typed_coverage = {
        "reviewed_systems": len(by_id),
        "systems_with_typed_relation": len(systems_with_typed_edge),
        "system_review_coverage_ratio": _ratio(
            len(systems_with_typed_edge), len(by_id)
        ),
        "typed_relation_count": len(relation_rows),
        "valid_typed_edge_count": len(typed_edges),
        "isolated_systems_by_typed_edges": typed_isolates,
        "typed_undirected_component_count": len(typed_components),
        "typed_component_sizes": sorted(
            (len(item) for item in typed_components), reverse=True
        ),
    }
    legacy_metrics = {
        "valid_legacy_related_edges": len(legacy_edges),
        "unique_legacy_edge_count": len(set(legacy_edges)),
        "combined_unique_directed_edge_count": len(combined_edges),
        "isolated_systems_in_combined_navigation_graph": combined_isolates,
        "combined_undirected_component_count": len(combined_components),
        "combined_component_sizes": sorted(
            (len(item) for item in combined_components), reverse=True
        ),
    }

    return {
        "analysis_version": ANALYSIS_VERSION,
        "interpretation": {
            "typed_relations_are_review_coverage": True,
            "degree_is_catalogue_connectivity_not_ecosystem_centrality": True,
            "no_metric_measures_importance_influence_completeness_or_superiority": True,
            "legacy_related_systems_is_navigation_only": True,
        },
        "typed_coverage": typed_coverage,
        "legacy_and_combined_navigation": legacy_metrics,
        "relation_types": dict(sorted(type_counts.items())),
        "claim_types": dict(sorted(claim_counts.items())),
        "claim_statuses": dict(sorted(status_counts.items())),
        "feature_relation_types": dict(sorted(feature_relation_types.items())),
        "supported_system_relation_types": sorted(RELATION_TYPES),
        "unsupported_system_relation_types_requiring_schema_work": ["refines"],
        "evidence_closure": {
            "all_relation_evidence_ids_source_local": not any(
                issue["kind"] in {"missing-source-evidence", "empty-evidence"}
                for issue in closure_issues
            ),
            "all_relation_targets_reviewed": not any(
                issue["kind"] == "missing-target-card" for issue in closure_issues
            ),
            "issue_count": len(closure_issues),
            "issues": closure_issues,
        },
        "status_semantics": {
            "allowed_statuses": sorted(CLAIM_STATUSES),
            "proposed_is_not_accepted": True,
            "validator_checks_shape_and_locality_not_truth": True,
            "status_counts": dict(sorted(status_counts.items())),
        },
        "scope_context": {
            "typed_relations_with_scope_context": relation_scope_context_count,
            "relation_schema_supports_scope_context": False,
            "interpretation": (
                "MTH-0143 scope_context is additive metadata on supported card "
                "objects; it is not currently a relation field"
            ),
        },
        "typed_degree_patterns": {
            "definition": (
                "in_degree, out_degree, and total_degree over valid explicit "
                "typed system edges"
            ),
            "top_systems": _top_degree_rows(typed_degrees),
        },
        "combined_navigation_degree_patterns": {
            "definition": (
                "degree over explicit typed edges plus legacy related_systems "
                "navigation edges"
            ),
            "top_systems": _top_degree_rows(combined_degrees),
        },
        "proposal_conflicts": {
            "same_directed_pair_with_multiple_types": pair_conflicts,
            "policy": (
                "abstain until a reviewer chooses one supported type and resolves "
                "contradictory evidence"
            ),
        },
        "relations": sorted(
            relation_rows,
            key=lambda row: (row["source"], row["target"], str(row["type"])),
        ),
    }


def write_relation_audit_report(cards_path: Path, output_path: Path) -> Path:
    """Load reviewed cards and write a deterministic audit report."""

    card_paths = discover_cards(cards_path) if cards_path.is_dir() else [cards_path]
    if not card_paths:
        raise GraphAuditError(f"no cards found in {cards_path}")
    report = generate_relation_audit_report(load_card(path) for path in card_paths)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output_path


def _ratio(numerator: int, denominator: int) -> float:
    return round(numerator / denominator, 6) if denominator else 0.0


def _degrees(
    nodes: dict[str, dict[str, Any]], edges: Iterable[tuple[str, str]]
) -> dict[str, dict[str, int]]:
    result = {
        node: {"in_degree": 0, "out_degree": 0, "total_degree": 0} for node in nodes
    }
    for source, target in edges:
        result[source]["out_degree"] += 1
        result[target]["in_degree"] += 1
    for values in result.values():
        values["total_degree"] = values["in_degree"] + values["out_degree"]
    return result


def _top_degree_rows(degrees: dict[str, dict[str, int]]) -> list[dict[str, Any]]:
    rows = [
        {"system": node, **values}
        for node, values in degrees.items()
        if values["total_degree"] > 0
    ]
    rows.sort(key=lambda row: (-row["total_degree"], -row["out_degree"], row["system"]))
    return rows[:MAX_HIGH_DEGREE_ROWS]


def _components(nodes: list[str], edges: Iterable[tuple[str, str]]) -> list[list[str]]:
    adjacency: dict[str, set[str]] = {node: set() for node in nodes}
    for source, target in edges:
        adjacency[source].add(target)
        adjacency[target].add(source)
    remaining = set(nodes)
    components: list[list[str]] = []
    while remaining:
        start = min(remaining)
        remaining.remove(start)
        queue = deque([start])
        component = [start]
        while queue:
            current = queue.popleft()
            for neighbor in sorted(adjacency[current]):
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    component.append(neighbor)
                    queue.append(neighbor)
        components.append(sorted(component))
    return components

"""Audit explicit lifecycle and claim-type coverage without mutating cards."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from mathen.cards import CLAIM_TYPES, discover_cards, load_card

PILOT_CARD_IDS = (
    "airflow",
    "carryctx",
    "firecracker",
    "kafka",
    "kubernetes",
    "postgresql",
    "sqlite",
)


def audit(root: Path) -> dict[str, Any]:
    cards = [load_card(path) for path in discover_cards(root)]
    surfaces: dict[str, list[dict[str, Any]]] = {
        "cards": cards,
        "features": [
            feature
            for card in cards
            for feature in card["features"]
            if isinstance(feature, dict)
        ],
        "mathematical_views": [
            view
            for card in cards
            for view in card["mathematical_views"]
            if isinstance(view, dict)
        ],
    }
    result: dict[str, Any] = {
        "task": "MTH-0145",
        "schema_version": 1,
        "corpus": str(root / "*.json"),
        "reviewed_only": True,
        "mutation_performed": False,
        "counts": {name: len(items) for name, items in surfaces.items()},
        "surfaces": {},
        "interpretation": {
            "status_inferred_from_claim_type": False,
            "status_inferred_from_source_kind": False,
            "status_inferred_from_popularity_or_graph": False,
            "status_inferred_from_similarity": False,
            "canonical_cards_backfilled": False,
        },
    }
    for name, records in surfaces.items():
        claim_types = Counter(
            record.get("claim_type", "<missing>") for record in records
        )
        claim_statuses = Counter(
            record.get("claim_status", "<missing>") for record in records
        )
        lifecycle_statuses = Counter(
            (record.get("lifecycle") or {}).get("status", "<missing>")
            for record in records
        )
        result["surfaces"][name] = {
            "total": len(records),
            "claim_type": dict(sorted(claim_types.items())),
            "claim_status": dict(sorted(claim_statuses.items())),
            "lifecycle_status": dict(sorted(lifecycle_statuses.items())),
            "records_with_lifecycle": sum("lifecycle" in record for record in records),
            "records_with_evidence_ids": sum(
                isinstance(record.get("evidence_ids"), list)
                and bool(record["evidence_ids"])
                for record in records
            ),
            "claim_types_missing_from_surface": sorted(
                CLAIM_TYPES - {record.get("claim_type") for record in records}
            ),
        }
    return result


def pilot_audit(root: Path) -> dict[str, Any]:
    """Report the bounded MTH-0153 lifecycle pilot without mutating cards."""

    cards = {
        card["id"]: card for card in (load_card(path) for path in discover_cards(root))
    }
    selected_cards = [cards[card_id] for card_id in PILOT_CARD_IDS]
    records: list[dict[str, Any]] = []
    surface_counts: dict[str, Counter[str]] = {
        "features": Counter(),
        "mathematical_views": Counter(),
    }
    for card in selected_cards:
        for surface in ("features", "mathematical_views"):
            for record in card[surface]:
                lifecycle = record.get("lifecycle")
                status = (lifecycle or {}).get("status", "unknown/not-recorded")
                surface_counts[surface][status] += 1
                if lifecycle is not None:
                    records.append(
                        {
                            "card_id": card["id"],
                            "surface": surface,
                            "record_id": record.get("id", record.get("model")),
                            "status": status,
                            "evidence_ids": lifecycle["evidence_ids"],
                            "claim_type": lifecycle["claim_type"],
                            "claim_status": lifecycle["claim_status"],
                        }
                    )
    records.sort(key=lambda item: (item["card_id"], item["surface"], item["record_id"]))
    return {
        "task": "MTH-0153",
        "schema_version": 1,
        "corpus": str(root / "*.json"),
        "selected_cards": list(PILOT_CARD_IDS),
        "mutation_performed": False,
        "counts": {
            "cards_selected": len(selected_cards),
            "features_selected": sum(len(card["features"]) for card in selected_cards),
            "mathematical_views_selected": sum(
                len(card["mathematical_views"]) for card in selected_cards
            ),
            "lifecycle_records": len(records),
            "lifecycle_records_by_surface": {
                surface: sum(1 for record in records if record["surface"] == surface)
                for surface in ("features", "mathematical_views")
            },
        },
        "statuses_by_surface": {
            surface: dict(sorted(counts.items()))
            for surface, counts in surface_counts.items()
        },
        "lifecycle_records": records,
        "absence_of_evidence_boundaries": {
            "unsupported_selected_records_remain_unknown": True,
            "features_without_lifecycle": sum(
                1
                for card in selected_cards
                for feature in card["features"]
                if "lifecycle" not in feature
            ),
            "mathematical_views_without_lifecycle": sum(
                1
                for card in selected_cards
                for view in card["mathematical_views"]
                if "lifecycle" not in view
            ),
            "cards_outside_pilot_included": False,
            "status_not_inferred_from_claim_type": True,
            "status_not_inferred_from_claim_status": True,
            "status_not_inferred_from_source_kind": True,
            "status_not_inferred_from_popularity_graph_version_name_or_similarity": (
                True
            ),
            "missing_lifecycle_is_unknown_not_recorded": True,
            "no_deprecated_or_superseded_status_asserted": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="?", default=Path("data/systems"))
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--pilot",
        action="store_true",
        help="report the fixed seven-card MTH-0153 lifecycle pilot",
    )
    args = parser.parse_args()
    report = pilot_audit(args.path) if args.pilot else audit(args.path)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Audit explicit lifecycle and claim-type coverage without mutating cards."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path
from typing import Any

from mathen.cards import CLAIM_TYPES, discover_cards, load_card


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path", type=Path, nargs="?", default=Path("data/systems"))
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit(args.path)
    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

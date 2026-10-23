import json
import tempfile
import unittest
from pathlib import Path

from mathen.relation_candidates import (
    ANALYSIS_VERSION,
    generate_relation_candidate_report,
    write_relation_candidate_report,
)


def card(
    card_id: str,
    *,
    name: str | None = None,
    related_systems: list[str] | None = None,
    feature_description: str = "A local architectural fact.",
    feature_evidence_ids: list[str] | None = None,
) -> dict:
    evidence_ids = feature_evidence_ids or [f"{card_id}-evidence"]
    return {
        "id": card_id,
        "name": name or card_id.title(),
        "summary": "A card fixture.",
        "scope": ["architecture"],
        "features": [
            {
                "id": "feature",
                "name": "Feature",
                "category": "architecture",
                "claim_type": "fact",
                "description": feature_description,
                "evidence_ids": evidence_ids,
            }
        ],
        "mathematical_views": [],
        "trade_offs": [],
        "evidence": [{"id": evidence_id} for evidence_id in evidence_ids],
        "related_systems": related_systems or [],
    }


class RelationCandidateTests(unittest.TestCase):
    def test_output_is_deterministic_for_card_order(self) -> None:
        source = card(
            "source",
            related_systems=["target"],
            feature_description="The source integrates with Target.",
        )
        target = card("target", name="Target")

        first = generate_relation_candidate_report([source, target])
        second = generate_relation_candidate_report([target, source])

        self.assertEqual(first, second)
        self.assertEqual(first["analysis_version"], ANALYSIS_VERSION)
        self.assertEqual(len(first["candidates"]), 1)

    def test_missing_related_target_is_reported_without_inventing_edge(self) -> None:
        report = generate_relation_candidate_report(
            [card("source", related_systems=["unreviewed"])]
        )

        self.assertEqual(
            report["candidates"],
            [
                {
                    "source": "source",
                    "target": "unreviewed",
                    "target_exists": False,
                    "status": "missing-target",
                    "reasons": ["related_systems", "missing_target"],
                    "score": 30,
                    "evidence_candidates": [],
                }
            ],
        )
        self.assertNotIn("relations", report)

    def test_duplicate_signals_merge_into_one_candidate(self) -> None:
        report = generate_relation_candidate_report(
            [
                card(
                    "source",
                    related_systems=["target", "target"],
                    feature_description="The source integrates with Target.",
                ),
                card("target", name="Target"),
            ]
        )

        self.assertEqual(len(report["candidates"]), 1)
        self.assertEqual(
            report["candidates"][0]["reasons"],
            ["related_systems", "source_local_target_mention"],
        )
        self.assertEqual(report["candidates"][0]["score"], 100)
        self.assertEqual(
            report["candidates"][0]["evidence_candidates"], ["source-evidence"]
        )

    def test_target_mention_needs_source_local_evidence_boundary(self) -> None:
        source = card(
            "source",
            feature_description="The source integrates with Target.",
            feature_evidence_ids=["foreign-evidence"],
        )
        source["evidence"] = [{"id": "source-evidence"}]

        report = generate_relation_candidate_report([source, card("target")])

        self.assertEqual(report["candidates"], [])

    def test_existing_relation_is_not_regenerated(self) -> None:
        source = card(
            "source",
            related_systems=["target"],
            feature_description="The source integrates with Target.",
        )
        source["relations"] = [
            {
                "type": "uses",
                "target": "target",
                "claim_status": "proposed",
                "evidence_ids": ["source-evidence"],
            }
        ]

        report = generate_relation_candidate_report([source, card("target")])

        self.assertEqual(report["candidates"], [])
        self.assertEqual(
            report["existing_relations"][0]["evidence_ids"], ["source-evidence"]
        )

    def test_writer_uses_stable_ignored_report_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cards_dir = root / "cards"
            cards_dir.mkdir()
            (cards_dir / "source.json").write_text(
                json.dumps(card("source", related_systems=["missing"])),
                encoding="utf-8",
            )
            output = root / "data" / "analyses" / "g6.json"

            written = write_relation_candidate_report(cards_dir, output)

            self.assertEqual(written, output)
            self.assertEqual(
                json.loads(output.read_text()),
                generate_relation_candidate_report(
                    [card("source", related_systems=["missing"])]
                ),
            )


if __name__ == "__main__":
    unittest.main()

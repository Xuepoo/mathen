import json
import tempfile
import unittest
from pathlib import Path

from mathen.graph_audit import (
    ANALYSIS_VERSION,
    generate_relation_audit_report,
    write_relation_audit_report,
)


def card(card_id: str, *, related_systems: list[str] | None = None) -> dict:
    evidence_id = f"{card_id}-evidence"
    return {
        "id": card_id,
        "name": card_id.title(),
        "summary": "A graph audit fixture.",
        "scope": ["architecture"],
        "features": [],
        "mathematical_views": [],
        "trade_offs": [],
        "evidence": [{"id": evidence_id}],
        "related_systems": related_systems or [],
    }


def relation(
    target: str,
    relation_type: str = "uses",
    *,
    claim_type: str = "fact",
    claim_status: str = "proposed",
    evidence_ids: list[str] | None = None,
) -> dict:
    return {
        "type": relation_type,
        "target": target,
        "claim_type": claim_type,
        "claim_status": claim_status,
        "evidence_ids": evidence_ids or ["source-evidence"],
    }


class GraphAuditTests(unittest.TestCase):
    def test_metrics_are_deterministic_and_keep_navigation_separate(self) -> None:
        source = card("source", related_systems=["target"])
        source["relations"] = [relation("target")]
        target = card("target")

        first = generate_relation_audit_report([target, source])
        second = generate_relation_audit_report([source, target])

        self.assertEqual(first, second)
        self.assertEqual(first["analysis_version"], ANALYSIS_VERSION)
        self.assertEqual(first["typed_coverage"]["typed_relation_count"], 1)
        self.assertEqual(
            first["legacy_and_combined_navigation"]["valid_legacy_related_edges"], 1
        )
        self.assertEqual(first["evidence_closure"]["issue_count"], 0)
        self.assertEqual(
            first["scope_context"]["typed_relations_with_scope_context"], 0
        )
        self.assertTrue(
            first["interpretation"][
                "degree_is_catalogue_connectivity_not_ecosystem_centrality"
            ]
        )

    def test_closure_reports_missing_target_and_source_evidence_without_repair(
        self,
    ) -> None:
        source = card("source")
        source["relations"] = [relation("unreviewed", evidence_ids=["not-local"])]

        report = generate_relation_audit_report([source])

        issues = report["evidence_closure"]["issues"]
        self.assertEqual(
            {issue["kind"] for issue in issues},
            {"missing-target-card", "missing-source-evidence"},
        )
        self.assertEqual(report["relations"][0]["target"], "unreviewed")
        self.assertEqual(report["typed_coverage"]["valid_typed_edge_count"], 0)

    def test_conflicting_types_are_reported_and_not_resolved(self) -> None:
        source = card("source")
        source["relations"] = [
            relation("target", "uses"),
            relation("target", "resembles", claim_type="analogy"),
        ]

        report = generate_relation_audit_report([source, card("target")])

        self.assertEqual(
            report["proposal_conflicts"]["same_directed_pair_with_multiple_types"],
            [{"source": "source", "target": "target", "types": ["resembles", "uses"]}],
        )
        self.assertEqual(report["typed_coverage"]["typed_relation_count"], 2)

    def test_writer_does_not_add_relations_to_cards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cards_dir = root / "cards"
            cards_dir.mkdir()
            source = card("source")
            (cards_dir / "source.json").write_text(json.dumps(source), encoding="utf-8")
            output = root / "audit.json"

            write_relation_audit_report(cards_dir, output)

            self.assertNotIn(
                "relations", json.loads((cards_dir / "source.json").read_text())
            )
            self.assertEqual(
                json.loads(output.read_text())["typed_coverage"][
                    "typed_relation_count"
                ],
                0,
            )


if __name__ == "__main__":
    unittest.main()

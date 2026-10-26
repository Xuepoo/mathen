import importlib.util
import json
import sys
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "scripts" / "audit_research_review_queue.py"
SPEC = importlib.util.spec_from_file_location("audit_research_review_queue", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


def card(card_id: str) -> dict:
    evidence_id = f"{card_id}-evidence"
    return {
        "id": card_id,
        "name": card_id.title(),
        "features": [
            {
                "id": f"{card_id}-feature",
                "name": "Feature",
                "claim_type": "fact",
                "evidence_ids": [evidence_id],
            }
        ],
        "mathematical_views": [
            {
                "name": "A view",
                "claim_type": "inference",
                "evidence_ids": [evidence_id],
            }
        ],
        "evidence": [{"id": evidence_id}],
        "related_systems": [],
    }


def observation() -> dict:
    return {
        "id": "observation-1",
        "kind": "benchmark",
        "observation_version": "1",
        "review": {"status": "unreviewed", "card_claim_refs": []},
        "result_boundary": {
            "promotion_requires_human_review": True,
            "storage_scope": "research",
        },
        "result": {"status": "observed"},
    }


class ResearchReviewQueueTests(unittest.TestCase):
    def test_missing_scope_and_lifecycle_are_not_inferred(self) -> None:
        report = AUDIT.audit_documents([card("source")], [], [])

        self.assertEqual(
            report["scope_context"]["surfaces"]["features"]["dimensions"]["workload"],
            {"not-recorded": 1},
        )
        self.assertEqual(
            report["lifecycle"]["surfaces"]["features"]["status_counts"],
            {"not-recorded": 1},
        )
        self.assertTrue(report["review_boundary"]["scope_status_inferred"] is False)
        self.assertTrue(report["review_boundary"]["lifecycle_status_inferred"] is False)

    def test_explicit_unknown_is_distinct_from_missing_scope(self) -> None:
        value = card("source")
        value["scope_context"] = {
            dimension: {"status": "unknown" if dimension == "scale" else "unspecified"}
            for dimension in AUDIT.SCOPE_DIMENSIONS
        }

        report = AUDIT.audit_documents([value], [], [])
        dimensions = report["scope_context"]["surfaces"]["cards"]["dimensions"]
        self.assertEqual(dimensions["scale"], {"unknown": 1})
        self.assertEqual(dimensions["workload"], {"unspecified": 1})
        self.assertEqual(
            next(
                item
                for item in report["scope_context"]["candidates"]
                if item["location"] == "card:source" and item["dimension"] == "scale"
            )["status"],
            "unknown",
        )

    def test_observation_references_do_not_infer_promotion(self) -> None:
        report = AUDIT.audit_documents(
            [], [("data/experiments/observation.json", observation())], []
        )

        record = report["detached_observation_evidence"]["records"][0]
        self.assertTrue(record["detached"])
        self.assertTrue(record["artifact_detached"])
        self.assertFalse(record["canonical_evidence_linked"])
        self.assertEqual(record["review_status"], "unreviewed")
        self.assertEqual(record["promotion_decision"], "not-determined")
        self.assertEqual(
            len(report["detached_observation_evidence"]["review_candidates"]), 1
        )

    def test_reviewed_observation_reference_still_does_not_infer_promotion(
        self,
    ) -> None:
        value = observation()
        value["review"] = {
            "status": "reviewed",
            "reviewer": "reviewer",
            "reviewed_at": "2026-10-27T00:00:00Z",
            "card_claim_refs": ["feature:source-feature"],
        }

        report = AUDIT.audit_documents(
            [], [("data/experiments/observation.json", value)], []
        )

        record = report["detached_observation_evidence"]["records"][0]
        self.assertEqual(record["card_claim_refs"], ["feature:source-feature"])
        self.assertEqual(record["promotion_decision"], "not-determined")

    def test_standalone_validation_record_is_not_promoted_by_valid_classification(
        self,
    ) -> None:
        contract = json.loads(
            (Path(__file__).parent / "fixtures" / "math-view-valid.json").read_text()
        )
        contract["validation_records"] = [
            {
                "id": "record-1",
                "view_id": contract["id"],
                "kind": "observed-result",
                "basis": "deterministic-check",
                "claim_type": "inference",
                "claim_status": "under-review",
                "system": "SQLite",
                "version": "fixture",
                "scope": {
                    "systems": ["SQLite"],
                    "versions": ["fixture"],
                    "deployment_origins": ["fixture-origin"],
                    "conditions": ["fixture condition"],
                    "exclusions": ["fixture limitation"],
                },
                "evidence_ids": ["design-doc"],
                "provenance": {
                    "run_id": "run-1",
                    "source_revision": "fixture",
                    "protocol_digest": "sha256:fixture",
                    "recorded_at": "2026-10-27T00:00:00Z",
                    "runner": "fixture-runner",
                    "toolchain": "fixture",
                },
                "result": {"status": "observed", "summary": "bounded"},
                "limitations": ["fixture only"],
            }
        ]

        report = AUDIT.audit_documents([], [], [("data/mathviews/view.json", contract)])

        self.assertEqual(
            report["standalone_mathviews"]["contracts"][0]["deterministic_validation"],
            "valid",
        )
        self.assertTrue(
            report["standalone_mathviews"]["classification_is_not_promotion"]
        )
        self.assertEqual(
            report["standalone_mathviews"]["review_candidates"][0]["reasons"],
            ["validation-record-not-accepted"],
        )

    def test_relation_candidates_are_separate_and_deterministic(self) -> None:
        source = card("source")
        source["related_systems"] = ["target"]
        target = card("target")
        first = AUDIT.audit_documents([source, target], [], [])
        second = AUDIT.audit_documents([target, source], [], [])

        self.assertEqual(first, second)
        self.assertEqual(first["relation_candidates"]["candidate_count"], 1)
        self.assertFalse(first["review_boundary"]["relation_written"])


if __name__ == "__main__":
    unittest.main()

import json
import unittest
from pathlib import Path

from scripts.agent_review_scoring import (
    DIMENSION_CATEGORIES,
    ScoringError,
    _copy_observation,
    build_artifact,
    file_digest,
)

ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "data/research-review/scoring/mth-0188-agent-review-scoring.json"
SCHEMA = ROOT / "schemas/agent-review-scoring.schema.json"


class AgentReviewScoringTests(unittest.TestCase):
    def test_checked_in_artifact_matches_builder_byte_for_byte(self) -> None:
        expected = json.dumps(build_artifact(), indent=2, sort_keys=True) + "\n"
        self.assertEqual(ARTIFACT.read_bytes(), expected.encode("utf-8"))

    def test_observations_retain_boundary_digests_scope_locality_and_timing(
        self,
    ) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(artifact["evaluation_boundary"]["observed_row_count"], 16)
        self.assertFalse(artifact["evaluation_boundary"]["holdout_included"])
        self.assertEqual(
            {row["packet_label"] for row in artifact["observations"]}, {"A", "B"}
        )
        for row in artifact["observations"]:
            self.assertTrue(row["pilot_digest"].startswith("sha256:"))
            self.assertTrue(row["study_packet_digest"].startswith("sha256:"))
            self.assertTrue(row["candidate_digest"].startswith("sha256:"))
            self.assertTrue(row["evidence_excerpt_digests"])
            self.assertTrue(row["negative_knowledge_digests"])
            self.assertTrue(row["source_ids"])
            self.assertTrue(row["scope_context"])
            self.assertTrue(row["locality"])
            self.assertEqual(row["timing"]["measurement_status"], "observed")
            self.assertGreaterEqual(row["timing"]["elapsed_seconds"], 0)

    def test_all_dimensions_and_slices_are_separate_exact_observations(self) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            set(artifact["scores"]["overall"]["dimensions"]),
            set(DIMENSION_CATEGORIES),
        )
        self.assertEqual(
            [item["slice"] for item in artifact["scores"]["by_pilot"]],
            ["mth-0186", "mth-0187"],
        )
        self.assertEqual(len(artifact["scores"]["by_task"]), 8)
        self.assertEqual(len(artifact["scores"]["by_domain"]), 4)
        metric = artifact["scores"]["overall"]["dimensions"]["usefulness"][
            "categories"
        ]["useful"]
        self.assertEqual(metric["denominator"], 16)
        self.assertEqual(metric["interval"]["method"], "clopper-pearson-exact")
        self.assertEqual(metric["warnings"], [])

    def test_small_sample_warnings_are_present_for_task_and_agreement_slices(
        self,
    ) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        for item in artifact["scores"]["by_task"]:
            self.assertTrue(item["dimensions"]["claim_type"]["warnings"])
        for item in artifact["agreement"]["by_task"]:
            self.assertTrue(item["warnings"])

    def test_agreement_is_explicitly_agent_pilot_only(self) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        agreement = artifact["agreement"]
        self.assertEqual(artifact["provenance"]["execution_actor"], "llm-based-agent")
        self.assertEqual(artifact["provenance"]["provider"], "not-recorded")
        self.assertEqual(artifact["provenance"]["model"], "not-recorded")
        self.assertEqual(agreement["observation_kind"], "agent-pilot-agreement")
        self.assertEqual(agreement["reviewer_kind"], "agent")
        self.assertFalse(agreement["human_review"])
        self.assertEqual(agreement["overall"]["paired_count"], 8)
        self.assertTrue(
            all(
                pair["dimensions"]["claim_type"]["agent_pilot_only"]
                for pair in agreement["paired_rows"]
            )
        )
        self.assertIn(
            "It is not human reviewer agreement and does not estimate human "
            "reliability.",
            agreement["non_claims"],
        )

    def test_no_aggregate_quality_score_or_promotion_claim(self) -> None:
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertNotIn("aggregate_quality_score", artifact)
        self.assertEqual(
            artifact["promotion_boundary"]["promotion_decision"], "not-determined"
        )
        self.assertFalse(artifact["promotion_boundary"]["review_implies_promotion"])
        self.assertFalse(artifact["promotion_boundary"]["canonical_cards_written"])

    def test_holdout_rows_are_rejected(self) -> None:
        with self.assertRaises(ScoringError):
            _copy_observation(
                "mth-0186",
                "A",
                "sha256:" + "0" * 64,
                "sha256:" + "1" * 64,
                {"task_id": "task-01"},
                {
                    "task_id": "task-01",
                    "assignment_id": "assignment-01",
                    "domain_id": "storage",
                    "partition": "holdout",
                },
            )

    def test_schema_is_closed_and_artifact_sources_are_digest_bound(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("aggregate_quality_score", schema["properties"])
        for source in artifact["sources"]:
            self.assertEqual(source["digest"], file_digest(ROOT / source["artifact"]))


if __name__ == "__main__":
    unittest.main()

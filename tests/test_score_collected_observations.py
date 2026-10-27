import json
import unittest
from pathlib import Path

from scripts.score_collected_observations import build_artifact
from scripts.statistical_error_analysis import ERROR_TAXONOMY

ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "data/benchmark/mth-0183-collected-observations.json"
SCHEMA = ROOT / "schemas/collected-observations.schema.json"


class CollectedObservationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))

    def test_checked_in_artifact_matches_builder(self) -> None:
        self.assertEqual(self.artifact, build_artifact())

    def test_agent_rows_preserve_provenance_and_unknown_abstentions(self) -> None:
        rows = self.artifact["observations"]["agent-review"]
        self.assertEqual(len(rows), 8)
        self.assertEqual({row["reviewer_kind"] for row in rows}, {"agent"})
        self.assertEqual({row["human_review"] for row in rows}, {False})
        self.assertEqual({row["evaluation_status"] for row in rows}, {"abstained"})
        self.assertTrue(all(not row["evidence_payload_available"] for row in rows))
        self.assertTrue(all(row["unknown_labels"] for row in rows))
        self.assertEqual({row["timing"]["timing_scope"] for row in rows}, {"agent-run"})

    def test_agent_aggregation_uses_mth_0177_and_keeps_dimensions_separate(
        self,
    ) -> None:
        overall = self.artifact["aggregation"]["agent-review"]["overall"]
        self.assertEqual(overall["observed_count"], 8)
        abstention = overall["metrics"]["abstention"]
        self.assertEqual(abstention["numerator"], 8)
        self.assertEqual(abstention["denominator"], 8)
        self.assertEqual(abstention["interval"]["method"], "clopper-pearson-exact")
        self.assertIsNone(overall["metrics"]["false-link"]["value"])
        self.assertEqual(
            len(self.artifact["aggregation"]["agent-review"]["by_pilot"]), 2
        )
        self.assertEqual(
            len(self.artifact["aggregation"]["agent-review"]["by_task"]), 4
        )

    def test_strata_and_direct_llm_not_evaluated(self) -> None:
        self.assertEqual(self.artifact["observations"]["human-review"], [])
        model = self.artifact["observations"]["model-run"][0]
        self.assertEqual(model["status"], "not-evaluated")
        self.assertTrue(
            all(value is None for value in model["output_metrics"].values())
        )
        model_aggregation = self.artifact["aggregation"]["model-run"]
        self.assertEqual(model_aggregation["overall"]["observed_count"], 0)
        self.assertIsNone(
            model_aggregation["overall"]["metrics"]["abstention"]["value"]
        )

    def test_schema_and_no_quality_score(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertNotIn("aggregate_quality_score", self.artifact)
        self.assertNotIn("aggregate_quality_score", self.artifact["aggregation"])
        self.assertEqual(
            {entry["id"] for entry in self.artifact["error_taxonomy"]},
            set(ERROR_TAXONOMY),
        )


if __name__ == "__main__":
    unittest.main()

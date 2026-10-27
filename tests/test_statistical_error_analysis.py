import json
import unittest
from pathlib import Path

from scripts.statistical_error_analysis import (
    ERROR_TAXONOMY,
    aggregate_rate,
    bootstrap_interval,
    build_artifact,
    error_analysis,
    exact_binomial_interval,
    repeated_run_aggregation,
)

ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "data/benchmark/mth-0177-statistical-analysis.json"
SCHEMA = ROOT / "schemas/statistical-analysis.schema.json"


class StatisticalErrorAnalysisTests(unittest.TestCase):
    def test_empty_observations_are_null_and_have_no_interval(self) -> None:
        result = error_analysis([])
        self.assertEqual(result["observed_count"], 0)
        self.assertEqual(set(result["metrics"]), set(ERROR_TAXONOMY))
        for metric in result["metrics"].values():
            self.assertIsNone(metric["value"])
            self.assertIsNone(metric["interval"])
            self.assertEqual(metric["denominator"], 0)
            self.assertEqual(metric["status"], "not-evaluated")

    def test_taxonomy_is_separate_and_sliced_by_domain_and_task(self) -> None:
        rows = [
            {
                "domain": "storage",
                "task_id": "task-01",
                "errors": ["false-link"],
            },
            {
                "domain": "storage",
                "task_id": "task-02",
                "errors": ["scope-loss", "claim-discipline"],
            },
            {
                "domain": "streaming",
                "task_id": "task-03",
                "errors": ["abstention", "counterexample-miss"],
            },
        ]
        result = error_analysis(rows)
        self.assertEqual(result["metrics"]["false-link"]["numerator"], 1)
        self.assertEqual(result["metrics"]["scope-loss"]["numerator"], 1)
        self.assertEqual(result["metrics"]["claim-discipline"]["numerator"], 1)
        self.assertEqual(result["metrics"]["reviewer-disagreement"]["value"], 0.0)
        self.assertEqual(
            [item["slice"] for item in result["by_domain"]], ["storage", "streaming"]
        )
        self.assertEqual(len(result["by_task"]), 3)

    def test_exact_interval_and_small_sample_warning_require_observations(self) -> None:
        interval = exact_binomial_interval(1, 3)
        self.assertIsNotNone(interval)
        self.assertLessEqual(interval["lower"], 1 / 3)
        self.assertGreaterEqual(interval["upper"], 1 / 3)
        metric = aggregate_rate(
            [{"correct": True}, {"correct": False}, {"correct": True}],
            metric="correct",
        )
        self.assertEqual(metric["value"], 2 / 3)
        self.assertEqual(len(metric["warnings"]), 1)
        self.assertEqual(metric["interval"]["method"], "clopper-pearson-exact")

    def test_bootstrap_is_deterministic_and_empty_is_null(self) -> None:
        self.assertIsNone(bootstrap_interval([]))
        first = bootstrap_interval([0.0, 0.5, 1.0], resamples=100, seed=17)
        second = bootstrap_interval([0.0, 0.5, 1.0], resamples=100, seed=17)
        self.assertEqual(first, second)
        self.assertEqual(first["method"], "percentile-bootstrap")

    def test_repeated_run_hook_does_not_invent_missing_runs(self) -> None:
        result = repeated_run_aggregation([])
        self.assertEqual(result["run_count"], 0)
        for metric in result["metrics"].values():
            self.assertIsNone(metric["mean"])
            self.assertIsNone(metric["interval"])
            self.assertEqual(metric["status"], "not-evaluated")

    def test_checked_in_artifact_matches_deterministic_builder(self) -> None:
        actual = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(actual, build_artifact())
        self.assertEqual(actual["protocol_capacity"]["task_count"], 12)
        self.assertEqual(len(actual["protocol_capacity"]["domain_slices"]), 4)
        self.assertEqual(actual["outcome"]["status"], "not-evaluated")

    def test_schema_closes_contract_and_preserves_no_aggregate_score(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("by_domain", schema["$defs"]["errorAnalysis"]["properties"])
        self.assertIn("by_task", schema["$defs"]["errorAnalysis"]["properties"])
        self.assertNotIn("aggregate_quality_score", schema["properties"])


if __name__ == "__main__":
    unittest.main()

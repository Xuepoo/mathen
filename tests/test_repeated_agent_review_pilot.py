import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/repeated_agent_review_pilot.py"
SPEC = importlib.util.spec_from_file_location("repeated_agent_review_pilot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class RepeatedAgentReviewPilotTests(unittest.TestCase):
    def load_artifact(self) -> dict:
        return json.loads(
            (ROOT / "data/research-review/pilots/mth-0193.json").read_text()
        )

    def test_checked_in_artifact_closes_two_independent_runs(self) -> None:
        artifact = self.load_artifact()
        MODULE.validate_artifact(artifact)
        self.assertEqual(artifact["pilot_id"], "mth-0193")
        self.assertEqual(artifact["run_count"], 2)
        self.assertEqual(
            [run["run_id"] for run in artifact["runs"]],
            ["mth-0193-run-alpha", "mth-0193-run-beta"],
        )
        self.assertNotEqual(
            artifact["runs"][0]["run_seed"], artifact["runs"][1]["run_seed"]
        )
        self.assertEqual(sum(len(run["observations"]) for run in artifact["runs"]), 32)

    def test_packet_and_order_variations_are_independent(self) -> None:
        artifact = self.load_artifact()
        first, second = artifact["runs"]
        self.assertNotEqual(first["packet_labels"], second["packet_labels"])
        first_orders = {
            item["packet_label"]: item["assignment_order"] for item in first["packets"]
        }
        second_orders = {
            item["packet_label"]: item["assignment_order"] for item in second["packets"]
        }
        self.assertNotEqual(first_orders["A"], second_orders["A"])
        self.assertNotEqual(first_orders["B"], second_orders["B"])

    def test_every_record_is_agent_only_and_retains_payload_boundaries(self) -> None:
        artifact = self.load_artifact()
        records = [artifact]
        for run in artifact["runs"]:
            records.append(run)
            records.extend(run["packets"])
            records.extend(run["observations"])
        for record in records:
            self.assertEqual(record["reviewer_kind"], "agent")
            self.assertFalse(record["human_review"])
            self.assertTrue(record["research_only"])
            self.assertTrue(record["non_canonical"])
            self.assertEqual(record["promotion_decision"], "not-determined")
        for run in artifact["runs"]:
            for observation in run["observations"]:
                self.assertTrue(observation["candidate_statement"])
                self.assertTrue(observation["candidate_digest"].startswith("sha256:"))
                self.assertTrue(observation["evidence_ids"])
                self.assertTrue(observation["evidence_excerpt_digests"])
                self.assertTrue(observation["source_ids"])
                self.assertTrue(observation["negative_knowledge_refs"])
                self.assertTrue(observation["negative_knowledge_digests"])
                self.assertEqual(
                    observation["timing"]["measurement_status"], "observed"
                )
                self.assertGreaterEqual(observation["timing"]["elapsed_seconds"], 0)

    def test_mutating_candidate_digest_is_rejected(self) -> None:
        artifact = self.load_artifact()
        artifact["runs"][0]["observations"][0]["candidate_digest"] = (
            "sha256:" + "0" * 64
        )
        with self.assertRaises(MODULE.PilotError):
            MODULE.validate_artifact(artifact)

    def test_holdout_payload_is_not_copied(self) -> None:
        artifact = self.load_artifact()
        rendered = json.dumps(artifact["runs"])
        for task_id in (
            "task-03-storage-mechanism",
            "task-06-stream-history",
            "task-09-reconciliation",
            "task-12-boundary-isolation",
        ):
            self.assertNotIn(task_id, rendered)


if __name__ == "__main__":
    unittest.main()

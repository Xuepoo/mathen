import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/enriched_review_packet.py"
SPEC = importlib.util.spec_from_file_location("enriched_review_packet", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class EnrichedReviewPacketTests(unittest.TestCase):
    def test_fixture_matches_deterministic_builder(self) -> None:
        artifact = json.loads(
            (ROOT / "data/research-review/mth-0185-enriched-study.json").read_text()
        )
        self.assertEqual(artifact, MODULE.build_packet())
        MODULE.validate_packet(artifact)

    def test_assignments_are_local_and_complete(self) -> None:
        packet = MODULE.build_packet()
        self.assertEqual(packet["balance"]["packet_labels"], ["A", "B"])
        self.assertEqual(
            [len(item["assignments"]) for item in packet["packets"]], [8, 8]
        )
        for reviewer_packet in packet["packets"]:
            for assignment in reviewer_packet["assignments"]:
                candidate = assignment["candidate"]
                self.assertTrue(candidate["statement"])
                self.assertIn(candidate["claim_type"], MODULE.CLAIM_TYPES)
                self.assertFalse(candidate["proven"])
                self.assertEqual(
                    set(candidate["evidence_ids"]),
                    {item["evidence_id"] for item in assignment["evidence"]},
                )
                self.assertTrue(assignment["locality"]["candidate_evidence_local"])
                for evidence in assignment["evidence"]:
                    self.assertTrue(evidence["excerpt"])
                    self.assertTrue(evidence["excerpt_digest"].startswith("sha256:"))
                self.assertTrue(assignment["negative_knowledge"])

    def test_holdout_content_is_not_present(self) -> None:
        packet = MODULE.build_packet()
        isolation = packet["holdout_isolation"]
        self.assertEqual(
            set(isolation["task_ids"]),
            {
                "task-03-storage-mechanism",
                "task-06-stream-history",
                "task-09-reconciliation",
                "task-12-boundary-isolation",
            },
        )
        rendered = json.dumps(packet["packets"])
        for task_id in isolation["task_ids"]:
            self.assertNotIn(task_id, rendered)
        self.assertFalse(isolation["candidate_content_in_packets"])
        self.assertFalse(isolation["evidence_content_in_packets"])

    def test_source_candidate_and_evidence_digests_are_distinct(self) -> None:
        packet = MODULE.build_packet()
        source_digest = packet["frozen_inputs"]["source_digests"]["benchmark"]
        assignment = packet["packets"][0]["assignments"][0]
        self.assertNotEqual(source_digest, assignment["candidate"]["candidate_digest"])
        self.assertNotEqual(
            assignment["candidate"]["candidate_digest"],
            assignment["evidence"][0]["excerpt_digest"],
        )

    def test_mutation_and_promotion_are_rejected(self) -> None:
        packet = MODULE.build_packet()
        packet["results"]["promotion_decision"] = "accepted"
        with self.assertRaises(MODULE.PacketError):
            MODULE.validate_packet(packet)


if __name__ == "__main__":
    unittest.main()

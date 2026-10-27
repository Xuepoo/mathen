import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/agent_review_pilot_b.py"
SPEC = importlib.util.spec_from_file_location("agent_review_pilot_b", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AgentReviewPilotBTests(unittest.TestCase):
    def test_checked_in_pilot_is_valid_packet_b(self) -> None:
        pilot = json.loads(
            (ROOT / "data/research-review/pilots/mth-0187.json").read_text()
        )
        MODULE.validate_pilot(pilot)
        self.assertEqual(pilot["record_kind"], "agent-review-pilot")
        self.assertEqual(pilot["pilot_kind"], "agent-review-pilot")
        self.assertEqual(pilot["packet_label"], "B")
        self.assertFalse(pilot["provenance"]["human_review"])
        self.assertEqual(pilot["provenance"]["execution_actor"], "llm-based-agent")
        self.assertEqual(pilot["provenance"]["provider"], "not-recorded")
        self.assertEqual(pilot["provenance"]["model"], "not-recorded")
        self.assertEqual(len(pilot["review_records"]), 8)
        self.assertEqual(pilot["promotion_decision"], "not-determined")

    def test_records_retain_packet_payload_digests_and_timing(self) -> None:
        pilot = json.loads(
            (ROOT / "data/research-review/pilots/mth-0187.json").read_text()
        )
        for record in pilot["review_records"]:
            self.assertTrue(record["candidate_statement"])
            self.assertTrue(record["evidence_excerpt_digests"])
            self.assertTrue(record["negative_knowledge_refs"])
            self.assertTrue(record["negative_knowledge_digests"])
            self.assertTrue(record["locality"]["candidate_evidence_local"])
            self.assertEqual(record["timing"]["measurement_status"], "observed")
            self.assertGreaterEqual(record["timing"]["elapsed_seconds"], 0)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/agent_review_pilot.py"
SPEC = importlib.util.spec_from_file_location("agent_review_pilot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


class AgentReviewPilotTests(unittest.TestCase):
    def test_checked_in_pilot_is_valid_and_packet_a_only(self) -> None:
        pilot = json.loads(
            (ROOT / "data/research-review/pilots/mth-0186.json").read_text()
        )
        MODULE.validate_pilot(pilot)
        self.assertEqual(pilot["record_kind"], "agent-review-pilot")
        self.assertEqual(pilot["pilot_kind"], "agent-review-pilot")
        self.assertFalse(pilot["provenance"]["human_review"])
        self.assertEqual(pilot["provenance"]["execution_actor"], "llm-based-agent")
        self.assertEqual(pilot["provenance"]["provider"], "not-recorded")
        self.assertEqual(pilot["provenance"]["model"], "not-recorded")
        self.assertEqual(pilot["packet_label"], "A")
        self.assertEqual(len(pilot["review_records"]), 8)
        self.assertEqual(pilot["promotion_decision"], "not-determined")

    def test_every_record_retains_evidence_boundary_and_timing(self) -> None:
        pilot = json.loads(
            (ROOT / "data/research-review/pilots/mth-0186.json").read_text()
        )
        for record in pilot["review_records"]:
            self.assertTrue(record["candidate_digest"].startswith("sha256:"))
            self.assertTrue(record["evidence_ids"])
            self.assertTrue(record["negative_knowledge_refs"])
            self.assertEqual(record["locality"]["candidate_evidence_local"], True)
            self.assertEqual(record["timing"]["measurement_status"], "observed")
            self.assertGreaterEqual(record["timing"]["elapsed_seconds"], 0)


if __name__ == "__main__":
    unittest.main()

import importlib.util
import json
import sys
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "reviewer_pilot.py"
SPEC = importlib.util.spec_from_file_location("reviewer_pilot", SCRIPT)
assert SPEC and SPEC.loader
PILOT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = PILOT
SPEC.loader.exec_module(PILOT)


class ReviewerPilotTests(unittest.TestCase):
    def test_checked_in_mth_0180_has_bounded_agent_provenance(self) -> None:
        record = json.loads(
            (ROOT / "data/research-review/pilots/mth-0180.json").read_text()
        )
        self.assertEqual(record["record_kind"], "agent-review-pilot")
        self.assertEqual(record["provenance"]["execution_actor"], "llm-based-agent")
        self.assertEqual(record["provenance"]["provider"], "not-recorded")
        self.assertEqual(record["provenance"]["model"], "not-recorded")
        self.assertEqual(record["promotion_decision"], "not-determined")

    def test_packet_b_record_is_digest_linked_and_non_promoting(self) -> None:
        study_path = ROOT / "data/research-review/mth-0175-study.json"
        study = json.loads(study_path.read_text(encoding="utf-8"))
        packet = study["packets"][1]
        records = [
            {
                "review_id": f"mth-0181-b-{assignment['task_id']}",
                "reviewer_key": packet["reviewer_key"],
                "task_id": assignment["task_id"],
                "labels": {
                    dimension: "unknown"
                    for dimension in PILOT.REVIEWER_STUDY.REVIEW_DIMENSIONS
                },
                "timing": {
                    "started_at": "2026-10-27T06:00:00.000Z",
                    "ended_at": "2026-10-27T06:00:01.000Z",
                    "elapsed_seconds": 1,
                },
                "notes": (
                    "Evidence content was not supplied in the assignment snapshot."
                ),
            }
            for assignment in packet["assignments"]
        ]
        record = PILOT._record_metadata(
            study,
            packet,
            {
                "started_at": "2026-10-27T06:00:00.000Z",
                "ended_at": "2026-10-27T06:00:04.000Z",
                "elapsed_seconds": 4,
            },
            records,
        )
        with TemporaryDirectory() as directory:
            path = Path(directory) / "pilot.json"
            path.write_text(json.dumps(record), encoding="utf-8")
            report = PILOT.validate(study_path, path)
        self.assertEqual(report["promotion_decision"], "not-determined")
        self.assertEqual(record["pilot_kind"], "agent-review-pilot")
        self.assertTrue(record["non_canonical"])
        self.assertEqual(record["provenance"]["execution_actor"], "llm-based-agent")
        self.assertEqual(record["provenance"]["provider"], "not-recorded")
        self.assertEqual(record["provenance"]["model"], "not-recorded")


if __name__ == "__main__":
    unittest.main()

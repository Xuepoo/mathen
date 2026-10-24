import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mathen.cards import validate_card

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "g5_sqlite_transaction_experiment.py"


class SQLiteExperimentTests(unittest.TestCase):
    def test_fixed_transaction_protocol_is_repeatable(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--expected-source-id",
                    self.source_id(),
                    "--repetitions",
                    "2",
                    "--output",
                    str(output),
                ],
                check=True,
                capture_output=True,
                text=True,
            )

            report = json.loads(output.read_text(encoding="utf-8"))
        self.assertEqual(report["kind"], "experiment")
        self.assertEqual(
            report["system_commit"],
            self.source_id(),
        )
        self.assertEqual(report["repetitions"], 2)
        self.assertEqual(report["metrics"]["rollback_preserved_rows"], 4)
        self.assertEqual(report["metrics"]["recovered_rows"], 5)
        self.assertEqual(report["metrics"]["integrity_checks_passed"], 2)
        self.assertEqual(report["metrics"]["rollback_checks_passed"], 2)
        self.assertEqual(report["metrics"]["repetitions_consistent"], 1)
        self.assertIn('"repetitions_consistent": 1', completed.stdout)
        self.validate_evidence(report)
        for result in report["artifacts"][0]["results"]:
            self.assertEqual(result["after_rollback"], result["seeded"])
            self.assertEqual(result["reopened"], result["recovered"])
            self.assertEqual(result["recovered"]["rows"][-1], [5, "epsilon", 50])

    @staticmethod
    def source_id() -> str:
        connection = sqlite3.connect(":memory:")
        source_id = connection.execute("SELECT sqlite_source_id()").fetchone()[0]
        connection.close()
        return source_id.split()[-1]

    @staticmethod
    def validate_evidence(report: dict) -> None:
        card = json.loads(
            (ROOT / "data/systems/sqlite.json").read_text(encoding="utf-8")
        )
        card["evidence"].append(report)
        validate_card(card)

    def test_recorded_evidence_is_valid_and_has_all_observations(self) -> None:
        report = json.loads(
            (ROOT / "data/experiments/g5-sqlite-transaction-results.json").read_text(
                encoding="utf-8"
            )
        )
        self.validate_evidence(report)
        self.assertEqual(len(report["artifacts"][0]["results"]), report["repetitions"])
        self.assertEqual(
            report["artifacts"][0]["runner_sha256"],
            hashlib.sha256(SCRIPT.read_bytes()).hexdigest(),
        )
        for result in report["artifacts"][0]["results"]:
            self.assertEqual(result["seeded"], result["after_rollback"])
            self.assertEqual(result["recovered"], result["reopened"])
            self.assertEqual(result["recovered"]["row_count"], 5)
            self.assertEqual(result["integrity_check"], "ok")

    def test_wrong_source_id_is_rejected_without_writing_results(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--expected-source-id",
                    "wrong",
                    "--output",
                    str(output),
                ],
                capture_output=True,
                text=True,
            )
            self.assertNotEqual(completed.returncode, 0)
            self.assertIn("SQLite source ID differs", completed.stderr)
            self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()

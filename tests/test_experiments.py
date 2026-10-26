import hashlib
import json
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from mathen.cards import validate_card
from mathen.evidence import ObservationEvidence
from mathen.mathviews import load_math_view_contract

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "g5_sqlite_transaction_experiment.py"
WAL_SCRIPT = ROOT / "scripts" / "g5_sqlite_wal_visibility_experiment.py"


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
            hashlib.sha256(SCRIPT.read_bytes().replace(b"\r\n", b"\n")).hexdigest(),
        )
        for result in report["artifacts"][0]["results"]:
            self.assertEqual(result["seeded"], result["after_rollback"])
            self.assertEqual(result["recovered"], result["reopened"])
            self.assertEqual(result["recovered"]["row_count"], 5)
            self.assertEqual(result["integrity_check"], "ok")

    def test_mth0152_observation_evidence_is_valid(self) -> None:
        report = json.loads(
            (
                ROOT
                / "data/experiments/g5-sqlite-transaction-mth-0152-observation.json"
            ).read_text(encoding="utf-8")
        )
        card = json.loads(
            (ROOT / "data/systems/sqlite.json").read_text(encoding="utf-8")
        )
        validate_card(card)
        self.assertIn(
            report["id"],
            {evidence["id"] for evidence in card["evidence"]},
        )
        self.assertEqual(report["observation_version"], "1")
        self.assertEqual(report["result"]["status"], "observed")
        self.assertEqual(report["metrics"]["repetitions_consistent"], 1)
        self.assertFalse(report["result_boundary"]["canonical"])

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

    def test_wal_visibility_observation_is_reproducible_and_bounded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    str(WAL_SCRIPT),
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
        self.assertEqual(
            report["environment"]["sqlite_source_id"].split()[-1], self.source_id()
        )
        self.assertEqual(report["metrics"]["snapshot_rows_during_writer_commit"], 4)
        self.assertEqual(report["metrics"]["writer_rows_after_commit"], 5)
        self.assertEqual(report["metrics"]["refreshed_reader_rows"], 5)
        self.assertEqual(report["metrics"]["snapshot_checks_passed"], 2)
        self.assertEqual(report["metrics"]["refresh_checks_passed"], 2)
        self.assertEqual(report["metrics"]["repetitions_consistent"], 1)
        self.assertIn('"snapshot_checks_passed": 2', completed.stdout)

    def test_recorded_wal_observation_and_standalone_view_validate(self) -> None:
        observation_path = (
            ROOT / "data/experiments/g5-sqlite-wal-visibility-observation.json"
        )
        observation = json.loads(observation_path.read_text(encoding="utf-8"))
        card = json.loads(
            (ROOT / "data/systems/sqlite.json").read_text(encoding="utf-8")
        )
        card["evidence"].append(observation)
        ObservationEvidence.from_dict(
            observation, {item["id"] for item in card["evidence"]}
        )
        validate_card(card)

        view_path = ROOT / "data/mathviews/sqlite-wal-snapshot-visibility-mth-0156.json"
        view = load_math_view_contract(view_path)
        self.assertEqual(view.to_dict()["classification"]["result"], "valid")
        self.assertEqual(len(view.to_dict()["validation_records"]), 2)


if __name__ == "__main__":
    unittest.main()

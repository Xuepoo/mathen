import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mathen.cli import validate_negative_knowledge_command
from mathen.negative_knowledge import (
    NEGATIVE_KNOWLEDGE_SCHEMA_VERSION,
    NegativeKnowledgeRecord,
    NegativeKnowledgeValidationError,
    validate_negative_knowledge,
    validate_negative_knowledge_collection,
)

ROOT = Path(__file__).parents[1]


class NegativeKnowledgeTests(unittest.TestCase):
    def test_representative_fixture_validates_and_round_trips(self) -> None:
        value = json.loads(
            (
                ROOT / "data" / "negative-knowledge" / "contract-boundaries.json"
            ).read_text()
        )
        validate_negative_knowledge(value)
        record = NegativeKnowledgeRecord.from_dict(value)
        self.assertEqual(record.schema_version, NEGATIVE_KNOWLEDGE_SCHEMA_VERSION)
        self.assertEqual(record.to_dict(), value)

    def test_cli_validates_fixture_and_empty_directory(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(
                validate_negative_knowledge_command(
                    ROOT / "data" / "negative-knowledge"
                ),
                0,
            )
        self.assertIn("contract-boundaries.json", output.getvalue())
        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(
                    validate_negative_knowledge_command(Path(directory)), 0
                )
            self.assertIn("nothing to validate", output.getvalue())

    def test_unbounded_language_is_rejected(self) -> None:
        value = self._fixture()
        value["negative_claim"] = "This never composes."
        with self.assertRaisesRegex(NegativeKnowledgeValidationError, "universal"):
            validate_negative_knowledge(value)

    def test_counterexample_requires_local_evidence_and_implication(self) -> None:
        value = self._fixture()
        del value["counterexamples"][0]["implication"]
        with self.assertRaisesRegex(NegativeKnowledgeValidationError, "missing fields"):
            validate_negative_knowledge(value)
        value = self._fixture()
        value["counterexamples"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(
            NegativeKnowledgeValidationError, "unknown evidence"
        ):
            validate_negative_knowledge(value)

    def test_lifecycle_and_composition_kinds_require_links(self) -> None:
        value = self._fixture()
        value["kind"] = "supersession"
        with self.assertRaisesRegex(
            NegativeKnowledgeValidationError, "related_claim_ids"
        ):
            validate_negative_knowledge(value)
        value = self._fixture()
        value["kind"] = "invalid-composition"
        value["composition"] = {
            "inputs": ["append-log", "snapshot"],
            "operation": "compose guarantees",
            "failure_mode": "the stronger guarantee is not established",
        }
        validate_negative_knowledge(value)

    def test_collection_resolves_valid_lifecycle_links(self) -> None:
        original = self._fixture()
        original["id"] = "original-claim"
        original["kind"] = "failed-hypothesis"
        retraction = self._fixture()
        retraction["id"] = "retracted-claim"
        retraction["kind"] = "retraction"
        retraction["related_claim_ids"] = ["original-claim"]
        supersession = self._fixture()
        supersession["id"] = "superseding-claim"
        supersession["kind"] = "supersession"
        supersession["related_claim_ids"] = ["original-claim"]
        supersession["replacement_id"] = "retracted-claim"

        validate_negative_knowledge_collection([original, retraction, supersession])

    def test_collection_rejects_dangling_lifecycle_links(self) -> None:
        retraction = self._fixture()
        retraction["kind"] = "retraction"
        retraction["related_claim_ids"] = ["missing-claim"]
        with self.assertRaisesRegex(
            NegativeKnowledgeValidationError, "related_claim_ids.*unknown"
        ):
            validate_negative_knowledge_collection([retraction])

        supersession = self._fixture()
        supersession["kind"] = "supersession"
        supersession["related_claim_ids"] = ["existing-claim"]
        supersession["replacement_id"] = "missing-replacement"
        existing = self._fixture()
        existing["id"] = "existing-claim"
        with self.assertRaisesRegex(
            NegativeKnowledgeValidationError, "replacement_id.*unknown"
        ):
            validate_negative_knowledge_collection([existing, supersession])

    def test_cli_validates_lifecycle_links_across_files(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            original = self._fixture()
            original["id"] = "original-claim"
            retraction = self._fixture()
            retraction["id"] = "retracted-claim"
            retraction["kind"] = "retraction"
            retraction["related_claim_ids"] = ["original-claim"]
            (path / "original.json").write_text(json.dumps(original), encoding="utf-8")
            (path / "retraction.json").write_text(
                json.dumps(retraction), encoding="utf-8"
            )

            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(validate_negative_knowledge_command(path), 0)
            self.assertIn("original.json", output.getvalue())
            self.assertIn("retraction.json", output.getvalue())

            retraction["related_claim_ids"] = ["missing-claim"]
            (path / "retraction.json").write_text(
                json.dumps(retraction), encoding="utf-8"
            )
            with self.assertRaisesRegex(
                NegativeKnowledgeValidationError, "related_claim_ids.*unknown"
            ):
                validate_negative_knowledge_command(path)

    @staticmethod
    def _fixture() -> dict:
        return {
            "schema_version": "1.0",
            "id": "bounded-counterexample",
            "name": "Bounded counterexample",
            "summary": "A bounded negative claim.",
            "kind": "failed-hypothesis",
            "negative_claim": (
                "The candidate does not establish the target guarantee under the "
                "stated conditions."
            ),
            "bounded": True,
            "scope": {
                "systems": ["fixture"],
                "versions": ["v1"],
                "deployment_origins": ["test-origin"],
                "conditions": ["controlled test"],
                "exclusions": ["other versions"],
            },
            "counterexamples": [
                {
                    "id": "failed-case",
                    "description": "The candidate fails in the controlled case.",
                    "implication": (
                        "Do not infer the target guarantee from the candidate shape."
                    ),
                    "claim_type": "fact",
                    "claim_status": "proposed",
                    "evidence_ids": ["fixture-evidence"],
                }
            ],
            "claim_type": "hypothesis",
            "claim_status": "proposed",
            "evidence_ids": ["fixture-evidence"],
            "evidence": [
                {
                    "id": "fixture-evidence",
                    "kind": "experiment",
                    "title": "Controlled failure",
                    "uri": "https://example.test/failure",
                }
            ],
        }


if __name__ == "__main__":
    unittest.main()

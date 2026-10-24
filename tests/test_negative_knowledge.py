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

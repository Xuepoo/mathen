import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mathen.benchmark import (
    BenchmarkManifestValidationError,
    BenchmarkRunManifest,
    citation_precision,
    claim_discipline,
    classification_metrics,
    counterexample_recall,
    evidence_locality,
    load_benchmark_manifest,
    typed_obligation_satisfaction,
    validate_benchmark_manifest,
)
from mathen.cli import validate_benchmark_command

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "benchmark-run-valid.json"


class BenchmarkManifestTests(unittest.TestCase):
    def test_fixture_round_trips_and_cli_validates(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        validate_benchmark_manifest(value)
        self.assertEqual(BenchmarkRunManifest.from_dict(value).to_dict(), value)
        self.assertEqual(load_benchmark_manifest(FIXTURE).to_dict(), value)
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(validate_benchmark_command(FIXTURE), 0)
        self.assertIn("valid", output.getvalue())

    def test_candidates_cannot_be_proven_or_cite_outside_bundle(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["candidates"][0]["proven"] = True
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "proven"):
            validate_benchmark_manifest(value)
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["candidates"][0]["claims"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "unknown"):
            validate_benchmark_manifest(value)

    def test_manifest_rejects_undeclared_fields(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["unexpected"] = True
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "unknown fields"):
            validate_benchmark_manifest(value)

    def test_model_is_detached(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        model = BenchmarkRunManifest.from_dict(value)
        value["candidates"][0]["proven"] = False
        self.assertTrue(model.to_dict()["candidates"][0]["claims"])


class BenchmarkMetricTests(unittest.TestCase):
    def test_evidence_locality_and_citation_precision_keep_denominators(self) -> None:
        claims = [
            {"evidence_ids": ["a"]},
            {"evidence_ids": ["outside"]},
            {"evidence_ids": []},
        ]
        locality = evidence_locality(claims, {"a"})
        self.assertEqual((locality.numerator, locality.denominator), (1, 3))
        self.assertEqual(
            citation_precision([{"supported": True}, {"supported": False}]).value, 0.5
        )
        self.assertIsNone(citation_precision([]).value)

    def test_claim_discipline_separates_type_accuracy_and_unsupported_types(
        self,
    ) -> None:
        metrics = claim_discipline(
            [
                {
                    "claim_type": "fact",
                    "expected_claim_type": "fact",
                    "supported": True,
                },
                {
                    "claim_type": "hypothesis",
                    "expected_claim_type": "inference",
                    "supported": False,
                },
            ]
        )
        self.assertEqual(metrics["claim_type_accuracy"].value, 0.5)
        self.assertEqual(metrics["unsupported_hypothesis_rate"].value, 1.0)
        self.assertIsNone(metrics["unsupported_analogy_rate"].value)

    def test_classification_reports_three_outcomes_and_confusion(self) -> None:
        result = classification_metrics(
            [
                {"expected": "valid", "predicted": "valid"},
                {"expected": "invalid", "predicted": "valid"},
                {"expected": "undetermined", "predicted": "undetermined"},
            ]
        )
        self.assertEqual(result["accuracy"].value, 2 / 3)
        self.assertEqual(result["confusion"]["invalid"]["valid"], 1)
        self.assertEqual(result["by_outcome"]["invalid"]["recall"].value, 0.0)

    def test_typed_obligations_require_explicit_provisions_or_adapters(self) -> None:
        result = typed_obligation_satisfaction(
            ["read", "write"],
            ["read", "wire-format"],
            [{"requirement": "write", "provision": "wire-format"}],
        )
        self.assertEqual((result.numerator, result.denominator), (2, 2))
        self.assertEqual(
            typed_obligation_satisfaction(["write"], ["wire-format"]).value, 0.0
        )

    def test_counterexample_recall_is_set_based_and_bounded(self) -> None:
        result = counterexample_recall(["a", "b"], ["b", "c"])
        self.assertEqual((result.numerator, result.denominator), (1, 2))
        self.assertIsNone(counterexample_recall([], ["a"]).value)


if __name__ == "__main__":
    unittest.main()

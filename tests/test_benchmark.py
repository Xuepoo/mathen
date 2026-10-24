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
    def test_schema_declares_python_list_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "benchmark-run-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["source_revisions"]["minItems"], 1)
        self.assertEqual(schema["$defs"]["stringList"]["minItems"], 0)
        self.assertEqual(schema["$defs"]["nonEmptyStringList"]["minItems"], 1)
        self.assertEqual(
            schema["properties"]["input_ids"]["required"],
            [
                "systems",
                "features",
                "views",
                "microstructures",
                "compositions",
                "analogies",
                "negative_knowledge",
            ],
        )
        self.assertEqual(
            schema["properties"]["deployment"]["required"],
            ["origin", "version", "conditions", "exclusions"],
        )
        self.assertEqual(
            schema["$defs"]["candidate"]["properties"]["evidence_ids"]["$ref"],
            "#/$defs/nonEmptyStringList",
        )
        self.assertEqual(
            schema["$defs"]["claim"]["properties"]["evidence_ids"]["$ref"],
            "#/$defs/nonEmptyStringList",
        )
        self.assertTrue(
            schema["properties"]["evidence_bundle"]["properties"]["evidence_ids"][
                "uniqueItems"
            ]
        )
        self.assertEqual(
            schema["$defs"]["candidate"]["required"],
            ["id", "evidence_ids", "claims", "validation_logs", "proven"],
        )
        self.assertEqual(
            schema["$defs"]["validationLog"]["required"],
            ["check", "result", "reason"],
        )
        self.assertEqual(
            schema["$defs"]["candidate"]["properties"]["proven"], {"const": False}
        )

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
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["candidates"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "unknown"):
            validate_benchmark_manifest(value)

    def test_candidate_and_claim_evidence_ids_must_be_non_empty(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["candidates"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "must not be empty"
        ):
            validate_benchmark_manifest(value)

        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["candidates"][0]["claims"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "must not be empty"
        ):
            validate_benchmark_manifest(value)

    def test_empty_input_and_deployment_lists_remain_valid(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["input_ids"]["systems"] = []
        value["deployment"]["conditions"] = []
        value["deployment"]["exclusions"] = []
        value["deployment"]["origin"] = "another-configured-origin"
        validate_benchmark_manifest(value)

    def test_optional_provenance_strings_are_non_empty_and_paired(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["provenance"]["provider"] = "provider"
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "together"):
            validate_benchmark_manifest(value)

        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["provenance"]["provider"] = ""
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "non-empty"):
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

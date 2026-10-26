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
    heldout_counterexample_recall,
    load_benchmark_manifest,
    load_retrieval_evaluation_manifest,
    ndcg_at_k,
    novelty_scope_completeness,
    recall_at_k,
    retrieval_abstention_rate,
    retrieval_claim_type_accuracy,
    retrieval_digest,
    retrieval_false_link_rate,
    retrieval_scope_completeness,
    typed_obligation_satisfaction,
    validate_benchmark_manifest,
    validate_retrieval_evaluation_manifest,
)
from mathen.cli import validate_benchmark_command

ROOT = Path(__file__).parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "benchmark-run-valid.json"
RETRIEVAL_FIXTURE = ROOT / "tests" / "fixtures" / "retrieval-evaluation-valid.json"


class BenchmarkManifestTests(unittest.TestCase):
    def test_schema_declares_python_list_contract(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "benchmark-run-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.1")
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
        self.assertIn("input_evidence", schema["required"])
        self.assertIn("split", schema["required"])
        self.assertIn("novelty", schema["required"])
        self.assertIn("analogy_policy", schema["required"])
        self.assertIn("result_boundary", schema["required"])

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
        value["candidates"][0]["evidence_ids"] = ["evidence-1", "evidence-1"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "unique"):
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
        del value["input_evidence"]["systems:fixture-system"]
        value["split"]["partitions"]["evaluation"] = []
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

    def test_manifest_rejects_archive_digest_mismatch(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["source_revisions"][0]["archive_digest"] = "sha256:archive"
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "digest mismatch"
        ):
            validate_benchmark_manifest(value)

    def test_manifest_requires_source_bundle_digest_linkage(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del value["evidence_bundle"]["source_revision_digests"]["fixture-repository"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "cover exactly"):
            validate_benchmark_manifest(value)

    def test_manifest_closes_digest_split_and_boundary_contracts(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["provenance"]["input_bundle_digest"] = "sha256:other"
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "must equal"):
            validate_benchmark_manifest(value)

        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["split"]["partitions"]["train"] = ["systems:fixture-system"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "disjoint"):
            validate_benchmark_manifest(value)

        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["result_boundary"]["canonical"] = True
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "canonical"):
            validate_benchmark_manifest(value)

    def test_manifest_rejects_missing_input_evidence_and_holdout_exposure(self) -> None:
        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        del value["input_evidence"]["systems:fixture-system"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "exactly"):
            validate_benchmark_manifest(value)

        value = json.loads(FIXTURE.read_text(encoding="utf-8"))
        value["input_ids"]["negative_knowledge"] = ["nk-1"]
        value["input_evidence"]["negative_knowledge:nk-1"] = ["source-evidence"]
        value["split"]["partitions"]["holdout"] = ["negative_knowledge:nk-1"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "held out"):
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
        self.assertEqual(result["abstention_rate"].value, 1 / 3)
        self.assertEqual(result["coverage"].value, 2 / 3)
        self.assertEqual(result["unknown_recall"].value, 1.0)

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


class RetrievalEvaluationManifestTests(unittest.TestCase):
    def test_fixture_round_trips_and_digest_is_reproducible(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "retrieval-evaluation-manifest.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            schema["properties"]["manifest_kind"]["const"], "retrieval_evaluation"
        )
        self.assertIn("document", schema["$defs"]["result"]["required"])
        self.assertIn("provenance", schema["$defs"]["result"]["required"])
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        validate_retrieval_evaluation_manifest(value)
        self.assertEqual(
            load_retrieval_evaluation_manifest(RETRIEVAL_FIXTURE).to_dict(), value
        )
        self.assertEqual(
            value["corpus_snapshot"]["digest"],
            retrieval_digest(value["corpus_snapshot"]["documents"]),
        )

    def test_retrieval_rejects_digest_split_and_holdout_boundary_changes(self) -> None:
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["corpus_snapshot"]["digest"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "corpus_snapshot.digest"
        ):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["split"]["partitions"]["holdout"] = []
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "cover all query"
        ):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["split"]["candidate_generation_exclusions"] = []
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "excluded"):
            validate_retrieval_evaluation_manifest(value)

    def test_retrieval_rejects_novelty_analogy_and_result_boundaries(self) -> None:
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["boundaries"]["novelty"]["aggregate_score_allowed"] = True
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "aggregate"):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["boundaries"]["analogy"]["non_equivalence_required"] = False
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "non_equivalence"
        ):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["result_boundary"]["score_is_truth"] = True
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "discovery-only"):
            validate_retrieval_evaluation_manifest(value)

    def test_retrieval_rejects_unknown_or_unlocal_evidence_results(self) -> None:
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["results"][0]["results"][0]["document"]["evidence_ids"] = ["outside"]
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "local"):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["results"][0]["results"][0]["document"]["id"] = "draft:unreviewed"
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "not in corpus"):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["results"][0]["results"][0]["provenance"]["source_digest"] = (
            "sha256:" + "0" * 64
        )
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "does not match"):
            validate_retrieval_evaluation_manifest(value)

    def test_retrieval_requires_nonempty_labels_and_contiguous_ranks(self) -> None:
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["labels"]["relevance"][0]["evidence_ids"] = []
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "must not be empty"
        ):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["results"][0]["results"][0]["rank"] = 2
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "contiguous"):
            validate_retrieval_evaluation_manifest(value)

    def test_retrieval_rejects_undeclared_fields_and_unpaired_model(self) -> None:
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["unexpected"] = True
        with self.assertRaisesRegex(BenchmarkManifestValidationError, "unknown fields"):
            validate_retrieval_evaluation_manifest(value)

        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        value["model"]["model_id"] = None
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "supplied together"
        ):
            validate_retrieval_evaluation_manifest(value)

    def test_retrieval_scope_context_is_optional_but_validated_and_local(self) -> None:
        value = json.loads(RETRIEVAL_FIXTURE.read_text(encoding="utf-8"))
        document = value["corpus_snapshot"]["documents"][0]
        unspecified = {
            "validity_scope": {
                "status": "unspecified",
                "systems": [],
                "versions": [],
                "deployment_origins": [],
                "conditions": [],
                "exclusions": [],
                "evidence_ids": [],
            },
            **{
                field: {"status": "unspecified", "values": [], "evidence_ids": []}
                for field in (
                    "workload",
                    "runtime_conditions",
                    "scale",
                    "failure_conditions",
                )
            },
        }
        document["scope_context"] = unspecified
        value["corpus_snapshot"]["digest"] = retrieval_digest(
            value["corpus_snapshot"]["documents"]
        )
        result_document = value["results"][0]["results"][0]["document"]
        result_document["scope_context"] = unspecified
        validate_retrieval_evaluation_manifest(value)

        result_document["scope_context"]["workload"]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(
            BenchmarkManifestValidationError, "unknown evidence"
        ):
            validate_retrieval_evaluation_manifest(value)

    def test_retrieval_discovery_metrics_keep_bounded_denominators(self) -> None:
        relevance = {"q": {"a": 3, "b": 1}}
        ranked = {"q": ["b", "a"]}
        recall = recall_at_k(relevance, ranked, 1)
        self.assertEqual((recall.numerator, recall.denominator), (1, 1))
        self.assertEqual(ndcg_at_k(relevance, ranked, 1).value, (2**1 - 1) / (2**3 - 1))
        self.assertIsNone(recall_at_k({"q": {}}, {"q": []}, 1).value)

        self.assertEqual(
            retrieval_claim_type_accuracy(
                [{"claim_type": "fact", "expected_claim_type": "fact"}]
            ).value,
            1.0,
        )
        self.assertEqual(
            retrieval_scope_completeness(
                [
                    {
                        "version_context": "1",
                        "deployment_origins": [],
                        "conditions": [],
                        "exclusions": [],
                    }
                ]
            ).value,
            1.0,
        )
        self.assertEqual(
            retrieval_false_link_rate([{"link_outcome": "false-link"}]).value,
            1.0,
        )
        self.assertEqual(
            retrieval_abstention_rate(
                [{"abstained": True}, {"abstained": False}]
            ).value,
            0.5,
        )
        self.assertIsNone(counterexample_recall([], ["a"]).value)

    def test_heldout_counterexample_recall_rejects_leakage(self) -> None:
        result = heldout_counterexample_recall(["a", "b"], ["b"])
        self.assertEqual((result.numerator, result.denominator), (1, 2))
        with self.assertRaisesRegex(ValueError, "exposed"):
            heldout_counterexample_recall(["a"], [], ["a"])

    def test_novelty_scope_completeness_keeps_empty_denominator(self) -> None:
        self.assertIsNone(novelty_scope_completeness([]).value)
        result = novelty_scope_completeness(
            [
                {
                    "dimension": "topology",
                    "reference_window": "window-1",
                    "representation": "graph-v1",
                    "scope": "system-x@v1",
                    "falsifiers": ["prior-art"],
                    "claim_type": "hypothesis",
                },
                {"dimension": "behavior", "claim_type": "fact"},
            ]
        )
        self.assertEqual((result.numerator, result.denominator), (1, 2))


if __name__ == "__main__":
    unittest.main()

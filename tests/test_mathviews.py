import copy
import io
import json
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory

from mathen.cards import CardValidationError, validate_card
from mathen.cli import validate_mathviews_command
from mathen.mathviews import (
    MathematicalViewContract,
    MathematicalViewValidationError,
    classify_math_view_contract,
    discover_math_view_contracts,
    load_math_view_contract,
    validate_math_view_contract,
)

ROOT = Path(__file__).parents[1]
FIXTURES = ROOT / "tests" / "fixtures"


class MathematicalViewContractTests(unittest.TestCase):
    def test_schema_is_versioned_and_exposes_contract_dimensions(self) -> None:
        schema = json.loads(
            (ROOT / "schemas" / "architecture-mathematical-view.schema.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(
            schema["$id"],
            "https://mathen.dev/schemas/architecture-mathematical-view.schema.json",
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertIn("classification", schema["required"])
        self.assertIn("state_space", schema["properties"])
        self.assertIn("queueing", schema["properties"]["family"]["enum"])

    def test_valid_partial_order_fixture_round_trips(self) -> None:
        value = self._fixture("math-view-valid.json")
        validate_math_view_contract(value, evidence_ids={"design-doc"})
        model = MathematicalViewContract.from_dict(value, evidence_ids={"design-doc"})
        self.assertEqual(model.to_dict(), value)
        self.assertEqual(classify_math_view_contract(value)["result"], "valid")

    def test_sqlite_mth0152_contract_is_valid(self) -> None:
        path = (
            ROOT
            / "data/mathviews/sqlite-crash-recovery-transition-system-mth-0152.json"
        )
        value = json.loads(path.read_text(encoding="utf-8"))
        validate_math_view_contract(value)
        self.assertEqual(value["family"], "state_machine")
        self.assertEqual(len(value["validation_records"]), 2)
        self.assertEqual(value["validation_records"][0]["result"]["status"], "observed")
        self.assertEqual(
            value["validation_records"][1]["result"]["status"], "not-established"
        )

    def test_validation_records_are_bounded_and_round_trip(self) -> None:
        value = self._fixture("math-view-validation-record.json")
        validate_math_view_contract(value, evidence_ids={"design-doc", "run-a"})
        model = MathematicalViewContract.from_dict(value, evidence_ids={"design-doc"})
        self.assertEqual(
            model.to_dict()["validation_records"], value["validation_records"]
        )

    def test_validation_records_reject_unclosed_or_proof_like_results(self) -> None:
        value = self._fixture("math-view-valid.json")
        record = self._validation_record()
        record["evidence_ids"] = ["missing"]
        value["validation_records"] = [record]
        with self.assertRaisesRegex(
            MathematicalViewValidationError, "unknown evidence"
        ):
            validate_math_view_contract(value, evidence_ids={"design-doc", "run-a"})

        value = self._fixture("math-view-valid.json")
        record = self._validation_record()
        record["kind"] = "invariant"
        record["result"] = {
            "status": "observed",
            "summary": "This proves the invariant for every implementation.",
        }
        value["validation_records"] = [record]
        with self.assertRaisesRegex(MathematicalViewValidationError, "status"):
            validate_math_view_contract(value, evidence_ids={"design-doc", "run-a"})

    def test_absence_of_evidence_is_not_a_negative_finding(self) -> None:
        value = self._fixture("math-view-valid.json")
        record = self._validation_record()
        record.update(
            {
                "id": "no-runtime-evidence",
                "kind": "absence-of-evidence",
                "basis": "absence-of-evidence",
                "result": {
                    "status": "not-established",
                    "summary": "No runtime result was established for this view.",
                },
                "question": "Was this view tested at runtime?",
                "what_not_established": "Runtime behavior was not established.",
            }
        )
        value["validation_records"] = [record]
        validate_math_view_contract(value, evidence_ids={"design-doc", "run-a"})

    def test_failed_predictions_counterexamples_invariants_and_negative_knowledge(
        self,
    ) -> None:
        records = []
        for kind, details, status in (
            (
                "failed-prediction",
                {
                    "target_claim": "The release order is observed at runtime.",
                    "condition": "A hotfix path bypasses the documented pipeline.",
                    "observed_result": "The bypass was observed.",
                },
                "failed",
            ),
            (
                "counterexample",
                {
                    "target_claim": "The release order covers every deployment path.",
                    "condition": "An emergency hotfix is deployed.",
                    "observed_result": "The hotfix skipped the test stage.",
                    "implication": "The view is bounded to the documented pipeline.",
                },
                "counterexample",
            ),
            (
                "invariant",
                {"condition": "The documented pipeline is used."},
                "invariant-under-conditions",
            ),
            (
                "negative-knowledge",
                {
                    "negative_claim": "The view does not establish hotfix behavior.",
                    "what_not_established": "Hotfix behavior remains unestablished.",
                },
                "not-established",
            ),
        ):
            record = self._validation_record()
            record.update(
                {
                    "id": f"release-order-{kind}",
                    "kind": kind,
                    "result": {
                        "status": status,
                        "summary": "A bounded result for the declared scope.",
                    },
                    **details,
                }
            )
            records.append(record)
        value = self._fixture("math-view-valid.json")
        value["validation_records"] = records
        validate_math_view_contract(value, evidence_ids={"design-doc", "run-a"})

    def test_standalone_loader_and_cli_validate_contract_file(self) -> None:
        fixture = FIXTURES / "math-view-valid.json"
        self.assertEqual(
            load_math_view_contract(fixture).to_dict(), self._fixture(fixture.name)
        )
        self.assertEqual(discover_math_view_contracts(fixture), [fixture])
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(validate_mathviews_command(fixture), 0)
        self.assertIn(f"valid  {fixture}", output.getvalue())

    def test_mathview_cli_empty_or_absent_directory_is_successful_noop(self) -> None:
        with TemporaryDirectory() as directory:
            empty_path = Path(directory) / "mathviews"
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(validate_mathviews_command(empty_path), 0)
            self.assertIn("nothing to validate", output.getvalue())

            empty_path.mkdir()
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(validate_mathviews_command(empty_path), 0)
            self.assertIn("nothing to validate", output.getvalue())

    def test_discovery_includes_nested_collection_members(self) -> None:
        with TemporaryDirectory() as directory:
            nested = Path(directory) / "batch" / "nested.json"
            nested.parent.mkdir()
            nested.write_text("{}", encoding="utf-8")
            self.assertEqual(discover_math_view_contracts(Path(directory)), [nested])

    def test_mathview_cli_reports_invalid_contract_path(self) -> None:
        with TemporaryDirectory() as directory:
            invalid_path = Path(directory) / "invalid.json"
            invalid_path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(
                MathematicalViewValidationError, "invalid JSON"
            ):
                validate_mathviews_command(invalid_path)

    def test_semilattice_requires_and_checks_operation_laws(self) -> None:
        value = self._fixture("math-view-valid.json")
        value.update(
            {
                "id": "join-semilattice",
                "family": "semilattice",
                "carrier": {
                    "kind": "flags",
                    "description": "Two finite feature flags.",
                    "elements": ["none", "read", "write"],
                },
                "operations": [
                    {
                        "id": "join",
                        "name": "Join",
                        "arity": 2,
                        "table": {
                            "none|none": "none",
                            "none|read": "read",
                            "none|write": "write",
                            "read|none": "read",
                            "read|read": "read",
                            "read|write": "write",
                            "write|none": "write",
                            "write|read": "write",
                            "write|write": "write",
                        },
                    }
                ],
                "relations": [],
                "laws_or_checks": [
                    {
                        "id": "associative",
                        "name": "Associative",
                        "description": "Join is associative.",
                        "check": "associative",
                    },
                    {
                        "id": "commutative",
                        "name": "Commutative",
                        "description": "Join is commutative.",
                        "check": "commutative",
                    },
                    {
                        "id": "idempotent",
                        "name": "Idempotent",
                        "description": "Join is idempotent.",
                        "check": "idempotent",
                    },
                ],
            }
        )
        value["classification"] = {
            "result": "valid",
            "reason": "The supplied finite operation table passes the declared laws.",
            "checks": [
                {"id": "associative", "result": "pass"},
                {"id": "commutative", "result": "pass"},
                {"id": "idempotent", "result": "pass"},
            ],
        }
        validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_reliability_rejects_probability_outside_unit_interval(self) -> None:
        value = self._fixture("math-view-valid.json")
        value.update(
            {
                "id": "bad-reliability",
                "family": "reliability",
                "parameters": {"availability": 1.2},
                "operations": [],
                "relations": [],
                "laws_or_checks": [],
            }
        )
        value["classification"] = {
            "result": "invalid",
            "reason": "Reliability probabilities must be within [0, 1].",
            "checks": [],
        }
        validate_math_view_contract(value, evidence_ids={"design-doc"})
        self.assertEqual(classify_math_view_contract(value)["result"], "invalid")

    def test_queueing_model_is_undetermined_without_required_rates(self) -> None:
        value = self._fixture("math-view-valid.json")
        value.update(
            {
                "id": "incomplete-queue",
                "family": "queueing",
                "parameters": {"arrival_rate": 2},
                "operations": [],
                "relations": [],
                "laws_or_checks": [],
            }
        )
        value["classification"] = {
            "result": "undetermined",
            "reason": (
                "A queueing model needs arrival_rate and service_rate parameters."
            ),
            "checks": [],
        }
        validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_state_machine_and_bisimulation_use_declared_state_space(self) -> None:
        value = self._fixture("math-view-valid.json")
        value.update(
            {
                "id": "bounded-state-machine",
                "family": "bisimulation",
                "carrier": {
                    "kind": "machine-state",
                    "description": "States of both transition systems.",
                    "elements": [
                        "left-ready",
                        "left-done",
                        "right-ready",
                        "right-done",
                    ],
                },
                "state_space": {
                    "states": ["left-ready", "left-done", "right-ready", "right-done"],
                    "initial": ["left-ready", "right-ready"],
                    "terminal": ["left-done", "right-done"],
                    "description": "Two observationally equivalent state machines.",
                },
                "operations": [],
                "relations": [
                    {
                        "id": "equivalence",
                        "name": "Observational relation",
                        "kind": "state-relation",
                        "pairs": [
                            ["left-ready", "right-ready"],
                            ["left-done", "right-done"],
                        ],
                    }
                ],
                "transitions": [
                    {
                        "id": "left-step",
                        "name": "Left step",
                        "source": "left-ready",
                        "target": "left-done",
                        "label": "complete",
                        "system": "left",
                    },
                    {
                        "id": "right-step",
                        "name": "Right step",
                        "source": "right-ready",
                        "target": "right-done",
                        "label": "complete",
                        "system": "right",
                    },
                ],
                "laws_or_checks": [
                    {
                        "id": "bisimulation-obligation",
                        "name": "Bisimulation obligation",
                        "description": (
                            "Each labeled transition is matched in both directions."
                        ),
                        "check": "bisimulation",
                    }
                ],
            }
        )
        value["classification"] = {
            "result": "valid",
            "reason": (
                "The declared state relation satisfies the supplied transition "
                "obligations."
            ),
            "checks": [{"id": "bisimulation-obligation", "result": "pass"}],
        }
        validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_dag_classifies_all_declared_relations(self) -> None:
        value = self._fixture("math-view-dag-multiple-relations.json")
        expected = classify_math_view_contract(value)
        self.assertEqual(expected["result"], "invalid")
        self.assertEqual(
            expected["checks"], [{"id": "combined-acyclic", "result": "fail"}]
        )
        validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_declared_unknown_law_is_undetermined(self) -> None:
        value = self._fixture("math-view-valid.json")
        value["laws_or_checks"] = [
            {
                "id": "unknown-law",
                "name": "Unknown law",
                "description": "The classifier does not implement this law.",
                "check": "well-founded",
            }
        ]
        expected = classify_math_view_contract(value)
        self.assertEqual(expected["result"], "undetermined")
        value["classification"] = expected
        validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_classification_checks_must_match_deterministic_checks(self) -> None:
        value = self._fixture("math-view-valid.json")
        value["classification"]["checks"] = []
        with self.assertRaisesRegex(
            MathematicalViewValidationError, "classification checks"
        ):
            validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_invalid_dag_fixture_is_deterministically_invalid(self) -> None:
        value = self._fixture("math-view-invalid.json")
        self.assertEqual(classify_math_view_contract(value)["result"], "invalid")
        with self.assertRaisesRegex(
            MathematicalViewValidationError, "classification result"
        ):
            invalid_claim = copy.deepcopy(value)
            invalid_claim["classification"]["result"] = "valid"
            validate_math_view_contract(invalid_claim, evidence_ids={"design-doc"})

    def test_unknown_evidence_is_rejected(self) -> None:
        value = self._fixture("math-view-valid.json")
        value["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(
            MathematicalViewValidationError, "unknown evidence"
        ):
            validate_math_view_contract(value, evidence_ids={"design-doc"})

    def test_legacy_mathematical_view_without_contract_remains_valid(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "git.json").read_text())
        validate_card(card)

    def test_card_contract_is_evidence_bounded(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "git.json").read_text())
        view = self._fixture("math-view-valid.json")
        card["mathematical_views"].append(
            {
                "model": "Release partial order",
                "question": view["question"],
                "assumptions": view["assumptions"],
                "claim_type": "inference",
                "evidence_ids": ["git-data-model"],
                "contract": view | {"evidence_ids": ["git-data-model"]},
            }
        )
        validate_card(card)
        card["mathematical_views"][-1]["contract"]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(CardValidationError, "mathematical view contract"):
            validate_card(card)

    def test_contract_scope_context_is_optional_but_evidence_bounded(self) -> None:
        value = self._fixture("math-view-valid.json")
        value["scope_context"] = {
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
        model = MathematicalViewContract.from_dict(value, evidence_ids={"design-doc"})
        self.assertEqual(model.to_dict()["scope_context"], value["scope_context"])
        value["scope_context"]["workload"]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(
            MathematicalViewValidationError, "unknown evidence"
        ):
            MathematicalViewContract.from_dict(value, evidence_ids={"design-doc"})

    @staticmethod
    def _fixture(name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))

    @staticmethod
    def _validation_record() -> dict:
        return {
            "id": "release-order-observed",
            "view_id": "release-order",
            "kind": "observed-result",
            "basis": "experiment",
            "claim_type": "inference",
            "claim_status": "under-review",
            "system": "fixture-system",
            "version": "2.x",
            "scope": {
                "systems": ["fixture-system"],
                "versions": ["2.x"],
                "deployment_origins": ["configured-origin"],
                "conditions": ["documented release pipeline"],
                "exclusions": ["emergency hotfix procedure"],
            },
            "evidence_ids": ["run-a"],
            "provenance": {
                "run_id": "run-a",
                "source_revision": "commit-a",
                "protocol_digest": "sha256:protocol",
                "recorded_at": "2026-10-26T00:00:00Z",
                "runner": "local-runner-1",
                "toolchain": {"python": "3.12"},
            },
            "result": {
                "status": "observed",
                "summary": "The release stages occurred in the declared order.",
            },
            "limitations": [
                "One fixture workload",
                "This result is not a theorem or proof of implementation behavior",
            ],
        }


if __name__ == "__main__":
    unittest.main()

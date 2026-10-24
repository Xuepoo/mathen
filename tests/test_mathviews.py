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
            "checks": [],
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
            "checks": [],
        }
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

    @staticmethod
    def _fixture(name: str) -> dict:
        return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()

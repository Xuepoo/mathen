import copy
import json
import unittest
from pathlib import Path

from mathen.cards import CardValidationError, validate_card
from mathen.scope import ScopeContextValidationError, validate_scope_context

ROOT = Path(__file__).parents[1]


def context(status: str = "unspecified") -> dict:
    dimension = {"status": status, "values": [], "evidence_ids": []}
    if status == "specified":
        dimension = {
            "status": status,
            "values": ["controlled benchmark"],
            "evidence_ids": ["spec"],
            "claim_type": "fact",
            "claim_status": "accepted",
        }
    return {
        "validity_scope": {
            "status": status,
            "systems": ["fixture"] if status == "specified" else [],
            "versions": ["1.0"] if status == "specified" else [],
            "deployment_origins": [],
            "conditions": [],
            "exclusions": [],
            "evidence_ids": ["spec"] if status == "specified" else [],
            **(
                {"claim_type": "fact", "claim_status": "accepted"}
                if status == "specified"
                else {}
            ),
        },
        "workload": copy.deepcopy(dimension),
        "runtime_conditions": copy.deepcopy(dimension),
        "scale": copy.deepcopy(dimension),
        "failure_conditions": copy.deepcopy(dimension),
    }


class ScopeContextTests(unittest.TestCase):
    def test_unspecified_is_explicit_and_has_no_evidence_claim(self) -> None:
        value = context()
        validate_scope_context(value, evidence_ids={"spec"})

        value["workload"]["evidence_ids"] = ["spec"]
        with self.assertRaisesRegex(ScopeContextValidationError, "unspecified"):
            validate_scope_context(value, evidence_ids={"spec"})

    def test_specified_dimensions_require_local_evidence_and_claim_fields(self) -> None:
        validate_scope_context(context("specified"), evidence_ids={"spec"})
        value = context("specified")
        value["scale"]["evidence_ids"] = ["outside"]
        with self.assertRaisesRegex(ScopeContextValidationError, "unknown evidence"):
            validate_scope_context(value, evidence_ids={"spec"})

    def test_non_specified_dimension_cannot_smuggle_values(self) -> None:
        value = context()
        value["failure_conditions"]["status"] = "unknown"
        value["failure_conditions"]["values"] = ["timeout"]
        value["failure_conditions"]["evidence_ids"] = ["spec"]
        value["failure_conditions"]["claim_type"] = "fact"
        value["failure_conditions"]["claim_status"] = "accepted"
        with self.assertRaisesRegex(
            ScopeContextValidationError, "must not contain values"
        ):
            validate_scope_context(value, evidence_ids={"spec"})

    def test_not_applicable_requires_an_explanation(self) -> None:
        value = context()
        dimension = value["scale"]
        dimension.update(
            {
                "status": "not-applicable",
                "evidence_ids": ["spec"],
                "claim_type": "fact",
                "claim_status": "accepted",
            }
        )
        with self.assertRaisesRegex(ScopeContextValidationError, "needs notes"):
            validate_scope_context(value, evidence_ids={"spec"})
        dimension["notes"] = "No scale claim applies to this descriptive record."
        validate_scope_context(value, evidence_ids={"spec"})

    def test_card_scope_context_is_optional_but_evidence_local(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "duckdb.json").read_text())
        validate_card(card)
        card["features"][0]["scope_context"] = context()
        validate_card(card)
        card["features"][0]["scope_context"]["workload"]["evidence_ids"] = [
            "duckdb-why"
        ]
        with self.assertRaisesRegex(CardValidationError, "unspecified"):
            validate_card(card)


if __name__ == "__main__":
    unittest.main()

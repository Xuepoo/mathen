import copy
import io
import json
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mathen.cli import validate_microstructures_command
from mathen.microstructures import (
    MICROSTRUCTURE_SCHEMA_VERSION,
    Microstructure,
    MicrostructureValidationError,
    load_microstructure,
    validate_microstructure,
)


class MicrostructureTests(unittest.TestCase):
    def test_json_schema_is_versioned_and_declares_all_contract_dimensions(
        self,
    ) -> None:
        schema = json.loads(
            (
                Path(__file__).parents[1]
                / "schemas"
                / "architecture-microstructure.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            schema["$id"],
            "https://mathen.dev/schemas/architecture-microstructure.schema.json",
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            set(schema["properties"]),
            {
                "schema_version",
                "id",
                "name",
                "summary",
                "scale",
                "role",
                "state",
                "events",
                "operations",
                "inputs",
                "outputs",
                "preconditions",
                "postconditions",
                "invariants",
                "boundaries",
                "resource_effects",
                "failure_modes",
                "validity_scope",
                "claim_type",
                "claim_status",
                "evidence_ids",
                "evidence",
            },
        )

    def test_scale_aware_contract_and_model_round_trip(self) -> None:
        value = self._fixture()
        validate_microstructure(value)

        model = Microstructure.from_dict(value)
        self.assertEqual(model.schema_version, MICROSTRUCTURE_SCHEMA_VERSION)
        self.assertEqual(model.scale["level"], "mechanism")
        self.assertEqual(model.to_dict(), value)

    def test_json_schema_accepts_non_empty_documented_shapes(self) -> None:
        validator = shutil.which("check-jsonschema")
        if validator is None:
            self.skipTest("check-jsonschema is not installed")

        result = subprocess.run(
            [
                validator,
                "--schemafile",
                str(
                    Path(__file__).parents[1]
                    / "schemas"
                    / "architecture-microstructure.schema.json"
                ),
                "-",
            ],
            cwd=Path(__file__).parents[1],
            input=json.dumps(self._fixture()),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_json_schema_rejects_unknown_element_fields(self) -> None:
        validator = shutil.which("check-jsonschema")
        if validator is None:
            self.skipTest("check-jsonschema is not installed")

        value = self._fixture()
        value["events"][0]["undocumented"] = "must be rejected"
        result = subprocess.run(
            [
                validator,
                "--schemafile",
                str(
                    Path(__file__).parents[1]
                    / "schemas"
                    / "architecture-microstructure.schema.json"
                ),
                "-",
            ],
            cwd=Path(__file__).parents[1],
            input=json.dumps(value),
            capture_output=True,
            text=True,
            check=False,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_unknown_evidence_is_rejected_for_every_claim(self) -> None:
        value = self._fixture()
        value["invariants"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(MicrostructureValidationError, "unknown evidence"):
            validate_microstructure(value)

    def test_scale_and_operation_references_are_checked(self) -> None:
        value = self._fixture()
        value["scale"]["level"] = "component"
        with self.assertRaisesRegex(
            MicrostructureValidationError, "invalid scale.level"
        ):
            validate_microstructure(value)

        value = self._fixture()
        value["operations"][0]["input_ids"] = ["unknown-input"]
        with self.assertRaisesRegex(MicrostructureValidationError, "unknown inputs"):
            validate_microstructure(value)

    def test_deployment_origins_are_data_not_hardcoded_hosts(self) -> None:
        value = self._fixture()
        value["validity_scope"]["deployment_origins"] = [
            "local-process",
            "configured-worker-origin",
        ]
        validate_microstructure(value)

    def test_load_microstructure_reports_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaisesRegex(MicrostructureValidationError, "invalid JSON"):
                load_microstructure(path)

    def test_empty_or_absent_directory_is_a_successful_noop(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            empty_path = Path(directory) / "microstructures"
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(validate_microstructures_command(empty_path), 0)
            self.assertIn("nothing to validate", output.getvalue())

            empty_path.mkdir()
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(validate_microstructures_command(empty_path), 0)
            self.assertIn("nothing to validate", output.getvalue())

    @staticmethod
    def _fixture() -> dict:
        evidence = {
            "id": "design-doc",
            "kind": "official-doc",
            "title": "Microstructure design contract",
            "uri": "https://example.test/design",
        }

        def claim(description: str, item_id: str) -> dict:
            return {
                "id": item_id,
                "name": item_id.replace("-", " ").title(),
                "description": description,
                "claim_type": "inference",
                "claim_status": "under-review",
                "evidence_ids": ["design-doc"],
            }

        value = {
            "schema_version": "1.0",
            "id": "bounded-transition",
            "name": "Bounded transition",
            "summary": (
                "A mechanism that transforms an input under explicit conditions."
            ),
            "scale": {
                "level": "mechanism",
                "unit": "transition mechanism",
                "description": "The unit owns one state transition boundary.",
                "claim_type": "inference",
                "claim_status": "under-review",
                "evidence_ids": ["design-doc"],
            },
            "role": {
                "description": "Transforms accepted input into a bounded output.",
                "claim_type": "inference",
                "claim_status": "under-review",
                "evidence_ids": ["design-doc"],
            },
            "state": [
                {**claim("Ready to accept input.", "ready"), "initial": True},
                {**claim("Input has been transformed.", "completed"), "terminal": True},
            ],
            "events": [
                {
                    **claim("An accepted input arrives.", "input-accepted"),
                    "source_state": "ready",
                    "target_state": "completed",
                }
            ],
            "operations": [
                {
                    **claim("Transform one input.", "transform"),
                    "input_ids": ["payload"],
                    "output_ids": ["result"],
                    "precondition_ids": ["valid-payload"],
                    "postcondition_ids": ["result-bounded"],
                }
            ],
            "inputs": [
                {
                    **claim("The payload to transform.", "payload"),
                    "type": "record",
                    "source": "caller",
                }
            ],
            "outputs": [
                {
                    **claim("The transformed result.", "result"),
                    "type": "record",
                    "destination": "caller",
                }
            ],
            "preconditions": [
                claim("Payload meets the input contract.", "valid-payload")
            ],
            "postconditions": [
                claim("Result stays within the stated boundary.", "result-bounded")
            ],
            "invariants": [
                claim(
                    "The mechanism does not mutate caller-owned input.",
                    "immutable-input",
                )
            ],
            "boundaries": [
                {
                    **claim(
                        "Caller and mechanism are separate ownership boundaries.",
                        "ownership",
                    ),
                    "kind": "ownership",
                    "inside": "mechanism",
                    "outside": "caller",
                }
            ],
            "resource_effects": [
                {
                    **claim("Transformation consumes bounded memory.", "memory"),
                    "resource": "memory",
                    "effect": "temporary allocation proportional to payload",
                }
            ],
            "failure_modes": [
                {
                    **claim("Malformed input is rejected.", "malformed-input"),
                    "trigger": "payload violates input contract",
                    "effect": "no output is emitted",
                    "recovery": "caller supplies a valid payload",
                }
            ],
            "validity_scope": {
                "systems": ["fixture-system"],
                "versions": ["2.x"],
                "deployment_origins": ["configured-origin"],
                "conditions": ["single-owner invocation"],
                "exclusions": ["distributed retry semantics"],
                "claim_type": "inference",
                "claim_status": "under-review",
                "evidence_ids": ["design-doc"],
            },
            "claim_type": "inference",
            "claim_status": "under-review",
            "evidence_ids": ["design-doc"],
            "evidence": [evidence],
        }
        return copy.deepcopy(value)


if __name__ == "__main__":
    unittest.main()

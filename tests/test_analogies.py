import copy
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from mathen.analogies import (
    ANALOGY_SCHEMA_VERSION,
    AnalogyMapping,
    AnalogyValidationError,
    validate_analogy,
)
from mathen.cli import validate_analogies_command


class AnalogyTests(unittest.TestCase):
    def test_json_schema_is_versioned_and_declares_mapping_dimensions(self) -> None:
        schema = json.loads(
            (
                Path(__file__).parents[1]
                / "schemas"
                / "cross-domain-analogy.schema.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(
            schema["$id"],
            "https://mathen.dev/schemas/cross-domain-analogy.schema.json",
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertTrue(
            {
                "source_domain",
                "target_domain",
                "source_concepts",
                "target_concepts",
                "mapping_type",
                "scale",
                "shared_properties",
                "preserved_properties",
                "non_preserved_properties",
                "scope",
                "counterexamples",
                "non_equivalence",
                "evidence",
            }.issubset(schema["required"])
        )

    def test_representative_cross_domain_fixture_is_valid_and_round_trips(self) -> None:
        path = (
            Path(__file__).parents[1] / "data" / "analogies" / "chemistry-biology.json"
        )
        value = json.loads(path.read_text(encoding="utf-8"))
        validate_analogy(value)
        mapping = AnalogyMapping.from_dict(value)
        self.assertEqual(mapping.schema_version, ANALOGY_SCHEMA_VERSION)
        self.assertEqual(mapping.to_dict(), value)

    def test_mapping_requires_explicit_non_equivalence(self) -> None:
        value = self._fixture()
        del value["non_equivalence"]
        with self.assertRaisesRegex(AnalogyValidationError, "missing fields"):
            validate_analogy(value)

    def test_unknown_concept_and_evidence_are_rejected(self) -> None:
        value = self._fixture()
        value["correspondences"][0]["target_concept_ids"] = ["unknown"]
        with self.assertRaisesRegex(AnalogyValidationError, "unknown concepts"):
            validate_analogy(value)

        value = self._fixture()
        value["shared_properties"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(AnalogyValidationError, "unknown evidence"):
            validate_analogy(value)

    def test_deployment_origins_are_configurable_data(self) -> None:
        value = self._fixture()
        value["scope"]["deployment_origins"] = ["configured-lab", "local-analysis"]
        validate_analogy(value)

    def test_analogy_type_is_required_at_document_level(self) -> None:
        value = self._fixture()
        value["claim_type"] = "inference"
        with self.assertRaisesRegex(AnalogyValidationError, "must be analogy"):
            validate_analogy(value)

    def test_cli_validates_fixture_and_empty_directory(self) -> None:
        fixture = Path(__file__).parents[1] / "data" / "analogies"
        output = io.StringIO()
        with redirect_stdout(output):
            self.assertEqual(validate_analogies_command(fixture), 0)
        self.assertIn("chemistry-biology.json", output.getvalue())

        with tempfile.TemporaryDirectory() as directory:
            output = io.StringIO()
            with redirect_stdout(output):
                self.assertEqual(validate_analogies_command(Path(directory)), 0)
            self.assertIn("nothing to validate", output.getvalue())

    def test_discovery_includes_nested_collection_members(self) -> None:
        from mathen.analogies import discover_analogies

        with tempfile.TemporaryDirectory() as directory:
            nested = Path(directory) / "batch" / "nested.json"
            nested.parent.mkdir()
            nested.write_text("{}", encoding="utf-8")
            self.assertEqual(discover_analogies(Path(directory)), [nested])

    @staticmethod
    def _fixture() -> dict:
        evidence = {
            "id": "source-paper",
            "kind": "paper",
            "title": "Bounded structural comparison",
            "uri": "https://example.test/source-paper",
        }

        def claims(item_id: str, claim_type: str = "analogy") -> dict:
            return {
                "claim_type": claim_type,
                "claim_status": "proposed",
                "evidence_ids": ["source-paper"],
            }

        def concept(item_id: str) -> dict:
            return {
                "id": item_id,
                "name": item_id,
                "description": "A bounded domain concept.",
                **claims(item_id, "fact"),
            }

        def prop(item_id: str) -> dict:
            return {
                "id": item_id,
                "name": item_id,
                "description": "A property in the comparison.",
                **claims(item_id),
            }

        value = {
            "schema_version": "1.0",
            "id": "source-target-motif",
            "name": "Source-target motif",
            "summary": "A bounded structural comparison.",
            "source_domain": {
                "name": "chemistry",
                "description": "Source domain.",
                **claims("source", "fact"),
            },
            "target_domain": {
                "name": "biology",
                "description": "Target domain.",
                **claims("target", "fact"),
            },
            "source_concepts": [concept("source-node")],
            "target_concepts": [concept("target-node")],
            "correspondences": [
                {
                    "id": "node-match",
                    "source_concept_ids": ["source-node"],
                    "target_concept_ids": ["target-node"],
                    "relation": "role-level resemblance",
                    "rationale": "Both participate in a directed motif.",
                    **claims("correspondence"),
                }
            ],
            "mapping_type": "structural",
            "scale": {
                "source": "motif",
                "target": "motif",
                "description": "Graph motif.",
                **claims("scale"),
            },
            "shared_properties": [prop("directed")],
            "preserved_properties": [prop("adjacency")],
            "non_preserved_properties": [prop("kinetics")],
            "scope": {
                "source_versions": ["source-v1"],
                "target_versions": ["target-v1"],
                "deployment_origins": ["configured-origin"],
                "conditions": ["motif comparison"],
                "exclusions": ["parameter transfer"],
                **claims("scope"),
            },
            "counterexamples": [
                {
                    "id": "different-laws",
                    "description": "Matching motifs can have different laws.",
                    "implication": "No predictive equivalence.",
                    **claims("counterexample"),
                }
            ],
            "non_equivalence": {
                "statement": "Concepts are not equivalent.",
                "reasons": ["Different substrates"],
                "substitutability": "not-substitutable",
                **claims("non-equivalence"),
            },
            **claims("mapping"),
            "evidence_ids": ["source-paper"],
            "evidence": [evidence],
        }
        return copy.deepcopy(value)


if __name__ == "__main__":
    unittest.main()

import unittest
from types import SimpleNamespace

from mathen.modeling import (
    build_modeling_bundle,
    protocol_run_record,
    render_modeling_prompt,
)


class ModelingContractTests(unittest.TestCase):
    def test_modeling_task_requires_evidence_bounded_coverage_review(self) -> None:
        spec = SimpleNamespace(
            id="fixture",
            name="Fixture",
            category="test",
            repository="https://example.com/fixture.git",
            documentation="https://example.com/docs",
            ref="main",
        )
        analysis = {
            "system_id": "fixture",
            "commit": "a" * 40,
            "commit_url": "https://example.com/commit/" + "a" * 40,
            "provenance": "fixture",
        }
        draft = {"id": "fixture", "features": [], "evidence": []}

        task = build_modeling_bundle(spec, analysis, draft)["modeling_task"]
        dimensions = {item["dimension"] for item in task["questions"]}
        self.assertTrue(
            {
                "domains and components",
                "state and lifecycle",
                "interfaces and dependencies",
                "consistency and ordering",
                "security and boundaries",
                "failure and recovery",
                "resources and scale",
                "evolution and compatibility",
                "transferable architecture",
            }.issubset(dimensions)
        )
        self.assertEqual(
            task["coverage_protocol"]["for_each_dimension"],
            [
                "cite the supporting evidence IDs",
                "record a concise supported claim",
                "record what is unknown or out of scope when evidence is insufficient",
            ],
        )
        self.assertTrue(any("quota" in rule for rule in task["evidence_rules"]))
        self.assertEqual(task["mathematical_view_contract"]["version"], "1.0")
        self.assertIn("partial_order", task["mathematical_view_contract"]["families"])
        self.assertIn(
            "classification", task["mathematical_view_contract"]["required_dimensions"]
        )
        self.assertEqual(
            task["claim_protocol"]["required_fields"],
            ["claim_type", "claim_status", "evidence_ids"],
        )
        self.assertIn(
            "cross-domain resemblance", task["claim_protocol"]["analogy_rule"]
        )
        self.assertEqual(
            task["evaluation"]["dimensions"],
            ["breadth", "citation_quality", "error_rate", "reviewer_usefulness"],
        )
        self.assertTrue(
            task["output"]["canonical_boundary"].startswith("Automated output")
        )
        self.assertIn(
            "unknown or out of scope",
            render_modeling_prompt(build_modeling_bundle(spec, analysis, draft)),
        )
        analogy = task["cross_domain_analogy_mapping"]
        self.assertEqual(analogy["schema_version"], "1.0")
        self.assertIn("non_equivalence", analogy["required_dimensions"])
        self.assertIn("historical influence", analogy["boundary"])

    def test_protocol_run_record_is_secret_safe_and_reproducible(self) -> None:
        spec = SimpleNamespace(
            id="fixture",
            name="Fixture",
            category="test",
            repository="https://example.com/fixture.git",
            documentation="https://example.com/docs",
            ref="main",
        )
        bundle = build_modeling_bundle(
            spec,
            {
                "system_id": "fixture",
                "commit": "a" * 40,
                "commit_url": "https://example.com/commit/" + "a" * 40,
                "provenance": "fixture",
            },
            {"id": "fixture", "features": [], "evidence": []},
        )
        prompt = render_modeling_prompt(bundle)
        record = protocol_run_record(
            bundle,
            prompt,
            provider="local-test",
            model="fixture-model",
        )
        self.assertEqual(record["protocol_version"], "mth-0112-v1")
        self.assertEqual(record["provider"], "local-test")
        self.assertEqual(record["model"], "fixture-model")
        self.assertTrue(record["secret_safe"])
        self.assertNotIn("api_key", repr(record))
        self.assertNotIn(prompt, repr(record))
        self.assertEqual(
            record,
            protocol_run_record(
                bundle, prompt, provider="local-test", model="fixture-model"
            ),
        )

    def test_contract_does_not_require_a_fixed_feature_count(self) -> None:
        spec = SimpleNamespace(
            id="fixture",
            name="Fixture",
            category="test",
            repository="https://example.com/fixture.git",
            documentation="https://example.com/docs",
            ref="main",
        )
        analysis = {
            "system_id": "fixture",
            "commit": "b" * 40,
            "commit_url": "https://example.com/commit/" + "b" * 40,
            "provenance": "fixture",
        }
        for feature_count in (0, 1, 7):
            with self.subTest(feature_count=feature_count):
                draft = {
                    "id": "fixture",
                    "features": [{} for _ in range(feature_count)],
                    "evidence": [],
                }
                bundle = build_modeling_bundle(spec, analysis, draft)
                self.assertEqual(
                    len(bundle["existing_structural_draft"]["features"]), feature_count
                )


if __name__ == "__main__":
    unittest.main()

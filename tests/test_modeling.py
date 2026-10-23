import unittest
from types import SimpleNamespace

from mathen.modeling import build_modeling_bundle, render_modeling_prompt


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
        self.assertIn(
            "unknown or out of scope",
            render_modeling_prompt(build_modeling_bundle(spec, analysis, draft)),
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

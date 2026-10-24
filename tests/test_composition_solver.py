import json
import unittest
from pathlib import Path

from mathen.composition_solver import (
    FeatureRecord,
    ReviewedFeatureSpec,
    adapt_reviewed_cards,
    adapt_typed_composition,
    solve_compositions,
    solve_reviewed_compositions,
    solve_typed_compositions,
)
from mathen.typed_composition import (
    TypedCompositionValidationError,
    validate_typed_composition,
)

ROOT = Path(__file__).parents[1]


class CompositionSolverTests(unittest.TestCase):
    def test_typed_solver_reports_explicit_semantics_without_proof(self) -> None:
        candidates = solve_typed_compositions(
            [
                {
                    "id": "consumer",
                    "provides": ["result"],
                    "requires": ["input"],
                    "consumes": ["input"],
                    "adapters": ["json-boundary"],
                    "boundaries": ["process-boundary"],
                    "preserves": ["ordering"],
                    "weakens": ["latency"],
                    "preconditions": ["input-valid"],
                    "postconditions": ["result-emitted"],
                    "resource_effects": ["buffer-memory"],
                    "failure_modes": ["timeout"],
                    "evidence_ids": ["consumer-doc"],
                },
                {
                    "id": "provider",
                    "provides": ["input"],
                    "evidence_ids": ["provider-doc"],
                },
            ],
            ["result"],
            max_components=2,
        )
        candidate = next(
            item for item in candidates if item.feature_ids == ("consumer",)
        )
        self.assertEqual(candidate.dependency_ids, ("provider",))
        self.assertEqual(candidate.consumed_capabilities, ("input",))
        self.assertEqual(candidate.adapters, ("json-boundary",))
        self.assertIn("preserves:ordering", candidate.property_effects)
        self.assertIn("weakens:latency", candidate.property_effects)
        self.assertIn("typed semantics remain a candidate", candidate.explanation[-1])
        self.assertFalse(candidate.proven)

    def test_typed_adapter_does_not_use_discovery_as_compatibility(self) -> None:
        contract = _typed_contract()
        specs = adapt_typed_composition(contract, evidence_ids={"source"})
        self.assertEqual(tuple(item.id for item in specs), ("source", "target"))
        self.assertEqual(
            specs[0].composition_semantics.to_dict(),
            contract,
        )
        candidates = solve_typed_compositions(specs, ["output"], max_components=1)
        self.assertEqual(candidates[0].unresolved_requirements, ())

    def test_typed_adapter_preserves_declared_semantics_and_conflicts(self) -> None:
        contract = _typed_contract()
        contract["components"][0]["conflicts"] = ["unsafe-target"]
        claim = {
            "claim_type": "hypothesis",
            "claim_status": "proposed",
            "evidence_ids": ["source"],
        }
        contract["adapters"] = [
            {
                "id": "source-target-adapter",
                "source": "source",
                "target": "target",
                "description": "Converts the source output for the target.",
                **claim,
            }
        ]
        contract["boundaries"] = [
            {
                "id": "source-target-boundary",
                "inside": "source",
                "outside": "target",
                "description": "Marks the process boundary.",
                **claim,
            }
        ]
        for field in (
            "preconditions",
            "postconditions",
            "resource_effects",
            "failure_modes",
            "examples",
            "counterexamples",
            "uncertainties",
            "disagreements",
        ):
            contract[field] = [
                {"id": field, "description": f"Declared {field}.", **claim}
            ]
        contract["property_effects"] = [
            {"id": "ordering", "property": "ordering", "relation": "preserves", **claim}
        ]
        contract["conflicts"] = [
            {
                "id": "contract-conflict",
                "description": "The boundary may reject unsafe targets.",
                **{
                    "claim_type": "hypothesis",
                    "claim_status": "proposed",
                    "evidence_ids": ["source"],
                },
            }
        ]
        specs = adapt_typed_composition(contract, evidence_ids={"source"})
        source = next(item for item in specs if item.id == "source")
        self.assertEqual(source.conflicts, frozenset({"unsafe-target"}))
        self.assertEqual(source.composition_semantics.to_dict(), contract)

    def test_typed_validator_rejects_undeclared_fields(self) -> None:
        contract = _typed_contract()
        contract["examples"] = [
            {
                "id": "example",
                "description": "A declared example.",
                "claim_type": "hypothesis",
                "claim_status": "proposed",
                "evidence_ids": ["source"],
                "unexpected": "must be rejected",
            }
        ]
        with self.assertRaisesRegex(TypedCompositionValidationError, "undeclared"):
            validate_typed_composition(contract, evidence_ids={"source"})

    def test_typed_contract_requires_proven_false_and_local_evidence(self) -> None:
        contract = _typed_contract()
        validate_typed_composition(contract, evidence_ids={"source"})
        contract["proven"] = True
        with self.assertRaisesRegex(TypedCompositionValidationError, "proven"):
            validate_typed_composition(contract, evidence_ids={"source"})
        contract = _typed_contract()
        contract["components"][0]["evidence_ids"] = ["unknown"]
        with self.assertRaisesRegex(
            TypedCompositionValidationError, "unknown evidence"
        ):
            validate_typed_composition(contract, evidence_ids={"source"})

    def test_dependency_closure_is_explained(self) -> None:
        candidates = solve_compositions(
            [
                FeatureRecord(
                    "app", provides=frozenset({"app"}), requires=frozenset({"db"})
                ),
                FeatureRecord(
                    "database", provides=frozenset({"db"}), evidence_ids=("db-doc",)
                ),
            ],
            {"app"},
            max_components=2,
        )

        candidate = next(item for item in candidates if item.feature_ids == ("app",))
        self.assertEqual(candidate.dependency_ids, ("database",))
        self.assertEqual(candidate.unresolved_requirements, ())
        self.assertIn("dependency closure added: database", candidate.explanation)
        self.assertFalse(candidate.proven)

    def test_provider_backtracking_chooses_usable_provider(self) -> None:
        candidates = solve_compositions(
            [
                FeatureRecord(
                    "app", provides=frozenset({"app"}), requires=frozenset({"runtime"})
                ),
                FeatureRecord(
                    "a-bad-provider",
                    provides=frozenset({"runtime"}),
                    requires=frozenset({"missing"}),
                ),
                FeatureRecord("z-good-provider", provides=frozenset({"runtime"})),
            ],
            {"app"},
            max_components=2,
        )

        candidate = next(item for item in candidates if item.feature_ids == ("app",))
        self.assertEqual(candidate.dependency_ids, ("z-good-provider",))
        self.assertEqual(candidate.unresolved_requirements, ())

    def test_conflicts_are_reported(self) -> None:
        candidates = solve_compositions(
            [
                FeatureRecord(
                    "left", provides=frozenset({"left"}), conflicts=frozenset({"right"})
                ),
                FeatureRecord("right", provides=frozenset({"right"})),
            ],
            {"left", "right"},
            max_components=2,
        )

        candidate = next(
            item for item in candidates if item.feature_ids == ("left", "right")
        )
        self.assertEqual(candidate.conflicts, ("left:right",))
        self.assertIn("detected conflicts: left:right", candidate.explanation)

    def test_feature_ids_are_not_conflict_tokens(self) -> None:
        candidates = solve_compositions(
            [
                FeatureRecord(
                    "left", provides=frozenset({"left"}), conflicts=frozenset({"right"})
                ),
                FeatureRecord("right", provides=frozenset({"other-capability"})),
            ],
            {"left", "other-capability"},
            max_components=2,
        )

        candidate = next(
            item for item in candidates if item.feature_ids == ("left", "right")
        )
        self.assertEqual(candidate.conflicts, ())

    def test_results_are_bounded(self) -> None:
        features = [
            FeatureRecord(f"feature-{index}", provides=frozenset({str(index)}))
            for index in range(4)
        ]
        candidates = solve_compositions(
            features, set(), max_components=2, max_results=3
        )

        self.assertEqual(len(candidates), 3)
        self.assertTrue(
            all(len(candidate.feature_ids) <= 2 for candidate in candidates)
        )

    def test_invalid_bounds_are_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "max_components"):
            solve_compositions([], set(), max_components=0)
        with self.assertRaisesRegex(ValueError, "max_depth"):
            solve_compositions([], set(), max_depth=0)
        with self.assertRaisesRegex(ValueError, "max_results"):
            solve_compositions([], set(), max_results=0)

    def test_ordering_is_deterministic_and_prefers_coverage(self) -> None:
        features = [
            FeatureRecord("zeta", provides=frozenset({"x"}), evidence_ids=("e",)),
            FeatureRecord("alpha", provides=frozenset({"x"})),
        ]
        first = solve_compositions(features, {"x"}, max_components=1)
        second = solve_compositions(reversed(features), {"x"}, max_components=1)

        self.assertEqual(first, second)
        self.assertEqual(first[0].feature_ids, ("zeta",))

    def test_missing_capabilities_are_unresolved(self) -> None:
        candidates = solve_compositions(
            [FeatureRecord("app", provides=frozenset({"app"}))],
            {"app", "missing"},
        )

        candidate = candidates[0]
        self.assertEqual(candidate.unresolved_requirements, ("missing",))
        self.assertEqual(candidate.coverage_score, 0.5)

    def test_reviewed_card_adapter_requires_explicit_capability_semantics(self) -> None:
        card = {
            "id": "reviewed-system",
            "features": [
                {"id": "feature", "evidence_ids": ["source"]},
            ],
        }

        with self.assertRaisesRegex(ValueError, "unknown reviewed features"):
            adapt_reviewed_cards(
                [card],
                [
                    ReviewedFeatureSpec(
                        "other-system", "feature", provides=frozenset({"capability"})
                    )
                ],
            )

        records = adapt_reviewed_cards(
            [card],
            [
                ReviewedFeatureSpec(
                    "reviewed-system", "feature", provides=frozenset({"capability"})
                )
            ],
        )
        self.assertEqual(records[0].id, "reviewed-system:feature")
        self.assertEqual(records[0].evidence_ids, ("reviewed-system:source",))

    def test_reviewed_cards_report_capabilities_evidence_and_unresolved(self) -> None:
        cards = [
            {
                "id": "app-system",
                "features": [{"id": "app", "evidence_ids": ["app-source"]}],
            },
            {
                "id": "storage-system",
                "features": [{"id": "storage", "evidence_ids": ["storage-source"]}],
            },
        ]
        candidates = solve_reviewed_compositions(
            cards,
            [
                {
                    "system_id": "app-system",
                    "feature_id": "app",
                    "provides": ["application"],
                    "requires": ["storage"],
                },
                {
                    "system_id": "storage-system",
                    "feature_id": "storage",
                    "provides": ["storage"],
                },
            ],
            ["application", "missing"],
            max_components=2,
        )

        candidate = next(
            item for item in candidates if item.feature_ids == ("app-system:app",)
        )
        self.assertEqual(candidate.dependency_ids, ("storage-system:storage",))
        self.assertEqual(candidate.selected_ids, ("app-system:app",))
        self.assertEqual(candidate.provided_capabilities, ("application", "storage"))
        self.assertEqual(
            candidate.required_capabilities, ("application", "missing", "storage")
        )
        self.assertEqual(candidate.unresolved_requirements, ("missing",))
        self.assertEqual(candidate.coverage_score, 0.5)
        self.assertEqual(candidate.evidence_score, 1.0)
        self.assertEqual(
            candidate.evidence_ids,
            ("app-system:app-source", "storage-system:storage-source"),
        )
        self.assertEqual(candidate.score, 41.0)
        self.assertFalse(candidate.proven)
        self.assertIn("candidate requires review", candidate.explanation[-1])

    def test_reviewed_card_conflicts_are_reported_without_proof(self) -> None:
        cards = [
            {
                "id": "left-system",
                "features": [{"id": "left", "evidence_ids": ["left-source"]}],
            },
            {
                "id": "right-system",
                "features": [{"id": "right", "evidence_ids": ["right-source"]}],
            },
        ]
        candidates = solve_reviewed_compositions(
            cards,
            [
                {
                    "system_id": "left-system",
                    "feature_id": "left",
                    "provides": ["left"],
                    "conflicts": ["right"],
                },
                {
                    "system_id": "right-system",
                    "feature_id": "right",
                    "provides": ["right"],
                },
            ],
            ["left", "right"],
            max_components=2,
        )
        candidate = next(
            item
            for item in candidates
            if item.feature_ids == ("left-system:left", "right-system:right")
        )
        self.assertEqual(candidate.conflicts, ("left-system:left:right",))
        self.assertFalse(candidate.proven)

    def test_reviewed_card_results_are_deterministic(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "carryctx.json").read_text())
        specs = [
            ReviewedFeatureSpec(
                "carryctx",
                "local-sqlite-project-state",
                provides=frozenset({"durable-state"}),
            ),
            ReviewedFeatureSpec(
                "carryctx",
                "guarded-task-lifecycle",
                provides=frozenset({"guarded-workflow"}),
                requires=frozenset({"durable-state"}),
            ),
        ]
        first = solve_reviewed_compositions(
            [card], specs, ["guarded-workflow"], max_components=2
        )
        second = solve_reviewed_compositions(
            [card], list(reversed(specs)), ["guarded-workflow"], max_components=2
        )
        self.assertEqual(first, second)
        self.assertEqual(first[0].feature_ids, ("carryctx:guarded-task-lifecycle",))
        self.assertEqual(
            first[0].dependency_ids, ("carryctx:local-sqlite-project-state",)
        )


def _typed_contract() -> dict:
    claim = {
        "claim_type": "hypothesis",
        "claim_status": "proposed",
        "evidence_ids": ["source"],
    }
    return {
        "schema_version": "1.0",
        "components": [
            {"id": "source", "role": "producer", "provides": ["output"], **claim},
            {"id": "target", "role": "consumer", "requires": ["output"], **claim},
        ],
        "adapters": [],
        "boundaries": [],
        "conflicts": [],
        "property_effects": [],
        "preconditions": [],
        "postconditions": [],
        "resource_effects": [],
        "failure_modes": [],
        "examples": [],
        "counterexamples": [],
        "uncertainties": [],
        "disagreements": [],
        "discovery": {
            "method": "graph-and-llm-review",
            "provenance": ["graph:source->target", "llm:review-1"],
            "source_community": "storage",
            "target_community": "execution",
            "path": ["storage", "boundary", "execution"],
            "candidate_status": "candidate",
        },
        "validity_scope": {
            "systems": ["source", "target"],
            "versions": ["unversioned"],
            "deployment_origins": ["local"],
            "conditions": ["declared interface"],
            "exclusions": ["production compatibility"],
        },
        **claim,
        "proven": False,
    }


if __name__ == "__main__":
    unittest.main()

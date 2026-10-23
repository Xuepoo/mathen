import json
import unittest
from pathlib import Path

from mathen.composition_solver import (
    FeatureRecord,
    ReviewedFeatureSpec,
    adapt_reviewed_cards,
    solve_compositions,
    solve_reviewed_compositions,
)

ROOT = Path(__file__).parents[1]


class CompositionSolverTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()

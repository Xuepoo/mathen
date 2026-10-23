import json
import unittest
from pathlib import Path

from mathen.taxonomy import (
    CATEGORY_ALIASES,
    LEGACY_CATEGORY_VALUES,
    TaxonomyValidationError,
    category_alias,
    is_valid_feature_taxonomy,
    normalize_feature_taxonomy,
    normalize_pattern_id,
    validate_feature_taxonomy,
)

ROOT = Path(__file__).parents[1]


class TaxonomyTests(unittest.TestCase):
    def test_legacy_category_alias_is_deterministic(self) -> None:
        first = category_alias("storage-model")
        second = category_alias("storage-model")
        self.assertEqual(first, second)
        self.assertEqual(
            first,
            {
                "kind": "model",
                "domain": "storage",
                "layer": "storage",
                "pattern_id": "storage-model",
            },
        )
        self.assertEqual(CATEGORY_ALIASES["storage-model"], first)

    def test_punctuation_in_legacy_categories_is_normalized(self) -> None:
        self.assertEqual(category_alias("I/O-model")["pattern_id"], "i-o-model")

    def test_all_current_category_values_have_aliases(self) -> None:
        categories = set()
        for path in (ROOT / "data" / "systems").glob("*.json"):
            card = json.loads(path.read_text(encoding="utf-8"))
            categories.update(
                feature["category"]
                for feature in card["features"]
                if "category" in feature
            )
        self.assertTrue(categories.issubset(set(LEGACY_CATEGORY_VALUES)))
        self.assertTrue(categories.issubset(CATEGORY_ALIASES))

    def test_new_taxonomy_normalizes_aliases_and_proposed_pattern(self) -> None:
        value = normalize_feature_taxonomy(
            {
                "kind": "architecture",
                "domain": "networking",
                "layer": "api",
                "pattern_id": "Proposed Network Pattern",
            }
        )
        self.assertEqual(
            value,
            {
                "kind": "model",
                "domain": "communication",
                "layer": "interface",
                "pattern_id": "proposed-network-pattern",
            },
        )

    def test_legacy_feature_can_be_normalized_without_migration(self) -> None:
        self.assertEqual(
            normalize_feature_taxonomy({"category": "execution-model"})["pattern_id"],
            "execution-model",
        )
        validate_feature_taxonomy({"category": "execution-model"})

    def test_invalid_dimensions_are_rejected(self) -> None:
        for field in ("kind", "domain", "layer"):
            value = {
                "kind": "model",
                "domain": "data",
                "layer": "data",
            }
            value[field] = "not-a-controlled-value"
            with (
                self.subTest(field=field),
                self.assertRaisesRegex(TaxonomyValidationError, f"invalid {field}"),
            ):
                validate_feature_taxonomy(value)

    def test_pattern_id_may_be_proposed_but_must_be_a_slug(self) -> None:
        self.assertEqual(normalize_pattern_id("new_pattern_2"), "new-pattern-2")
        self.assertTrue(
            is_valid_feature_taxonomy(
                {
                    "kind": "mechanism",
                    "domain": "execution",
                    "layer": "runtime",
                    "pattern_id": "future-pattern",
                }
            )
        )
        with self.assertRaises(TaxonomyValidationError):
            normalize_pattern_id("!!!")

    def test_strict_mode_rejects_legacy_categories(self) -> None:
        with self.assertRaisesRegex(TaxonomyValidationError, "legacy category"):
            validate_feature_taxonomy(
                {"category": "storage-model"}, allow_legacy_category=False
            )

    def test_pattern_id_can_be_required_for_new_records(self) -> None:
        with self.assertRaisesRegex(TaxonomyValidationError, "pattern_id"):
            validate_feature_taxonomy(
                {"kind": "model", "domain": "data", "layer": "data"},
                require_pattern_id=True,
            )


if __name__ == "__main__":
    unittest.main()

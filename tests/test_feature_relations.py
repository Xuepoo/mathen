import copy
import unittest

from mathen.cards import CardValidationError, validate_card, validate_card_collection


def feature_relation_fixture() -> list[dict[str, object]]:
    return [
        {
            "id": "alpha",
            "name": "Alpha",
            "summary": "Source fixture.",
            "scope": ["architecture"],
            "features": [
                {
                    "id": "embedded-execution",
                    "name": "Embedded execution",
                    "category": "execution-model",
                    "claim_type": "fact",
                    "description": "Executes within the host process.",
                    "evidence_ids": ["alpha-doc"],
                }
            ],
            "mathematical_views": [],
            "trade_offs": [],
            "evidence": [
                {
                    "id": "alpha-doc",
                    "kind": "official-doc",
                    "title": "Alpha architecture",
                    "uri": "https://example.com/alpha",
                }
            ],
            "feature_relations": [
                {
                    "source_feature_id": "embedded-execution",
                    "target_system_id": "beta",
                    "target_feature_id": "embedded-execution",
                    "type": "resembles",
                    "claim_type": "analogy",
                    "claim_status": "proposed",
                    "evidence_ids": ["alpha-doc"],
                    "notes": "Bounded comparison only.",
                }
            ],
        },
        {
            "id": "beta",
            "name": "Beta",
            "summary": "Target fixture.",
            "scope": ["architecture"],
            "features": [
                {
                    "id": "embedded-execution",
                    "name": "Embedded execution",
                    "category": "execution-model",
                    "claim_type": "fact",
                    "description": "Provides an embedded execution boundary.",
                    "evidence_ids": ["beta-doc"],
                }
            ],
            "mathematical_views": [],
            "trade_offs": [],
            "evidence": [
                {
                    "id": "beta-doc",
                    "kind": "official-doc",
                    "title": "Beta architecture",
                    "uri": "https://example.com/beta",
                }
            ],
        },
    ]


class FeatureRelationValidationTests(unittest.TestCase):
    def test_local_and_collection_validation(self):
        cards = feature_relation_fixture()
        for card in cards:
            validate_card(card)
        validate_card_collection(cards)

    def test_missing_source_feature_is_rejected(self):
        card = copy.deepcopy(feature_relation_fixture()[0])
        card["feature_relations"][0]["source_feature_id"] = "missing"
        with self.assertRaises(CardValidationError):
            validate_card(card)

    def test_foreign_evidence_is_rejected(self):
        card = copy.deepcopy(feature_relation_fixture()[0])
        card["feature_relations"][0]["evidence_ids"] = ["beta-doc"]
        with self.assertRaises(CardValidationError):
            validate_card(card)

    def test_duplicate_directed_relation_is_rejected(self):
        card = copy.deepcopy(feature_relation_fixture()[0])
        card["feature_relations"].append(copy.deepcopy(card["feature_relations"][0]))
        with self.assertRaises(CardValidationError):
            validate_card(card)

    def test_missing_target_feature_is_rejected_by_collection_validation(self):
        cards = feature_relation_fixture()
        cards[0]["feature_relations"][0]["target_feature_id"] = "missing"
        validate_card(cards[0])
        validate_card(cards[1])
        with self.assertRaises(CardValidationError):
            validate_card_collection(cards)

    def test_unresolved_target_is_allowed_by_local_validation(self):
        card = feature_relation_fixture()[0]
        validate_card(card)
        with self.assertRaises(CardValidationError):
            validate_card_collection([card])

    def test_null_feature_relations_is_rejected(self):
        card = feature_relation_fixture()[0]
        card["feature_relations"] = None
        with self.assertRaises(CardValidationError):
            validate_card(card)

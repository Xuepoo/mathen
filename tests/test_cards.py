import json
import tempfile
import unittest
from pathlib import Path

from mathen.cards import (
    CardValidationError,
    discover_cards,
    load_card,
    validate_card,
)

ROOT = Path(__file__).parents[1]


class CardValidationTests(unittest.TestCase):
    def test_seed_cards_are_valid(self) -> None:
        cards = discover_cards(ROOT / "data" / "systems")
        self.assertGreaterEqual(len(cards), 4)
        for card in cards:
            load_card(card)

    def test_unknown_evidence_is_rejected(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "git.json").read_text())
        card["features"][0]["evidence_ids"] = ["missing"]
        with self.assertRaises(CardValidationError):
            validate_card(card)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(CardValidationError):
                load_card(path)

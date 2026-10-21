"""Command-line interface for the Mathen prototype."""

from __future__ import annotations

import argparse
from pathlib import Path

from .cards import CardValidationError, discover_cards, load_card

DEFAULT_CARDS = Path(__file__).parents[2] / "data" / "systems"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="mathen")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate architecture cards")
    validate.add_argument("path", nargs="?", type=Path, default=DEFAULT_CARDS)

    listing = subparsers.add_parser("list", help="list architecture cards")
    listing.add_argument("path", nargs="?", type=Path, default=DEFAULT_CARDS)

    show = subparsers.add_parser("show", help="show one architecture card")
    show.add_argument("card_id")
    show.add_argument("path", nargs="?", type=Path, default=DEFAULT_CARDS)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        if args.command == "validate":
            return validate_command(args.path)
        if args.command == "list":
            return list_command(args.path)
        if args.command == "show":
            return show_command(args.path, args.card_id)
    except CardValidationError as error:
        print(f"ERROR: {error}")
        return 1
    return 2


def validate_command(path: Path) -> int:
    cards = discover_cards(path) if path.is_dir() else [path]
    if not cards:
        print(f"No cards found in {path}")
        return 1
    for card_path in cards:
        load_card(card_path)
        print(f"valid  {card_path}")
    return 0


def list_command(path: Path) -> int:
    for card_path in discover_cards(path):
        card = load_card(card_path)
        print(f"{card['id']}\t{card['name']}")
    return 0


def show_command(path: Path, card_id: str) -> int:
    for card_path in discover_cards(path):
        card = load_card(card_path)
        if card["id"] == card_id:
            print(card["summary"])
            for feature in card["features"]:
                print(f"- {feature['name']}: {feature['description']}")
            return 0
    print(f"Card not found: {card_id}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())

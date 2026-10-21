"""Command-line interface for the Mathen prototype."""

from __future__ import annotations

import argparse
from pathlib import Path

from .cards import CardValidationError, discover_cards, load_card
from .modeling import (
    ModelingBundleError,
    build_modeling_bundles,
    write_modeling_prompts,
)
from .repositories import RepositoryAnalysisError, analyze_manifest

DEFAULT_CARDS = Path(__file__).parents[2] / "data" / "systems"
DEFAULT_MANIFEST = (
    Path(__file__).parents[2] / "data" / "repositories" / "representative.json"
)
DEFAULT_CACHE = Path(".cache") / "mathen" / "repos"
DEFAULT_DRAFTS = Path(__file__).parents[2] / "data" / "drafts"
DEFAULT_ANALYSES = Path(__file__).parents[2] / "data" / "analyses"
DEFAULT_BUNDLES = Path(__file__).parents[2] / "data" / "modeling"


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

    analyze = subparsers.add_parser(
        "analyze", help="clone repositories and generate draft architecture cards"
    )
    analyze.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    analyze.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE)
    analyze.add_argument("--output-dir", type=Path, default=DEFAULT_DRAFTS)
    analyze.add_argument("--limit", type=int)
    analyze.add_argument(
        "--priority",
        action="append",
        choices=("seed", "core", "extended"),
        help="restrict the batch to one or more catalog priorities",
    )

    prepare = subparsers.add_parser(
        "prepare-modeling", help="build evidence bundles for LLM architecture modeling"
    )
    prepare.add_argument("manifest", nargs="?", type=Path, default=DEFAULT_MANIFEST)
    prepare.add_argument("--analyses-dir", type=Path, default=DEFAULT_ANALYSES)
    prepare.add_argument("--drafts-dir", type=Path, default=DEFAULT_DRAFTS)
    prepare.add_argument("--output-dir", type=Path, default=DEFAULT_BUNDLES)
    prepare.add_argument("--system", action="append", dest="system_ids")
    prepare.add_argument(
        "--write-prompts",
        action="store_true",
        help="also render portable Markdown prompts",
    )
    analyze.add_argument(
        "--refresh",
        action="store_true",
        help="fetch the requested refs before analysis",
    )
    analyze.add_argument(
        "--transport",
        choices=("auto", "git", "archive"),
        default="auto",
        help="repository acquisition method",
    )
    analyze.add_argument(
        "--continue-on-error",
        action="store_true",
        help="record failed repositories and continue the batch",
    )
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
        if args.command == "analyze":
            return analyze_command(
                args.manifest,
                args.cache_dir,
                args.output_dir,
                args.limit,
                args.refresh,
                priorities=set(args.priority or []),
                transport=args.transport,
                continue_on_error=args.continue_on_error,
            )
        if args.command == "prepare-modeling":
            return prepare_modeling_command(
                args.manifest,
                args.analyses_dir,
                args.drafts_dir,
                args.output_dir,
                set(args.system_ids or []),
                args.write_prompts,
            )
    except (CardValidationError, ModelingBundleError, RepositoryAnalysisError) as error:
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


def analyze_command(
    manifest: Path,
    cache_dir: Path,
    output_dir: Path,
    limit: int | None,
    refresh: bool,
    priorities: set[str] | None,
    transport: str,
    continue_on_error: bool,
) -> int:
    if limit is not None and limit < 1:
        print("ERROR: --limit must be positive")
        return 1
    for path in analyze_manifest(
        manifest,
        cache_dir,
        output_dir,
        limit,
        refresh,
        priorities,
        transport,
        continue_on_error,
    ):
        print(f"draft  {path}")
    return 0


def prepare_modeling_command(
    manifest: Path,
    analyses_dir: Path,
    drafts_dir: Path,
    output_dir: Path,
    system_ids: set[str],
    write_prompts: bool,
) -> int:
    bundle_paths = build_modeling_bundles(
        manifest, analyses_dir, drafts_dir, output_dir, system_ids
    )
    for path in bundle_paths:
        print(f"bundle  {path}")
    if write_prompts:
        for path in write_modeling_prompts(bundle_paths, output_dir / "prompts"):
            print(f"prompt  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

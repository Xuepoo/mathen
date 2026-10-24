"""Command-line interface for the Mathen prototype."""

from __future__ import annotations

import argparse
from pathlib import Path

from .cards import (
    CardValidationError,
    discover_cards,
    load_card,
    validate_card_collection,
)
from .llm import LLMModelError, client_from_environment, model_bundles
from .modeling import (
    ModelingBundleError,
    build_modeling_bundles,
    write_modeling_prompts,
)
from .relation_candidates import (
    RelationCandidateError,
    write_relation_candidate_report,
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
DEFAULT_LLM_DRAFTS = DEFAULT_DRAFTS / "llm"


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
    model = subparsers.add_parser(
        "model", help="run an LLM over evidence bundles into draft cards"
    )
    model.add_argument("bundle_dir", nargs="?", type=Path, default=DEFAULT_BUNDLES)
    model.add_argument("--output-dir", type=Path, default=DEFAULT_LLM_DRAFTS)
    model.add_argument("--system", action="append", dest="system_ids")
    model.add_argument("--api-key", help="API key; defaults to OPENAI_API_KEY")
    model.add_argument("--model", help="model name; defaults to MATHEN_LLM_MODEL")
    model.add_argument(
        "--base-url",
        help="OpenAI-compatible API base URL; defaults to MATHEN_LLM_BASE_URL",
    )
    model.add_argument("--timeout", type=float, default=120.0)
    model.add_argument(
        "--force", action="store_true", help="overwrite existing draft cards"
    )
    relation_candidates = subparsers.add_parser(
        "relation-candidates",
        help="generate a review-only deterministic relation-candidate report",
    )
    relation_candidates.add_argument(
        "path", nargs="?", type=Path, default=DEFAULT_CARDS
    )
    relation_candidates.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_ANALYSES / "g6-relation-candidates.json",
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
        if args.command == "model":
            return model_command(
                args.bundle_dir,
                args.output_dir,
                set(args.system_ids or []),
                args.api_key,
                args.model,
                args.base_url,
                args.timeout,
                args.force,
            )
        if args.command == "relation-candidates":
            return relation_candidates_command(args.path, args.output)
    except (
        CardValidationError,
        LLMModelError,
        ModelingBundleError,
        RepositoryAnalysisError,
        RelationCandidateError,
    ) as error:
        print(f"ERROR: {error}")
        return 1
    return 2


def validate_command(path: Path) -> int:
    cards = discover_cards(path) if path.is_dir() else [path]
    if not cards:
        print(f"No cards found in {path}")
        return 1
    loaded_cards = []
    for card_path in cards:
        loaded_cards.append(load_card(card_path))
        print(f"valid  {card_path}")
    if path.is_dir():
        resolved_path = path.resolve()
        drafts_root = DEFAULT_DRAFTS.resolve()
        is_drafts = resolved_path == drafts_root or drafts_root in resolved_path.parents
        validate_card_collection(
            loaded_cards, require_feature_relation_targets=not is_drafts
        )
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


def model_command(
    bundle_dir: Path,
    output_dir: Path,
    system_ids: set[str],
    api_key: str | None,
    model: str | None,
    base_url: str | None,
    timeout: float,
    force: bool,
) -> int:
    """Run the provider-neutral model adapter and print created draft paths."""

    if timeout <= 0:
        print("ERROR: --timeout must be positive")
        return 1
    resolved_output = output_dir.resolve()
    required_root = DEFAULT_LLM_DRAFTS.resolve()
    if (
        resolved_output != required_root
        and required_root not in resolved_output.parents
    ):
        print(f"ERROR: model output must stay under {required_root}")
        return 1
    client = client_from_environment(
        base_url=base_url,
        api_key=api_key,
        model=model,
        timeout=timeout,
    )
    for path in model_bundles(
        bundle_dir, output_dir, client, system_ids or None, overwrite=force
    ):
        print(f"draft  {path}")
    return 0


def relation_candidates_command(cards_path: Path, output_path: Path) -> int:
    """Write the G6 report and print its path."""

    path = write_relation_candidate_report(cards_path, output_path)
    print(f"report  {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

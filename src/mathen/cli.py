"""Command-line interface for the Mathen prototype."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from . import __version__
from .analogies import AnalogyValidationError, discover_analogies, load_analogy
from .benchmark import (
    BenchmarkManifestValidationError,
    discover_benchmark_manifests,
    discover_retrieval_evaluation_manifests,
    load_benchmark_manifest,
    load_retrieval_evaluation_manifest,
)
from .cards import (
    CardValidationError,
    discover_cards,
    load_card,
    validate_card_collection,
)
from .config import (
    ConfigError,
    MathenConfig,
    config_to_dict,
    default_config,
    initialize_config,
    load_config,
    set_config_value,
    unset_config_value,
)
from .data_sync import SyncError, sync_reviewed_cards
from .data_sync import status as sync_status
from .llm import LLMModelError, client_from_environment, model_bundles
from .mathviews import (
    MathematicalViewValidationError,
    discover_math_view_contracts,
    load_math_view_contract,
)
from .microstructures import (
    MicrostructureValidationError,
    discover_microstructures,
    load_microstructure,
)
from .modeling import (
    ModelingBundleError,
    build_modeling_bundles,
    write_modeling_prompts,
)
from .negative_knowledge import (
    NegativeKnowledgeValidationError,
    discover_negative_knowledge,
    load_negative_knowledge,
    validate_negative_knowledge_collection,
)
from .relation_candidates import (
    RelationCandidateError,
    write_relation_candidate_report,
)
from .repositories import RepositoryAnalysisError, analyze_manifest

VERSION = __version__


def build_parser(config: MathenConfig | None = None) -> argparse.ArgumentParser:
    """Build the command parser using resolved configuration defaults."""

    config = config or default_config()
    parser = argparse.ArgumentParser(prog="mathen")
    parser.add_argument("--config", type=Path, default=config.path)
    parser.add_argument("--no-config", action="store_true")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate architecture cards")
    validate.add_argument("path", nargs="?", type=Path, default=config.paths.cards_dir)

    microstructure = subparsers.add_parser(
        "validate-microstructures", help="validate architecture microstructures"
    )
    microstructure.add_argument(
        "path", nargs="?", type=Path, default=Path("data/microstructures")
    )
    analogy = subparsers.add_parser(
        "validate-analogies", help="validate cross-domain analogy mappings"
    )
    analogy.add_argument("path", nargs="?", type=Path, default=Path("data/analogies"))
    negative_knowledge = subparsers.add_parser(
        "validate-negative-knowledge",
        help="validate evidence-bounded negative-knowledge records",
    )
    negative_knowledge.add_argument(
        "path", nargs="?", type=Path, default=Path("data/negative-knowledge")
    )
    benchmark = subparsers.add_parser(
        "validate-benchmark", help="validate research benchmark run manifests"
    )
    benchmark.add_argument("path", nargs="?", type=Path, default=Path("data/benchmark"))
    retrieval_benchmark = subparsers.add_parser(
        "validate-retrieval-evaluation",
        help="validate research-only retrieval evaluation manifests",
    )
    retrieval_benchmark.add_argument(
        "path", nargs="?", type=Path, default=Path("data/benchmark/retrieval")
    )
    mathview = subparsers.add_parser(
        "validate-mathviews", help="validate mathematical-view contracts"
    )
    mathview.add_argument("path", nargs="?", type=Path, default=Path("data/mathviews"))

    listing = subparsers.add_parser("list", help="list architecture cards")
    listing.add_argument("path", nargs="?", type=Path, default=config.paths.cards_dir)

    show = subparsers.add_parser("show", help="show one architecture card")
    show.add_argument("card_id")
    show.add_argument("path", nargs="?", type=Path, default=config.paths.cards_dir)

    analyze = subparsers.add_parser(
        "analyze", help="clone repositories and generate draft architecture cards"
    )
    analyze.add_argument(
        "manifest", nargs="?", type=Path, default=config.paths.manifest
    )
    analyze.add_argument("--cache-dir", type=Path, default=config.paths.cache_dir)
    analyze.add_argument("--output-dir", type=Path, default=config.paths.drafts_dir)
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
    prepare.add_argument(
        "manifest", nargs="?", type=Path, default=config.paths.manifest
    )
    prepare.add_argument("--analyses-dir", type=Path, default=config.paths.analyses_dir)
    prepare.add_argument("--drafts-dir", type=Path, default=config.paths.drafts_dir)
    prepare.add_argument("--output-dir", type=Path, default=config.paths.bundles_dir)
    prepare.add_argument("--system", action="append", dest="system_ids")
    prepare.add_argument(
        "--write-prompts",
        action="store_true",
        help="also render portable Markdown prompts",
    )
    model = subparsers.add_parser(
        "model", help="run an LLM over evidence bundles into draft cards"
    )
    model.add_argument(
        "bundle_dir", nargs="?", type=Path, default=config.paths.bundles_dir
    )
    model.add_argument(
        "--output-dir", type=Path, default=config.paths.drafts_dir / "llm"
    )
    model.add_argument("--system", action="append", dest="system_ids")
    model.add_argument("--api-key", help="API key; defaults to OPENAI_API_KEY")
    model.add_argument("--model", help="model name; defaults to MATHEN_LLM_MODEL")
    model.add_argument(
        "--base-url",
        help="OpenAI-compatible API base URL; defaults to MATHEN_LLM_BASE_URL",
    )
    model.add_argument("--timeout", type=float)
    model.add_argument(
        "--force", action="store_true", help="overwrite existing draft cards"
    )
    relation_candidates = subparsers.add_parser(
        "relation-candidates",
        help="generate a review-only deterministic relation-candidate report",
    )
    relation_candidates.add_argument(
        "path", nargs="?", type=Path, default=config.paths.cards_dir
    )
    relation_candidates.add_argument(
        "--output",
        type=Path,
        default=config.paths.analyses_dir / "g6-relation-candidates.json",
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
    config_parser = subparsers.add_parser("config", help="manage user configuration")
    config_subparsers = config_parser.add_subparsers(
        dest="config_command", required=True
    )
    config_init = config_subparsers.add_parser(
        "init", help="create a starter TOML file"
    )
    config_init.add_argument("--force", action="store_true")
    config_show = config_subparsers.add_parser("show", help="show resolved settings")
    config_show.add_argument("--json", action="store_true", dest="as_json")
    config_show.add_argument("--show-secrets", action="store_true")
    config_subparsers.add_parser("path", help="print the active config path")
    config_set = config_subparsers.add_parser("set", help="set a TOML value")
    config_set.add_argument("key")
    config_set.add_argument("value")
    config_unset = config_subparsers.add_parser("unset", help="remove a TOML value")
    config_unset.add_argument("key")
    subparsers.add_parser("version", help="print the Mathen version")
    sync = subparsers.add_parser("data", help="manage the local reviewed-card dataset")
    sync_subparsers = sync.add_subparsers(dest="data_command", required=True)
    sync_subparsers.add_parser("status", help="show the local dataset status")
    sync_subparsers.add_parser("sync", help="download and validate reviewed cards")
    mcp = subparsers.add_parser("mcp", help="check the configured hosted MCP endpoint")
    mcp_subparsers = mcp.add_subparsers(dest="mcp_command", required=True)
    mcp_subparsers.add_parser("path", help="print the configured MCP endpoint")
    mcp_subparsers.add_parser(
        "check", help="perform an authenticated MCP initialize request"
    )
    subparsers.add_parser("doctor", help="diagnose the local Mathen installation")
    return parser


def main() -> int:
    bootstrap = argparse.ArgumentParser(add_help=False)
    bootstrap.add_argument("--config", type=Path)
    bootstrap.add_argument("--no-config", action="store_true")
    bootstrap_args, _ = bootstrap.parse_known_args()
    try:
        config = load_config(
            bootstrap_args.config, use_file=not bootstrap_args.no_config
        )
        args = build_parser(config).parse_args()
        if args.command == "config":
            return config_command(args, config)
        if args.command == "version":
            print(VERSION)
            return 0
        if args.command == "data":
            return data_command(args, config)
        if args.command == "doctor":
            return doctor_command(config)
        if args.command == "mcp":
            return mcp_command(args, config)
        if args.command == "validate":
            return validate_command(args.path, config)
        if args.command == "validate-microstructures":
            return validate_microstructures_command(args.path)
        if args.command == "validate-analogies":
            return validate_analogies_command(args.path)
        if args.command == "validate-negative-knowledge":
            return validate_negative_knowledge_command(args.path)
        if args.command == "validate-benchmark":
            return validate_benchmark_command(args.path)
        if args.command == "validate-retrieval-evaluation":
            return validate_retrieval_evaluation_command(args.path)
        if args.command == "validate-mathviews":
            return validate_mathviews_command(args.path)
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
                config,
            )
        if args.command == "relation-candidates":
            return relation_candidates_command(args.path, args.output)
    except (
        CardValidationError,
        ConfigError,
        SyncError,
        LLMModelError,
        ModelingBundleError,
        RepositoryAnalysisError,
        RelationCandidateError,
        MicrostructureValidationError,
        AnalogyValidationError,
        NegativeKnowledgeValidationError,
        BenchmarkManifestValidationError,
        MathematicalViewValidationError,
    ) as error:
        print(f"ERROR: {error}")
        return 1
    return 2


def validate_command(path: Path, config: MathenConfig | None = None) -> int:
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
        drafts_root = (config or default_config()).paths.drafts_dir.resolve()
        is_drafts = resolved_path == drafts_root or drafts_root in resolved_path.parents
        validate_card_collection(
            loaded_cards, require_feature_relation_targets=not is_drafts
        )
    return 0


def validate_microstructures_command(path: Path) -> int:
    """Validate all standalone microstructures at ``path``."""

    paths = discover_microstructures(path)
    if not paths:
        print(f"No microstructures found in {path}; nothing to validate")
        return 0
    for microstructure_path in paths:
        load_microstructure(microstructure_path)
        print(f"valid  {microstructure_path}")
    return 0


def validate_analogies_command(path: Path) -> int:
    """Validate all standalone cross-domain analogy mappings at ``path``."""

    paths = discover_analogies(path)
    if not paths:
        print(f"No analogies found in {path}; nothing to validate")
        return 0
    for analogy_path in paths:
        load_analogy(analogy_path)
        print(f"valid  {analogy_path}")
    return 0


def validate_negative_knowledge_command(path: Path) -> int:
    """Validate standalone evidence-bounded negative-knowledge records."""

    paths = discover_negative_knowledge(path)
    if not paths:
        print(f"No negative-knowledge records found in {path}; nothing to validate")
        return 0
    records = []
    for record_path in paths:
        records.append(load_negative_knowledge(record_path))
    validate_negative_knowledge_collection(records)
    for record_path in paths:
        print(f"valid  {record_path}")
    return 0


def validate_benchmark_command(path: Path) -> int:
    """Validate research-only benchmark run manifests."""

    paths = discover_benchmark_manifests(path)
    if not paths:
        print(f"No benchmark manifests found in {path}; nothing to validate")
        return 0
    for manifest_path in paths:
        load_benchmark_manifest(manifest_path)
        print(f"valid  {manifest_path}")
    return 0


def validate_retrieval_evaluation_command(path: Path) -> int:
    """Validate research-only retrieval evaluation manifests."""

    paths = discover_retrieval_evaluation_manifests(path)
    if not paths:
        print(f"No retrieval evaluation manifests found in {path}; nothing to validate")
        return 0
    for manifest_path in paths:
        load_retrieval_evaluation_manifest(manifest_path)
        print(f"valid  {manifest_path}")
    return 0


def validate_mathviews_command(path: Path) -> int:
    """Validate standalone evidence-bounded mathematical-view contracts."""

    paths = discover_math_view_contracts(path)
    if not paths:
        print(f"No mathematical-view contracts found in {path}; nothing to validate")
        return 0
    for contract_path in paths:
        load_math_view_contract(contract_path)
        print(f"valid  {contract_path}")
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
    timeout: float | None,
    force: bool,
    config: MathenConfig | None = None,
) -> int:
    """Run the provider-neutral model adapter and print created draft paths."""

    resolved_config = config or default_config()
    effective_timeout = timeout if timeout is not None else resolved_config.llm.timeout
    if effective_timeout <= 0:
        print("ERROR: --timeout must be positive")
        return 1
    resolved_output = output_dir.resolve()
    required_root = (resolved_config.paths.drafts_dir / "llm").resolve()
    if (
        resolved_output != required_root
        and required_root not in resolved_output.parents
    ):
        print(f"ERROR: model output must stay under {required_root}")
        return 1
    llm = resolved_config.llm
    provider = (llm.providers or {}).get(llm.provider, {})
    provider_timeout = float(provider.get("timeout", effective_timeout))
    if provider_timeout <= 0:
        print("ERROR: provider timeout must be positive")
        return 1
    client = client_from_environment(
        base_url=base_url
        or os.environ.get("MATHEN_LLM_BASE_URL")
        or provider.get("base_url")
        or llm.base_url,
        api_key=(
            api_key
            or os.environ.get(str(provider.get("api_key_env", llm.api_key_env)))
            or os.environ.get("OPENAI_API_KEY")
            or provider.get("api_key")
            or llm.api_key
        ),
        model=model
        or os.environ.get("MATHEN_LLM_MODEL")
        or provider.get("model")
        or llm.model,
        timeout=provider_timeout,
        api_key_env=str(provider.get("api_key_env", llm.api_key_env)),
    )
    for path in model_bundles(
        bundle_dir,
        output_dir,
        client,
        system_ids or None,
        overwrite=force,
        provider=llm.provider,
    ):
        print(f"draft  {path}")
    return 0


def relation_candidates_command(cards_path: Path, output_path: Path) -> int:
    """Write the G6 report and print its path."""

    path = write_relation_candidate_report(cards_path, output_path)
    print(f"report  {path}")
    return 0


def config_command(args: argparse.Namespace, config: MathenConfig) -> int:
    """Handle configuration lifecycle and inspection commands."""

    if args.config_command == "init":
        path = initialize_config(args.config, force=args.force)
        print(f"created  {path}")
        return 0
    if args.config_command == "path":
        print(config.path)
        return 0
    if args.config_command == "show":
        values = config_to_dict(config, redact_secrets=not args.show_secrets)
        if args.as_json:
            print(json.dumps(values, indent=2, ensure_ascii=False))
        else:
            print(f"config  {config.path}")
            print(f"status  {'loaded' if config.loaded else 'defaults'}")
            for section, entries in values.items():
                print(f"[{section}]")
                for key, value in entries.items():
                    print(f"{key} = {value}")
        return 0
    if args.config_command == "set":
        path = set_config_value(args.key, args.value, args.config)
        print(f"updated  {path}")
        return 0
    if args.config_command == "unset":
        path = unset_config_value(args.key, args.config)
        print(f"updated  {path}")
        return 0
    return 2


def data_command(args: argparse.Namespace, config: MathenConfig) -> int:
    """Show or update the locally cached reviewed cards."""

    current = sync_status(config)
    if args.data_command == "status":
        print(f"directory  {current.directory}")
        print(f"cards      {current.card_count}")
        if current.source:
            print(f"source     {current.source}")
        if current.ref:
            print(f"ref        {current.ref}")
        if current.digest:
            print(f"digest     {current.digest}")
        print(f"valid      {'yes' if current.valid else 'no'}")
        if current.error:
            print(f"error      {current.error}")
        return 0
    if args.data_command == "sync":
        updated = sync_reviewed_cards(config)
        print(f"synced     {updated.card_count} cards")
        print(f"directory  {updated.directory}")
        return 0
    return 2


def doctor_command(config: MathenConfig) -> int:
    """Print actionable local installation diagnostics without contacting APIs."""

    dataset = sync_status(config)
    provider = (config.llm.providers or {}).get(config.llm.provider, {})
    api_key_env = str(provider.get("api_key_env", config.llm.api_key_env))
    api_key_configured = bool(
        provider.get("api_key")
        or config.llm.api_key
        or os.environ.get(api_key_env)
        or os.environ.get("OPENAI_API_KEY")
    )
    print(f"Mathen version: {VERSION}")
    print(f"Config: {config.path} ({'loaded' if config.loaded else 'defaults'})")
    print(f"Data directory: {config.paths.data_dir}")
    reviewed_status = "valid" if dataset.valid else f"invalid ({dataset.error})"
    print(f"Reviewed cards: {dataset.card_count} ({reviewed_status})")
    print(f"Cache directory: {config.paths.cache_dir}")
    print(f"LLM provider: {config.llm.provider}")
    print(f"LLM model: {provider.get('model') or config.llm.model or 'not configured'}")
    print(f"LLM API key: {'configured' if api_key_configured else 'not configured'}")
    print(f"MCP: {config.mcp.url or 'not configured'}")
    return 0


def mcp_command(args: argparse.Namespace, config: MathenConfig) -> int:
    """Inspect or verify the configured hosted MCP endpoint."""

    if args.mcp_command == "path":
        print(config.mcp.url or "not configured")
        return 0
    if args.mcp_command != "check":
        return 2
    if not config.mcp.url:
        print("ERROR: configure mcp.url first")
        return 1
    token = os.environ.get(config.mcp.token_env)
    if not token:
        print(f"ERROR: set {config.mcp.token_env} before checking MCP")
        return 1
    request = Request(
        config.mcp.url,
        data=json.dumps(
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {
                    "protocolVersion": "2025-06-18",
                    "capabilities": {},
                    "clientInfo": {"name": "mathen-cli", "version": VERSION},
                },
            }
        ).encode("utf-8"),
        headers={
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Mcp-Protocol-Version": "2025-06-18",
        },
        method="POST",
    )
    try:
        with urlopen(request, timeout=config.mcp.timeout) as response:
            body = json.loads(response.read(256_000))
    except HTTPError as error:
        print(f"ERROR: MCP endpoint returned HTTP {error.code}")
        return 1
    except URLError as error:
        print(f"ERROR: MCP endpoint request failed: {error.reason}")
        return 1
    except (TimeoutError, OSError, json.JSONDecodeError) as error:
        print(f"ERROR: MCP endpoint response was invalid: {error}")
        return 1
    if (
        not isinstance(body, dict)
        or body.get("jsonrpc") != "2.0"
        or body.get("id") != 1
        or "result" not in body
        or not isinstance(body["result"], dict)
        or not isinstance(body["result"].get("protocolVersion"), str)
        or not isinstance(body["result"].get("capabilities"), dict)
        or not isinstance(body["result"].get("serverInfo"), dict)
    ):
        print("ERROR: MCP endpoint returned an invalid initialize response")
        return 1
    result = body["result"]
    server_info = result.get("serverInfo") if isinstance(result, dict) else None
    name = server_info.get("name") if isinstance(server_info, dict) else None
    print(f"connected  {name or 'Mathen MCP'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

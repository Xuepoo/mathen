"""Build deterministic evidence bundles for LLM-assisted architecture modeling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

from mathen.repositories import load_manifest

MODELING_CONTRACT_VERSION = 2
LLM_RESEARCH_PROTOCOL_VERSION = "mth-0112-v1"
CROSS_DOMAIN_ANALOGY_SCHEMA_VERSION = "1.0"


class ModelingBundleError(RuntimeError):
    """Raised when a modeling bundle cannot be assembled."""


def build_modeling_bundles(
    manifest: Path,
    analyses_dir: Path,
    drafts_dir: Path,
    output_dir: Path,
    system_ids: set[str] | None = None,
) -> list[Path]:
    """Create one LLM input bundle per analyzed repository."""

    specs = load_manifest(manifest)
    if system_ids:
        specs = [spec for spec in specs if spec.id in system_ids]
    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in specs:
        analysis_path = analyses_dir / f"{spec.id}.json"
        draft_path = drafts_dir / f"{spec.id}.json"
        if not analysis_path.is_file() or not draft_path.is_file():
            continue
        try:
            analysis = _load_object(analysis_path)
            draft = _load_object(draft_path)
        except (OSError, json.JSONDecodeError, ModelingBundleError) as error:
            raise ModelingBundleError(
                f"{spec.id}: cannot load evidence: {error}"
            ) from error
        bundle = build_modeling_bundle(spec, analysis, draft)
        path = output_dir / f"{spec.id}.json"
        path.write_text(
            json.dumps(bundle, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        written.append(path)
    if not written:
        raise ModelingBundleError("no matching analysis and draft pairs found")
    return written


def build_modeling_bundle(
    spec: Any, analysis: dict[str, Any], draft: dict[str, Any]
) -> dict[str, Any]:
    """Construct the stable prompt-facing contract for one system."""

    required_analysis = {"system_id", "commit", "commit_url", "provenance"}
    missing = required_analysis - analysis.keys()
    if missing:
        raise ModelingBundleError(f"analysis is missing fields: {sorted(missing)}")
    if analysis["system_id"] != spec.id or draft.get("id") != spec.id:
        raise ModelingBundleError("manifest, analysis, and draft IDs do not match")
    return {
        "contract_version": MODELING_CONTRACT_VERSION,
        "system": {
            "id": spec.id,
            "name": spec.name,
            "category": spec.category,
            "repository": spec.repository,
            "documentation": spec.documentation,
            "requested_ref": spec.ref,
            "commit": analysis["commit"],
            "commit_url": analysis["commit_url"],
            "provenance": analysis["provenance"],
        },
        "deterministic_observations": analysis,
        "existing_structural_draft": draft,
        "modeling_task": {
            "objective": (
                "Transform repository evidence into a reviewed-quality, "
                "evidence-backed architecture model."
            ),
            "questions": [
                {
                    "dimension": "domains and components",
                    "question": (
                        "What user-facing domains, services, subsystems, and "
                        "deployment roles exist, and how do they interact?"
                    ),
                },
                {
                    "dimension": "state and lifecycle",
                    "question": (
                        "What are the durable, mutable, cached, and ephemeral "
                        "state components; what transitions change them; and "
                        "what invariants are observable?"
                    ),
                },
                {
                    "dimension": "interfaces and dependencies",
                    "question": (
                        "Which APIs, protocols, queues, storage interfaces, "
                        "plugins, and external dependencies connect the "
                        "components, and which direction does each dependency "
                        "flow?"
                    ),
                },
                {
                    "dimension": "consistency and ordering",
                    "question": (
                        "Where are ordering, ownership, isolation, consistency, "
                        "concurrency, or idempotency rules enforced, and what "
                        "is explicitly left eventual or unspecified?"
                    ),
                },
                {
                    "dimension": "security and boundaries",
                    "question": (
                        "Which boundaries concern namespace, tenant, identity, "
                        "authorization, transport, or process isolation, and "
                        "what configuration is required for the security claim "
                        "to hold?"
                    ),
                },
                {
                    "dimension": "failure and recovery",
                    "question": (
                        "How do failures, timeouts, retries, redelivery, replay, "
                        "failover, repair, and operator actions affect state and "
                        "progress?"
                    ),
                },
                {
                    "dimension": "resources and scale",
                    "question": (
                        "Which queues, shards, caches, limits, timers, "
                        "backpressure mechanisms, and resource costs constrain "
                        "throughput, latency, or cardinality?"
                    ),
                },
                {
                    "dimension": "evolution and compatibility",
                    "question": (
                        "How do versions, migrations, rolling upgrades, schema or "
                        "protocol compatibility, and deprecation affect existing "
                        "state and clients?"
                    ),
                },
                {
                    "dimension": "transferable architecture",
                    "question": (
                        "Which structures are independently meaningful reusable "
                        "patterns, and which observations remain product-specific, "
                        "implementation detail, or only analogy?"
                    ),
                },
            ],
            "coverage_protocol": {
                "for_each_dimension": [
                    "cite the supporting evidence IDs",
                    "record a concise supported claim",
                    "record what is unknown or out of scope when evidence is "
                    "insufficient",
                ],
                "review_questions": [
                    "Does every component or domain named in the source evidence "
                    "have a differentiated role rather than a generic scope label?",
                    "Does each mathematical view answer one concrete question and "
                    "state assumptions, limits, and counterexamples?",
                    "Are source relations supported by evidence of the relationship "
                    "itself, rather than shared vocabulary or co-occurrence?",
                    "Was the evidence checked against the requested fixed revision, "
                    "with later documentation marked as current-doc context?",
                ],
            },
            "mathematical_view_contract": {
                "schema": "schemas/architecture-mathematical-view.schema.json",
                "version": "1.0",
                "optional_mapping": {
                    "model": (
                        "contract.family and contract carrier/operations/relations"
                    ),
                    "question": "contract.question",
                    "assumptions": "contract.assumptions",
                    "claim_type": "contract.claim_type",
                    "claim_status": "contract.claim_status",
                    "evidence_ids": "contract.evidence_ids",
                },
                "families": [
                    "graph",
                    "dag",
                    "partial_order",
                    "state_machine",
                    "algebraic",
                    "semilattice",
                    "monotone_system",
                    "refinement",
                    "simulation",
                    "bisimulation",
                    "cost",
                    "complexity",
                    "queueing",
                    "reliability",
                ],
                "required_dimensions": [
                    "carrier",
                    "operations",
                    "relations",
                    "transitions",
                    "laws_or_checks",
                    "assumptions",
                    "validity_scope",
                    "evidence_ids",
                    "claim_type",
                    "claim_status",
                    "classification",
                ],
                "classification_rule": (
                    "Classification is a deterministic finite-data consistency result: "
                    "valid means the supplied checks pass, invalid means a check "
                    "fails, and undetermined means the evidence or representation "
                    "is insufficient. "
                    "No classification is a formal proof."
                ),
            },
            "required_claim_types": ["fact", "inference", "hypothesis", "analogy"],
            "claim_protocol": {
                "required_fields": [
                    "claim_type",
                    "claim_status",
                    "evidence_ids",
                ],
                "uncertainty_rule": (
                    "When evidence is incomplete, state the uncertainty and its "
                    "scope; use hypothesis or analogy rather than upgrading the "
                    "claim to fact."
                ),
                "disagreement_rule": (
                    "Record conflicting evidence or reviewer disagreement as an "
                    "unresolved note in the protocol record; do not silently "
                    "select a consensus claim."
                ),
                "analogy_rule": (
                    "A cross-domain resemblance is a candidate abstraction only. "
                    "Label it analogy, name the shared structure and boundary, "
                    "and do not imply equivalence, dependency, composition, or "
                    "historical influence without direct evidence."
                ),
            },
            "cross_domain_analogy_mapping": {
                "schema_version": CROSS_DOMAIN_ANALOGY_SCHEMA_VERSION,
                "schema": "schemas/cross-domain-analogy.schema.json",
                "required_dimensions": [
                    "source_domain",
                    "target_domain",
                    "source_concepts",
                    "target_concepts",
                    "mapping_type",
                    "scale",
                    "shared_properties",
                    "preserved_properties",
                    "non_preserved_properties",
                    "scope",
                    "counterexamples",
                    "non_equivalence",
                    "claim_type",
                    "claim_status",
                    "evidence",
                ],
                "boundary": (
                    "Use a standalone analogy mapping for cross-domain resemblance. "
                    "Do not turn it into a canonical relation or claim equivalence, "
                    "dependency, composition, substitutability, proof, or historical "
                    "influence."
                ),
                "evidence_rule": (
                    "Every mapping claim must cite evidence already present in the "
                    "mapping; unknown evidence remains unknown or out of scope."
                ),
            },
            "evidence_rules": [
                "Do not promote a path name or file count into a semantic fact.",
                "Every feature and mathematical view must cite evidence IDs.",
                "Use only evidence IDs already present in existing_structural_draft.",
                "For every coverage dimension, label the result supported, unknown, "
                "or out-of-scope; absence of evidence is not evidence of absence.",
                "Do not add features to satisfy a quota: each feature must identify "
                "a distinct boundary, mechanism, state transition, or trade-off.",
                "Differentiate shared architecture patterns from vague scope labels "
                "and product-specific names.",
                "Treat current documentation as documenting its access date; do not "
                "apply a later guarantee to the pinned source revision without source "
                "evidence.",
                "Use hypothesis or analogy when the mathematical "
                "correspondence is not established.",
                "Keep product-specific facts separate from transferable feature names.",
            ],
            "output": {
                "format": "Mathen Architecture Card JSON",
                "schema": "schemas/architecture-card.schema.json",
                "destination": "data/drafts/<system-id>.json",
                "status": "draft; requires human review before data/systems promotion",
                "canonical_boundary": (
                    "Automated output is never canonical and never proof. A human "
                    "reviewer must check evidence, claim type, uncertainty, and "
                    "disagreement before deliberate promotion."
                ),
            },
            "evaluation": {
                "dimensions": [
                    "breadth",
                    "citation_quality",
                    "error_rate",
                    "reviewer_usefulness",
                ],
                "recording_rule": (
                    "Evaluate a batch against a reviewed reference or reviewer "
                    "audit; report each dimension separately rather than reducing "
                    "quality to one confidence score."
                ),
            },
        },
        "research_protocol": {
            "version": LLM_RESEARCH_PROTOCOL_VERSION,
            "provenance": {
                "provider": "record the provider name, not a secret",
                "model": "record the exact model identifier",
                "prompt_sha256": "record the rendered prompt digest",
                "evidence_bundle_sha256": "record the input bundle digest",
                "source_revision": "record system.commit and provenance",
            },
            "reproducibility": {
                "secret_safe": True,
                "rule": (
                    "Never store API keys, authorization headers, or raw secret-"
                    "bearing configuration in bundles, prompts, drafts, or run "
                    "records."
                ),
            },
            "review": {
                "required_before_canonical": True,
                "review_record": [
                    "reviewer",
                    "reviewed_at",
                    "decision",
                    "uncertainties",
                    "disagreements",
                ],
            },
        },
    }


def render_modeling_prompt(bundle: dict[str, Any]) -> str:
    """Render a portable English prompt from a modeling bundle."""

    payload = json.dumps(bundle, indent=2, ensure_ascii=False)
    return (
        "You are the Mathen software architecture modeling analyst.\n"
        "Follow the modeling_task contract below. Return only one JSON object "
        "conforming to the Mathen Architecture Card schema. Do not invent "
        "evidence, guarantees, or historical influence.\n\n"
        f"MODEL PREPARATION BUNDLE:\n{payload}\n"
    )


def protocol_run_record(
    bundle: dict[str, Any],
    prompt: str,
    *,
    provider: str,
    model: str,
) -> dict[str, Any]:
    """Build a secret-free provenance record for one modeling attempt.

    The record intentionally contains hashes rather than prompt or evidence
    contents. It can be stored beside an unreviewed draft without becoming a
    second source of claims.
    """

    system = bundle.get("system")
    if not isinstance(system, dict):
        raise ModelingBundleError("modeling bundle has no system metadata")
    return {
        "protocol_version": LLM_RESEARCH_PROTOCOL_VERSION,
        "system_id": system.get("id"),
        "source_revision": {
            "commit": system.get("commit"),
            "provenance": system.get("provenance"),
        },
        "provider": provider,
        "model": model,
        "prompt_sha256": hashlib.sha256(prompt.encode("utf-8")).hexdigest(),
        "evidence_bundle_sha256": hashlib.sha256(
            json.dumps(
                bundle, sort_keys=True, separators=(",", ":"), ensure_ascii=False
            ).encode("utf-8")
        ).hexdigest(),
        "secret_safe": True,
        "review": {
            "status": "pending",
            "canonical_promotion": "human review required",
            "uncertainties": [],
            "disagreements": [],
        },
        "evaluation": {
            "breadth": None,
            "citation_quality": None,
            "error_rate": None,
            "reviewer_usefulness": None,
        },
    }


def write_modeling_prompts(bundle_paths: list[Path], prompt_dir: Path) -> list[Path]:
    """Write human- and agent-readable prompt files next to bundle data."""

    prompt_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for bundle_path in bundle_paths:
        bundle = _load_object(bundle_path)
        prompt_path = prompt_dir / f"{bundle_path.stem}.md"
        prompt_path.write_text(render_modeling_prompt(bundle), encoding="utf-8")
        written.append(prompt_path)
    return written


def _load_object(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ModelingBundleError(f"{path}: expected a JSON object")
    return data

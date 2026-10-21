"""Build deterministic evidence bundles for LLM-assisted architecture modeling."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mathen.repositories import load_manifest

MODELING_CONTRACT_VERSION = 1


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
                "What are the system's core abstractions and state components?",
                "Which operations change state, and what invariants do they preserve?",
                "Which reusable architecture features are supported by evidence?",
                "Which mathematical views explain those features, under "
                "which assumptions?",
                "What benefits, costs, failure modes, and counterexamples apply?",
            ],
            "required_claim_types": ["fact", "inference", "hypothesis", "analogy"],
            "evidence_rules": [
                "Do not promote a path name or file count into a semantic fact.",
                "Every feature and mathematical view must cite evidence IDs.",
                "Use only evidence IDs already present in existing_structural_draft.",
                "Use hypothesis or analogy when the mathematical "
                "correspondence is not established.",
                "Keep product-specific facts separate from transferable feature names.",
            ],
            "output": {
                "format": "Mathen Architecture Card JSON",
                "schema": "schemas/architecture-card.schema.json",
                "destination": "data/drafts/<system-id>.json",
                "status": "draft; requires human review before data/systems promotion",
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

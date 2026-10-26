"""Build a deterministic, read-only research review queue projection.

The default input is the resolved ``origin/main`` Git ref.  Files are read via
``git show`` so an audit cannot accidentally inspect or mutate a dirty
worktree.  The report preserves missing metadata as ``not-recorded`` and
explicit ``unknown`` as ``unknown``; it never promotes research artifacts or
turns deterministic classifications into review decisions.
"""

from __future__ import annotations

import argparse
import json
import subprocess
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from mathen.mathviews import validate_math_view_contract
from mathen.relation_candidates import generate_relation_candidate_report

TASK = "MTH-0159"
ANALYSIS_VERSION = "mth-0159-research-review-queue-v1"
SCOPE_DIMENSIONS = (
    "validity_scope",
    "workload",
    "runtime_conditions",
    "scale",
    "failure_conditions",
)
LIFECYCLE_SURFACES = ("features", "mathematical_views")
OBSERVATION_KINDS = frozenset(
    {
        "experiment",
        "benchmark",
        "fault-injection",
        "operational-observation",
        "counterexample",
        "negative-result",
    }
)


class AuditError(ValueError):
    """Raised when a source ref or research artifact cannot be read."""


def audit_documents(
    cards: Iterable[dict[str, Any]],
    experiments: Iterable[tuple[str, dict[str, Any]]],
    mathviews: Iterable[tuple[str, dict[str, Any]]],
    *,
    source_revision: str = "not-recorded",
    source_ref: str = "provided-input",
) -> dict[str, Any]:
    """Return a stable review queue projection without changing any input."""

    ordered_cards = sorted(cards, key=lambda card: str(card.get("id", "")))
    card_ids = [card.get("id") for card in ordered_cards]
    if any(not isinstance(card_id, str) or not card_id for card_id in card_ids):
        raise AuditError("every canonical card needs a non-empty string id")
    if len(card_ids) != len(set(card_ids)):
        raise AuditError("canonical card ids must be unique")

    ordered_experiments = sorted(experiments, key=lambda item: item[0])
    ordered_mathviews = sorted(mathviews, key=lambda item: item[0])
    scope = _scope_audit(ordered_cards)
    lifecycle = _lifecycle_audit(ordered_cards)
    observations = _observation_audit(ordered_cards, ordered_experiments)
    standalone = _standalone_mathview_audit(ordered_mathviews)
    relation_report = generate_relation_candidate_report(ordered_cards)

    return {
        "task": TASK,
        "analysis_version": ANALYSIS_VERSION,
        "source": {
            "ref": source_ref,
            "revision": source_revision,
            "canonical_corpus": "data/systems/*.json",
            "research_artifacts": [
                "data/experiments/*.json",
                "data/mathviews/*.json",
            ],
        },
        "review_boundary": {
            "review_only": True,
            "mutation_performed": False,
            "canonical_cards_written": False,
            "drafts_written": False,
            "research_artifacts_promoted": False,
            "lifecycle_status_inferred": False,
            "scope_status_inferred": False,
            "relation_written": False,
            "classification_is_review_decision": False,
            "missing_metadata_is_negative_finding": False,
        },
        "counts": {
            "canonical_cards": len(ordered_cards),
            "research_experiment_artifacts": len(ordered_experiments),
            "standalone_mathview_contracts": len(ordered_mathviews),
        },
        "scope_context": scope,
        "lifecycle": lifecycle,
        "detached_observation_evidence": observations,
        "standalone_mathviews": standalone,
        "relation_candidates": {
            "analysis_version": relation_report["analysis_version"],
            "existing_relations": relation_report["existing_relations"],
            "candidates": relation_report["candidates"],
            "candidate_count": len(relation_report["candidates"]),
            "existing_relation_count": len(relation_report["existing_relations"]),
        },
    }


def audit_ref(root: Path, ref: str = "origin/main") -> dict[str, Any]:
    """Read canonical and research JSON files from one Git ref."""

    revision = _git(root, ["rev-parse", f"{ref}^{{commit}}"]).strip()
    paths = _git(root, ["ls-tree", "-r", "--name-only", ref]).splitlines()

    def load_paths(prefix: str) -> list[tuple[str, dict[str, Any]]]:
        selected = sorted(
            path
            for path in paths
            if path.startswith(prefix + "/") and path.endswith(".json")
        )
        loaded = []
        for path in selected:
            try:
                value = json.loads(_git(root, ["show", f"{ref}:{path}"]))
            except json.JSONDecodeError as error:
                raise AuditError(f"{ref}:{path} is not valid JSON: {error}") from error
            if not isinstance(value, dict):
                raise AuditError(f"{ref}:{path} must contain a JSON object")
            loaded.append((path, value))
        return loaded

    card_files = load_paths("data/systems")
    cards = [value for _, value in card_files]
    return audit_documents(
        cards,
        load_paths("data/experiments"),
        load_paths("data/mathviews"),
        source_revision=revision,
        source_ref=ref,
    )


def write_ref_audit(root: Path, output: Path, ref: str = "origin/main") -> Path:
    """Write one deterministic audit report and return its path."""

    report = audit_ref(root, ref)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return output


def _scope_audit(cards: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[tuple[str, dict[str, Any]]] = []
    records.extend((f"card:{card['id']}", card) for card in cards)
    for card in cards:
        for surface in ("features", "mathematical_views"):
            values = card.get(surface, [])
            if not isinstance(values, list):
                continue
            for index, value in enumerate(values):
                if isinstance(value, dict):
                    records.append(
                        (
                            f"card:{card['id']}:{surface}[{index}]"
                            f":{_record_id(value, index)}",
                            value,
                        )
                    )
        for index, value in enumerate(card.get("evidence", [])):
            if isinstance(value, dict):
                records.append(
                    (
                        f"card:{card['id']}:evidence[{index}]"
                        f":{_record_id(value, index)}",
                        value,
                    )
                )

    candidates: list[dict[str, Any]] = []
    surfaces: dict[str, dict[str, Any]] = {}
    for location, record in records:
        if ":features[" in location:
            surface = "features"
        elif ":mathematical_views[" in location:
            surface = "mathematical_views"
        elif ":evidence[" in location:
            surface = "evidence"
        else:
            surface = "cards"
        row = surfaces.setdefault(
            surface,
            {
                "total": 0,
                "dimensions": {dimension: Counter() for dimension in SCOPE_DIMENSIONS},
            },
        )
        row["total"] += 1
        envelope = record.get("scope_context")
        for dimension in SCOPE_DIMENSIONS:
            status = _scope_status(envelope, dimension)
            row["dimensions"][dimension][status] += 1
            if status in {"not-recorded", "unknown", "unspecified", "invalid"}:
                candidates.append(
                    {
                        "location": location,
                        "dimension": dimension,
                        "status": status,
                        "reason": (
                            "missing-scope-context"
                            if status == "not-recorded"
                            else "scope-dimension-needs-review"
                        ),
                    }
                )

    for row in surfaces.values():
        row["dimensions"] = {
            dimension: dict(sorted(counts.items()))
            for dimension, counts in row["dimensions"].items()
        }
    return {
        "dimensions": list(SCOPE_DIMENSIONS),
        "surfaces": dict(sorted(surfaces.items())),
        "candidate_count": len(candidates),
        "candidates": sorted(
            candidates, key=lambda item: (item["location"], item["dimension"])
        ),
    }


def _lifecycle_audit(cards: list[dict[str, Any]]) -> dict[str, Any]:
    records: list[dict[str, Any]] = []
    missing: list[dict[str, Any]] = []
    status_counts = {surface: Counter() for surface in LIFECYCLE_SURFACES}
    for card in cards:
        for surface in LIFECYCLE_SURFACES:
            values = card.get(surface, [])
            if not isinstance(values, list):
                continue
            for index, value in enumerate(values):
                if not isinstance(value, dict):
                    continue
                location = f"card:{card['id']}:{surface}[{index}]"
                record_id = _record_id(value, index)
                lifecycle = value.get("lifecycle")
                status = (
                    lifecycle.get("status")
                    if isinstance(lifecycle, dict)
                    else "not-recorded"
                )
                if not isinstance(status, str) or not status:
                    status = "not-recorded"
                status_counts[surface][status] += 1
                if isinstance(lifecycle, dict):
                    records.append(
                        {
                            "location": location,
                            "record_id": record_id,
                            "status": status,
                            "claim_type": lifecycle.get("claim_type", "not-recorded"),
                            "claim_status": lifecycle.get(
                                "claim_status", "not-recorded"
                            ),
                            "evidence_ids": sorted(
                                item
                                for item in lifecycle.get("evidence_ids", [])
                                if isinstance(item, str)
                            ),
                        }
                    )
                else:
                    missing.append(
                        {
                            "location": location,
                            "record_id": record_id,
                            "status": "not-recorded",
                            "reason": "lifecycle-not-recorded",
                        }
                    )
    return {
        "surfaces": {
            surface: {
                "status_counts": dict(sorted(status_counts[surface].items())),
                "missing_count": len(
                    [item for item in missing if f":{surface}[" in item["location"]]
                ),
            }
            for surface in LIFECYCLE_SURFACES
        },
        "recorded": sorted(records, key=lambda item: item["location"]),
        "missing": sorted(missing, key=lambda item: item["location"]),
        "candidate_count": len(records) + len(missing),
        "review_candidates": sorted(
            [
                {**item, "reason": "recorded-lifecycle-needs-independent-review"}
                for item in records
            ]
            + missing,
            key=lambda item: item["location"],
        ),
    }


def _observation_audit(
    cards: list[dict[str, Any]],
    experiments: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    canonical_evidence = {
        evidence.get("id")
        for card in cards
        for evidence in card.get("evidence", [])
        if isinstance(evidence, dict) and isinstance(evidence.get("id"), str)
    }
    records: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for path, value in experiments:
        if not _is_observation(value):
            continue
        review = value.get("review")
        review_status = (
            review.get("status") if isinstance(review, dict) else "not-recorded"
        )
        if not isinstance(review_status, str) or not review_status:
            review_status = "not-recorded"
        refs = (
            review.get("card_claim_refs")
            if isinstance(review, dict)
            and isinstance(review.get("card_claim_refs"), list)
            else []
        )
        explicit_refs = sorted(item for item in refs if isinstance(item, str))
        row = {
            "path": path,
            "id": value.get("id", "not-recorded"),
            "kind": value.get("kind", "not-recorded"),
            "review_status": review_status,
            "card_claim_refs": explicit_refs,
            "promoted": bool(explicit_refs),
            "artifact_detached": True,
            "detached": value.get("id") not in canonical_evidence,
            "canonical_evidence_linked": value.get("id") in canonical_evidence,
            "result_status": _nested(value, "result", "status"),
            "storage_scope": _nested(value, "result_boundary", "storage_scope"),
            "promotion_requires_human_review": _nested(
                value, "result_boundary", "promotion_requires_human_review"
            ),
        }
        records.append(row)
        reasons = []
        if review_status != "reviewed":
            reasons.append("review-not-recorded-as-reviewed")
        if not explicit_refs:
            reasons.append("no-explicit-card-claim-ref")
        if row["promotion_requires_human_review"] is True:
            reasons.append("human-review-promotion-gate")
        if reasons:
            candidates.append({"path": path, "id": row["id"], "reasons": reasons})
    return {
        "contract": "observation_version=1",
        "records": sorted(records, key=lambda item: item["path"]),
        "candidate_count": len(candidates),
        "review_candidates": sorted(candidates, key=lambda item: item["path"]),
        "canonical_evidence_ids_matching_observations": sorted(
            {record["id"] for record in records if record["canonical_evidence_linked"]}
        ),
    }


def _standalone_mathview_audit(
    mathviews: list[tuple[str, dict[str, Any]]],
) -> dict[str, Any]:
    contracts: list[dict[str, Any]] = []
    records: list[dict[str, Any]] = []
    candidates: list[dict[str, Any]] = []
    for path, contract in mathviews:
        validation_error = None
        try:
            validate_math_view_contract(contract, path=Path(path))
            validation_result = "valid"
        except (ValueError, TypeError) as error:
            validation_result = "invalid"
            validation_error = str(error)
        validation_records = contract.get("validation_records", [])
        if not isinstance(validation_records, list):
            validation_records = []
        contracts.append(
            {
                "path": path,
                "id": contract.get("id", "not-recorded"),
                "classification": _nested(contract, "classification", "result"),
                "deterministic_validation": validation_result,
                "validation_error": validation_error,
                "claim_status": contract.get("claim_status", "not-recorded"),
                "validation_record_count": len(validation_records),
            }
        )
        for index, record in enumerate(validation_records):
            if not isinstance(record, dict):
                records.append(
                    {
                        "path": path,
                        "index": index,
                        "id": "not-recorded",
                        "claim_status": "invalid",
                        "result_status": "invalid",
                    }
                )
                candidates.append(
                    {"path": path, "index": index, "reasons": ["invalid-record"]}
                )
                continue
            row = {
                "path": path,
                "index": index,
                "id": record.get("id", "not-recorded"),
                "kind": record.get("kind", "not-recorded"),
                "basis": record.get("basis", "not-recorded"),
                "claim_type": record.get("claim_type", "not-recorded"),
                "claim_status": record.get("claim_status", "not-recorded"),
                "result_status": _nested(record, "result", "status"),
                "evidence_ids": sorted(
                    item
                    for item in record.get("evidence_ids", [])
                    if isinstance(item, str)
                ),
            }
            records.append(row)
            if row["claim_status"] != "accepted":
                candidates.append(
                    {
                        "path": path,
                        "index": index,
                        "id": row["id"],
                        "reasons": ["validation-record-not-accepted"],
                    }
                )
    return {
        "contracts": sorted(contracts, key=lambda item: item["path"]),
        "validation_records": sorted(
            records, key=lambda item: (item["path"], item["index"])
        ),
        "review_candidates": sorted(
            candidates, key=lambda item: (item["path"], item["index"])
        ),
        "candidate_count": len(candidates),
        "classification_is_not_promotion": True,
    }


def _scope_status(envelope: Any, dimension: str) -> str:
    if not isinstance(envelope, dict):
        return "not-recorded"
    value = envelope.get(dimension)
    if not isinstance(value, dict):
        return "not-recorded" if value is None else "invalid"
    status = value.get("status")
    return status if isinstance(status, str) and status else "not-recorded"


def _is_observation(value: dict[str, Any]) -> bool:
    return (
        value.get("kind") in OBSERVATION_KINDS
        and value.get("observation_version") == "1"
    )


def _record_id(value: dict[str, Any], fallback: int) -> str:
    for key in ("id", "name"):
        if isinstance(value.get(key), str) and value[key]:
            return value[key]
    return f"index-{fallback}"


def _nested(value: dict[str, Any], outer: str, inner: str) -> Any:
    nested = value.get(outer)
    return (
        nested.get(inner, "not-recorded")
        if isinstance(nested, dict)
        else "not-recorded"
    )


def _git(root: Path, arguments: list[str]) -> str:
    result = subprocess.run(
        ["git", *arguments],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise AuditError(f"git {' '.join(arguments)} failed: {detail}")
    return result.stdout


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--ref", default="origin/main")
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    report = audit_ref(args.root, args.ref)
    rendered = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

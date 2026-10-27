#!/usr/bin/env python3
"""Build deterministic research-only scores for the MTH-0186/0187 pilots.

This builder reports separate observed label distributions.  It does not turn
the labels into a quality score, infer promotion, or treat agent-pilot
agreement as human review agreement.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = (
    ROOT / "data/research-review/scoring/mth-0188-agent-review-scoring.json"
)
PILOT_SOURCES = (
    ("mth-0186", "A", ROOT / "data/research-review/pilots/mth-0186.json"),
    ("mth-0187", "B", ROOT / "data/research-review/pilots/mth-0187.json"),
)
SMALL_SAMPLE_THRESHOLD = 5

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.statistical_error_analysis import exact_binomial_interval  # noqa: E402

DIMENSION_CATEGORIES: dict[str, tuple[str, ...]] = {
    "evidence_support": (
        "supported",
        "partially-supported",
        "unsupported",
        "unknown",
        "not-recorded",
    ),
    "claim_type": (
        "fact",
        "inference",
        "hypothesis",
        "analogy",
        "unknown",
        "not-recorded",
    ),
    "scope_completeness": (
        "complete",
        "partial",
        "incomplete",
        "unknown",
        "not-recorded",
    ),
    "false_link": ("false", "not-false", "unknown", "not-recorded"),
    "usefulness": (
        "useful",
        "somewhat-useful",
        "not-useful",
        "unknown",
        "not-recorded",
    ),
    "counterexample_awareness": (
        "aware",
        "unaware",
        "not-applicable",
        "unknown",
        "not-recorded",
    ),
    "abstention": ("abstained", "not-abstained", "unknown", "not-recorded"),
    "reviewer_effort": ("low", "medium", "high", "unknown", "not-recorded"),
}


class ScoringError(ValueError):
    """Raised when a source pilot cannot be scored without guessing."""


def canonical_digest(value: Any) -> str:
    """Return a stable digest for JSON-compatible data."""

    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ScoringError(f"{path} must contain an object")
    return value


def _warnings(count: int) -> list[str]:
    if 0 < count < SMALL_SAMPLE_THRESHOLD:
        return [f"small sample: denominator {count} is below {SMALL_SAMPLE_THRESHOLD}"]
    return []


def _metric(
    name: str,
    numerator: int,
    denominator: int,
    *,
    reason: str,
) -> dict[str, Any]:
    if not 0 <= numerator <= denominator:
        raise ScoringError("metric counts must satisfy 0 <= numerator <= denominator")
    measured = denominator > 0
    return {
        "name": name,
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if measured else None,
        "status": "measured" if measured else "not-evaluated",
        "reason": reason if measured else f"No evaluated rows: {reason}",
        "interval": exact_binomial_interval(numerator, denominator),
        "warnings": _warnings(denominator),
    }


def _dimension_set(rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Report each label category independently, without an aggregate score."""

    result: dict[str, Any] = {"observed_count": len(rows), "dimensions": {}}
    for dimension, categories in DIMENSION_CATEGORIES.items():
        values = [row["labels"][dimension] for row in rows]
        if any(value not in categories for value in values):
            raise ScoringError(f"invalid {dimension} label")
        result["dimensions"][dimension] = {
            "categories": {
                category: _metric(
                    f"{dimension}:{category}",
                    values.count(category),
                    len(values),
                    reason=f"Observed {dimension} label is {category}.",
                )
                for category in categories
            },
            "warnings": _warnings(len(values)),
        }
    return result


def _slices(rows: Sequence[Mapping[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        groups[str(row[key])].append(row)
    return [
        {"slice": label, **_dimension_set(groups[label])} for label in sorted(groups)
    ]


def _copy_observation(
    pilot_id: str,
    packet_label: str,
    pilot_digest: str,
    study_packet_digest: str,
    assignment_digest: Mapping[str, Any],
    record: Mapping[str, Any],
) -> dict[str, Any]:
    partition = record["partition"]
    if partition == "holdout":
        raise ScoringError("holdout rows must not be included in scoring")
    if partition not in {"train", "evaluation"}:
        raise ScoringError(f"unsupported partition: {partition}")
    if assignment_digest["task_id"] != record["task_id"]:
        raise ScoringError("assignment and review task IDs differ")
    return {
        "pilot_id": pilot_id,
        "packet_label": packet_label,
        "pilot_digest": pilot_digest,
        "study_packet_digest": study_packet_digest,
        "task_id": record["task_id"],
        "assignment_id": record["assignment_id"],
        "domain_id": record["domain_id"],
        "partition": partition,
        "candidate_statement": record["candidate_statement"],
        "candidate_claim_type": record["candidate_claim_type"],
        "candidate_digest": record["candidate_digest"],
        "evidence_ids": record["evidence_ids"],
        "evidence_excerpt_digests": record["evidence_excerpt_digests"],
        "source_ids": record["source_ids"],
        "negative_knowledge_refs": record["negative_knowledge_refs"],
        "negative_knowledge_digests": record["negative_knowledge_digests"],
        "scope_context": record["scope_context"],
        "locality": record["locality"],
        "labels": record["labels"],
        "timing": record["timing"],
    }


def _load_observations() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    sources: list[dict[str, Any]] = []
    for pilot_id, packet_label, path in PILOT_SOURCES:
        pilot = _read(path)
        if pilot["pilot_id"] != pilot_id or pilot["packet_label"] != packet_label:
            raise ScoringError(f"unexpected pilot identity in {path}")
        if pilot["record_kind"] != "agent-review-pilot":
            raise ScoringError(f"unexpected record kind in {path}")
        if not pilot["research_only"] or not pilot["non_canonical"]:
            raise ScoringError(f"pilot is not research-only and non-canonical: {path}")
        provenance = pilot["provenance"]
        if (
            provenance["reviewer_kind"] != "agent"
            or provenance["human_review"] is not False
            or provenance["mode"] != "agent-review-pilot"
        ):
            raise ScoringError(f"invalid provenance in {path}")
        assignment_digests = {
            item["task_id"]: item for item in pilot["assignment_digests"]
        }
        packet_digest = pilot.get("study_packet_digest", pilot.get("packet_digest"))
        if not packet_digest:
            raise ScoringError(f"missing packet digest in {path}")
        pilot_digest = file_digest(path)
        sources.append(
            {
                "pilot_id": pilot_id,
                "packet_label": packet_label,
                "artifact": str(path.relative_to(ROOT)),
                "digest": pilot_digest,
                "study_packet_digest": packet_digest,
                "assignment_digests": pilot["assignment_digests"],
                "run_timing": pilot["run_timing"],
            }
        )
        for record in pilot["review_records"]:
            task_id = record["task_id"]
            if task_id not in assignment_digests:
                raise ScoringError(f"missing assignment digest for {task_id}")
            rows.append(
                _copy_observation(
                    pilot_id,
                    packet_label,
                    pilot_digest,
                    packet_digest,
                    assignment_digests[task_id],
                    record,
                )
            )
    return rows, sources


def _agreement_rows(rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_task: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[row["task_id"]].append(row)
    result = []
    for task_id, pair in sorted(by_task.items()):
        if len(pair) != 2 or {row["packet_label"] for row in pair} != {"A", "B"}:
            raise ScoringError(f"task {task_id} does not have exactly one A/B pair")
        first, second = sorted(pair, key=lambda row: row["packet_label"])
        if first["candidate_digest"] != second["candidate_digest"]:
            raise ScoringError(f"candidate digest mismatch for paired task {task_id}")
        result.append(
            {
                "task_id": task_id,
                "domain_id": first["domain_id"],
                "candidate_digest": first["candidate_digest"],
                "pilot_labels": {
                    "A": first["labels"],
                    "B": second["labels"],
                },
                "dimensions": {
                    dimension: {
                        "status": (
                            "agree"
                            if first["labels"][dimension] == second["labels"][dimension]
                            else "disagree"
                        ),
                        "agent_pilot_only": True,
                    }
                    for dimension in DIMENSION_CATEGORIES
                },
            }
        )
    return result


def _agreement_set(pairs: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {"paired_count": len(pairs), "dimensions": {}}
    for dimension in DIMENSION_CATEGORIES:
        statuses = [pair["dimensions"][dimension]["status"] for pair in pairs]
        result["dimensions"][dimension] = {
            "categories": {
                status: _metric(
                    f"reviewer_agreement:{dimension}:{status}",
                    statuses.count(status),
                    len(statuses),
                    reason=(
                        "A and B agent-pilot labels agree"
                        if status == "agree"
                        else "A and B agent-pilot labels disagree"
                    ),
                )
                for status in ("agree", "disagree")
            },
            "warnings": _warnings(len(statuses)),
        }
    return result


def build_artifact() -> dict[str, Any]:
    """Build the checked-in scoring artifact from the two accepted pilots."""

    rows, sources = _load_observations()
    pairs = _agreement_rows(rows)
    overall = _dimension_set(rows)
    return {
        "schema_version": "1.0",
        "scoring_id": "mth-0188-agent-review-scoring",
        "record_kind": "agent-review-scoring",
        "research_only": True,
        "non_canonical": True,
        "purpose": (
            "Separate deterministic observations from the two enriched packet "
            "agent-review pilots."
        ),
        "provenance": {
            "mode": "agent-review-pilot",
            "reviewer_kind": "agent",
            "human_review": False,
            "pilot_ids": ["mth-0186", "mth-0187"],
            "source_artifacts": [source["artifact"] for source in sources],
        },
        "evaluation_boundary": {
            "included_partitions": ["train", "evaluation"],
            "holdout_included": False,
            "observed_row_count": len(rows),
            "pilot_count": len(sources),
            "reason": (
                "Only rows present in the two accepted pilot artifacts are scored; "
                "no holdout payload is read or copied."
            ),
        },
        "sources": sources,
        "observations": rows,
        "scores": {
            "overall": overall,
            "by_pilot": [
                {
                    "slice": source["pilot_id"],
                    **_dimension_set(
                        [row for row in rows if row["pilot_id"] == source["pilot_id"]]
                    ),
                }
                for source in sources
            ],
            "by_task": _slices(rows, "task_id"),
            "by_domain": _slices(rows, "domain_id"),
        },
        "agreement": {
            "observation_kind": "agent-pilot-agreement",
            "reviewer_kind": "agent",
            "human_review": False,
            "pilot_pair": ["mth-0186", "mth-0187"],
            "status": "observed",
            "paired_rows": pairs,
            "overall": _agreement_set(pairs),
            "by_task": [
                {
                    "slice": pair["task_id"],
                    "paired_count": 1,
                    "dimensions": _agreement_set([pair])["dimensions"],
                    "warnings": _warnings(1),
                }
                for pair in pairs
            ],
            "by_domain": [
                {
                    "slice": domain,
                    **_agreement_set(
                        [pair for pair in pairs if pair["domain_id"] == domain]
                    ),
                }
                for domain in sorted({pair["domain_id"] for pair in pairs})
            ],
            "non_claims": [
                "This is agreement between two agent-review pilot runs only.",
                "It is not human reviewer agreement and does not estimate human "
                "reliability.",
            ],
        },
        "small_sample_policy": {
            "threshold": SMALL_SAMPLE_THRESHOLD,
            "warning": (
                "Every measured denominator below the threshold receives a small-"
                "sample warning; observations remain included."
            ),
        },
        "non_claims": [
            "No aggregate quality score is computed.",
            "Observed labels do not imply promotion or canonical-card validity.",
            "No human evidence, human review, holdout data, or production record "
            "is included.",
            "Agent timing is observed wall-clock timing with the source pilots' "
            "stated scope.",
        ],
        "promotion_boundary": {
            "promotion_decision": "not-determined",
            "review_implies_promotion": False,
            "canonical_cards_written": False,
            "production_records_written": False,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_artifact(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

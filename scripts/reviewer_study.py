"""Generate and safely import a blinded, research-only reviewer study.

The generator creates empty review packets.  It never invents reviewer labels,
timings, agreement, adjudication, or promotion decisions.  Review records can
later be validated and summarized without writing canonical cards or other
production data.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable

TASK = "MTH-0175"
SCHEMA_VERSION = "1.0"
STUDY_KIND = "blinded_reviewer_study"
ANALYSIS_VERSION = "mth-0175-reviewer-study-v1"
MIN_REVIEWERS = 2
REVIEW_DIMENSIONS = (
    "evidence_support",
    "claim_type",
    "scope_completeness",
    "false_link",
    "counterexample_awareness",
    "usefulness",
    "abstention",
    "reviewer_effort",
)
LABEL_VALUES = {
    "evidence_support": (
        "supported",
        "partially-supported",
        "unsupported",
        "unknown",
    ),
    "claim_type": ("fact", "inference", "hypothesis", "analogy", "unknown"),
    "scope_completeness": ("complete", "partial", "incomplete", "unknown"),
    "false_link": ("false", "not-false", "unknown"),
    "counterexample_awareness": ("aware", "unaware", "not-applicable", "unknown"),
    "usefulness": ("useful", "somewhat-useful", "not-useful", "unknown"),
    "abstention": ("abstained", "not-abstained", "unknown"),
    "reviewer_effort": ("low", "medium", "high", "unknown"),
}
MISSING = "not-recorded"
ADJUDICATION_STATUSES = ("open", "resolved", "abstained")
OPAQUE_WORDS = (
    "amber",
    "birch",
    "cedar",
    "cobalt",
    "coral",
    "dune",
    "fern",
    "flint",
    "frost",
    "hazel",
    "ivory",
    "jade",
    "juniper",
    "lark",
    "linen",
    "maple",
    "mist",
    "moss",
    "olive",
    "onyx",
    "opal",
    "pine",
    "quartz",
    "reed",
    "river",
    "sable",
    "slate",
    "spruce",
    "stone",
    "thyme",
    "willow",
    "wren",
)


class StudyError(ValueError):
    """Raised when a study or later review import is unsafe or malformed."""


def canonical_digest(value: Any) -> str:
    """Return a stable digest for JSON-compatible input."""

    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def build_study(
    tasks: Iterable[dict[str, Any]],
    *,
    study_id: str,
    assignment_seed: str,
    reviewer_count: int = MIN_REVIEWERS,
    source_ref: str = "provided-input",
    source_revision: str = "not-recorded",
) -> dict[str, Any]:
    """Build deterministic balanced packets for independent opaque reviewers.

    Every reviewer receives every task, which preserves an overlap set for
    disagreement retention.  Tasks must be balanced across domains.  Within
    each packet, a seeded deterministic shuffle hides domain/task order without
    changing the task set.  Complexity is O(R * T) time and space.
    """

    if not _non_empty(study_id) or not _non_empty(assignment_seed):
        raise StudyError("study_id and assignment_seed must be non-empty strings")
    if not isinstance(reviewer_count, int) or isinstance(reviewer_count, bool):
        raise StudyError("reviewer_count must be an integer")
    if reviewer_count < MIN_REVIEWERS:
        raise StudyError(f"at least {MIN_REVIEWERS} independent reviewers are required")
    normalized_tasks = _validate_tasks(tasks)
    domain_counts = _domain_counts(normalized_tasks)
    if len(set(domain_counts.values())) != 1:
        raise StudyError("tasks must be balanced: every domain needs the same count")

    reviewer_keys = [
        _opaque_key(assignment_seed, index) for index in range(reviewer_count)
    ]
    task_digest = canonical_digest(normalized_tasks)
    packets = []
    for reviewer_key in reviewer_keys:
        ordered = list(normalized_tasks)
        random.Random(_shuffle_seed(assignment_seed, reviewer_key)).shuffle(ordered)
        assignments = [
            {
                "assignment_id": _assignment_id(
                    study_id, reviewer_key, task["task_id"]
                ),
                "reviewer_key": reviewer_key,
                "task_id": task["task_id"],
                "domain_id": task["domain_id"],
                "order": order,
                "task": task,
            }
            for order, task in enumerate(ordered, start=1)
        ]
        packets.append(
            {
                "packet_id": _packet_id(study_id, reviewer_key),
                "reviewer_key": reviewer_key,
                "instructions": _instructions(),
                "assignments": assignments,
                "review_records": [],
            }
        )

    return {
        "study_kind": STUDY_KIND,
        "schema_version": SCHEMA_VERSION,
        "analysis_version": ANALYSIS_VERSION,
        "study_id": study_id,
        "research_only": True,
        "purpose": (
            "Measure independent evidence-bounded review judgments while retaining "
            "missing values, unknown values, and disagreements for later study."
        ),
        "reproducibility": {
            "source_ref": source_ref,
            "source_revision": source_revision,
            "task_set_digest": task_digest,
            "assignment_seed": assignment_seed,
            "generated_at": MISSING,
        },
        "reviewer_pool": {
            "count": reviewer_count,
            "independent": True,
            "identity_visibility": "opaque",
            "reviewer_keys": reviewer_keys,
        },
        "balance": {
            "balanced": True,
            "domain_task_counts": dict(sorted(domain_counts.items())),
            "tasks_per_reviewer": len(normalized_tasks),
            "overlap_policy": "all-reviewers-review-all-tasks",
        },
        "instructions": _instructions(),
        "rubric": _rubric(),
        "timing": {
            "required_for_submitted_record": True,
            "fields": ["started_at", "ended_at", "elapsed_seconds"],
            "missing_value": MISSING,
            "policy": (
                "Record observed timestamps and/or elapsed seconds; never estimate "
                "or backfill them."
            ),
        },
        "packets": packets,
        "review_records": [],
        "disagreement_records": [],
        "adjudications": [],
        "adjudication_protocol": _adjudication_protocol(),
        "results": {
            "status": "not-started",
            "agreement": {"status": "not-determined"},
            "promotion_decision": "not-determined",
        },
        "promotion_boundary": {
            "promotion_decision": "not-determined",
            "review_implies_promotion": False,
            "adjudication_implies_promotion": False,
            "canonical_cards_written": False,
            "production_records_written": False,
        },
    }


def validate_study(study: dict[str, Any]) -> None:
    """Validate a generated study before any review records are imported."""

    if not isinstance(study, dict):
        raise StudyError("study must be a JSON object")
    for key, expected in (
        ("study_kind", STUDY_KIND),
        ("schema_version", SCHEMA_VERSION),
        ("research_only", True),
    ):
        if study.get(key) != expected:
            raise StudyError(f"{key} must equal {expected!r}")
    pool = _object(study, "reviewer_pool")
    keys = pool.get("reviewer_keys")
    if (
        not isinstance(keys, list)
        or len(keys) < MIN_REVIEWERS
        or len(keys) != len(set(keys))
        or any(not _non_empty(key) for key in keys)
    ):
        raise StudyError("reviewer_pool must contain unique opaque reviewer keys")
    if pool.get("count") != len(keys) or pool.get("identity_visibility") != "opaque":
        raise StudyError("reviewer_pool count or identity policy is invalid")
    reproducibility = _object(study, "reproducibility")
    if not _non_empty(reproducibility.get("assignment_seed")):
        raise StudyError("reproducibility.assignment_seed is required")
    packets = study.get("packets")
    if not isinstance(packets, list) or len(packets) != len(keys):
        raise StudyError("one packet is required per reviewer key")
    assignments_by_reviewer: dict[str, dict[str, str]] = {}
    expected_tasks: set[str] | None = None
    for packet in packets:
        _validate_packet(packet, keys)
        reviewer_key = packet["reviewer_key"]
        assignments = packet["assignments"]
        task_map = {item["task_id"]: item["domain_id"] for item in assignments}
        if reviewer_key in assignments_by_reviewer:
            raise StudyError("reviewer packets must be unique")
        assignments_by_reviewer[reviewer_key] = task_map
        if expected_tasks is None:
            expected_tasks = set(task_map)
        elif set(task_map) != expected_tasks:
            raise StudyError("reviewer packets must contain the same task set")
    if expected_tasks is None or not expected_tasks:
        raise StudyError("study must contain at least one task")
    _validate_balance(study, packets)
    if study.get("results", {}).get("promotion_decision") != "not-determined":
        raise StudyError("promotion_decision must remain not-determined")


def validate_review_records(
    study: dict[str, Any],
    records: Iterable[dict[str, Any]],
    adjudications: Iterable[dict[str, Any]] = (),
) -> dict[str, Any]:
    """Validate real records and return a non-promoting research summary.

    Records are copied and normalized for reporting.  No record is silently
    added for an unreviewed assignment; absent labels become ``not-recorded``
    while an explicit ``unknown`` remains ``unknown``.
    """

    validate_study(study)
    packet_map = {packet["reviewer_key"]: packet for packet in study["packets"]}
    assignments = {
        (packet["reviewer_key"], assignment["task_id"]): assignment
        for packet in study["packets"]
        for assignment in packet["assignments"]
    }
    normalized = []
    seen: set[tuple[str, str]] = set()
    review_ids: set[str] = set()
    for record in records:
        _validate_record(record, packet_map, assignments, seen, review_ids)
        reviewer_key = record["reviewer_key"]
        task_id = record["task_id"]
        assignment = assignments[(reviewer_key, task_id)]
        labels = {
            dimension: record.get("labels", {}).get(dimension, MISSING)
            for dimension in REVIEW_DIMENSIONS
        }
        timing = record.get("timing", {})
        normalized.append(
            {
                "review_id": record["review_id"],
                "reviewer_key": reviewer_key,
                "task_id": task_id,
                "domain_id": assignment["domain_id"],
                "labels": labels,
                "timing": {
                    field: timing.get(field, MISSING)
                    for field in ("started_at", "ended_at", "elapsed_seconds")
                },
                "notes": record.get("notes", MISSING),
            }
        )
    normalized.sort(key=lambda item: item["review_id"])
    disagreements = _disagreements(normalized)
    adjudication_records = _validate_adjudications(adjudications, disagreements)
    coverage = _coverage(study, normalized)
    return {
        "task": TASK,
        "analysis_version": ANALYSIS_VERSION,
        "study_id": study["study_id"],
        "records": normalized,
        "coverage": coverage,
        "disagreement_records": disagreements,
        "adjudications": adjudication_records,
        "agreement": {"status": "not-determined"},
        "promotion_decision": "not-determined",
        "mutation_performed": False,
        "canonical_cards_written": False,
    }


def _validate_tasks(tasks: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    values = list(tasks)
    if not values:
        raise StudyError("at least one task is required")
    result = []
    ids: set[str] = set()
    for task in values:
        if not isinstance(task, dict):
            raise StudyError("every task must be an object")
        for key in ("task_id", "domain_id", "prompt"):
            if not _non_empty(task.get(key)):
                raise StudyError(f"task.{key} must be a non-empty string")
        if task["task_id"] in ids:
            raise StudyError("task_id values must be unique")
        ids.add(task["task_id"])
        candidate_refs = task.get("candidate_refs", [])
        source_refs = task.get("source_refs", [])
        for key, values_for_key in (
            ("candidate_refs", candidate_refs),
            ("source_refs", source_refs),
        ):
            if not isinstance(values_for_key, list) or any(
                not _non_empty(value) for value in values_for_key
            ):
                raise StudyError(f"task.{key} must be a list of non-empty strings")
        result.append(
            {
                "task_id": task["task_id"],
                "domain_id": task["domain_id"],
                "prompt": task["prompt"],
                "candidate_refs": list(candidate_refs),
                "source_refs": list(source_refs),
            }
        )
    return sorted(result, key=lambda item: item["task_id"])


def _validate_packet(packet: Any, reviewer_keys: list[str]) -> None:
    if not isinstance(packet, dict):
        raise StudyError("packet must be an object")
    reviewer_key = packet.get("reviewer_key")
    if reviewer_key not in reviewer_keys:
        raise StudyError("packet has an unknown reviewer key")
    assignments = packet.get("assignments")
    if not isinstance(assignments, list) or not assignments:
        raise StudyError("packet assignments must be a non-empty list")
    orders = [item.get("order") for item in assignments if isinstance(item, dict)]
    if orders != list(range(1, len(assignments) + 1)):
        raise StudyError("packet assignment order must be contiguous")
    for assignment in assignments:
        if not isinstance(assignment, dict):
            raise StudyError("assignment must be an object")
        if assignment.get("reviewer_key") != reviewer_key:
            raise StudyError("assignment reviewer key mismatch")
        task = assignment.get("task")
        if not isinstance(task, dict) or task.get("task_id") != assignment.get(
            "task_id"
        ):
            raise StudyError("assignment task snapshot is invalid")


def _validate_balance(study: dict[str, Any], packets: list[dict[str, Any]]) -> None:
    balance = _object(study, "balance")
    expected = balance.get("domain_task_counts")
    if not isinstance(expected, dict) or not expected:
        raise StudyError("balance.domain_task_counts is required")
    for packet in packets:
        counts = _domain_counts(packet["assignments"], key="domain_id")
        if counts != expected:
            raise StudyError("each reviewer packet must be balanced by domain")


def _validate_record(
    record: Any,
    packet_map: dict[str, dict[str, Any]],
    assignments: dict[tuple[str, str], dict[str, Any]],
    seen: set[tuple[str, str]],
    review_ids: set[str],
) -> None:
    if not isinstance(record, dict):
        raise StudyError("review record must be an object")
    for key in ("review_id", "reviewer_key", "task_id"):
        if not _non_empty(record.get(key)):
            raise StudyError(f"review record.{key} is required")
    review_id = record["review_id"]
    if review_id in review_ids:
        raise StudyError("review_id values must be unique")
    review_ids.add(review_id)
    pair = (record["reviewer_key"], record["task_id"])
    if record["reviewer_key"] not in packet_map or pair not in assignments:
        raise StudyError("review record references an unassigned task")
    if pair in seen:
        raise StudyError("one review record per reviewer/task is allowed")
    seen.add(pair)
    labels = record.get("labels", {})
    if not isinstance(labels, dict):
        raise StudyError("review record.labels must be an object")
    for dimension, value in labels.items():
        if dimension not in REVIEW_DIMENSIONS:
            raise StudyError(f"unknown rubric dimension: {dimension}")
        if value not in LABEL_VALUES[dimension]:
            raise StudyError(f"invalid {dimension} label: {value!r}")
    timing = record.get("timing")
    if not isinstance(timing, dict):
        raise StudyError("review record.timing must be an object")
    if not any(
        timing.get(field) not in (None, MISSING)
        for field in ("started_at", "ended_at", "elapsed_seconds")
    ):
        raise StudyError(
            "review record must include an observed timestamp or elapsed_seconds"
        )
    for field in ("started_at", "ended_at"):
        value = timing.get(field)
        if value is not None and value != MISSING:
            if not isinstance(value, str) or not _parse_timestamp(value):
                raise StudyError(f"timing.{field} must be an ISO-8601 timestamp")
    elapsed = timing.get("elapsed_seconds")
    if (
        elapsed is not None
        and elapsed != MISSING
        and (
            isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or elapsed < 0
        )
    ):
        raise StudyError("timing.elapsed_seconds must be a non-negative number")
    if timing.get("started_at") not in (None, MISSING) and timing.get(
        "ended_at"
    ) not in (
        None,
        MISSING,
    ):
        try:
            reversed_order = _parse_timestamp(timing["ended_at"]) < _parse_timestamp(
                timing["started_at"]
            )
        except TypeError as error:
            raise StudyError(
                "timing timestamps must use comparable timezone formats"
            ) from error
        if reversed_order:
            raise StudyError("timing.ended_at cannot precede timing.started_at")


def _validate_adjudications(
    records: Iterable[dict[str, Any]], disagreements: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    disagreement_tasks = {item["task_id"] for item in disagreements}
    output = []
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict) or not _non_empty(record.get("task_id")):
            raise StudyError("adjudication requires a task_id")
        task_id = record["task_id"]
        if task_id in seen:
            raise StudyError("one adjudication record per task is allowed")
        seen.add(task_id)
        status = record.get("status")
        if status not in ADJUDICATION_STATUSES:
            raise StudyError("invalid adjudication status")
        if task_id not in disagreement_tasks:
            raise StudyError("adjudication requires a retained disagreement")
        if status == "resolved" and not _non_empty(record.get("rationale")):
            raise StudyError("resolved adjudication requires a rationale")
        output.append(
            {
                "task_id": task_id,
                "status": status,
                "outcome": record.get("outcome", MISSING),
                "rationale": record.get("rationale", MISSING),
                "adjudicator_key": record.get("adjudicator_key", MISSING),
            }
        )
    return sorted(output, key=lambda item: item["task_id"])


def _disagreements(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[record["task_id"]].append(record)
    disagreements = []
    for task_id, task_records in sorted(grouped.items()):
        if len(task_records) < 2:
            continue
        for dimension in REVIEW_DIMENSIONS:
            values = {record["labels"][dimension] for record in task_records}
            if len(values) > 1:
                disagreements.append(
                    {
                        "task_id": task_id,
                        "domain_id": task_records[0]["domain_id"],
                        "dimension": dimension,
                        "reviewer_keys": sorted(
                            record["reviewer_key"] for record in task_records
                        ),
                        "values": sorted(values),
                    }
                )
    return disagreements


def _coverage(study: dict[str, Any], records: list[dict[str, Any]]) -> dict[str, Any]:
    reviewed = {(record["reviewer_key"], record["task_id"]) for record in records}
    result = {}
    for packet in sorted(study["packets"], key=lambda item: item["reviewer_key"]):
        key = packet["reviewer_key"]
        task_ids = [assignment["task_id"] for assignment in packet["assignments"]]
        result[key] = {
            "assigned_count": len(task_ids),
            "reviewed_count": sum((key, task_id) in reviewed for task_id in task_ids),
            "unreviewed_task_ids": sorted(
                task_id for task_id in task_ids if (key, task_id) not in reviewed
            ),
        }
    return result


def _domain_counts(
    values: Iterable[dict[str, Any]], key: str = "domain_id"
) -> dict[str, int]:
    counts: defaultdict[str, int] = defaultdict(int)
    for value in values:
        counts[value[key]] += 1
    return dict(sorted(counts.items()))


def _rubric() -> dict[str, Any]:
    return {
        "version": "reviewer-study-rubric-v1",
        "missing_value": MISSING,
        "unknown_value": "unknown",
        "dimensions": [
            {
                "id": dimension,
                "allowed_values": list(values),
                "question": _rubric_question(dimension),
            }
            for dimension, values in LABEL_VALUES.items()
        ],
    }


def _rubric_question(dimension: str) -> str:
    return {
        "evidence_support": "How well do the supplied records support the item?",
        "claim_type": "What claim type best describes the item?",
        "scope_completeness": "Is the stated scope sufficiently complete?",
        "false_link": "Does the item contain a false or unsupported link?",
        "counterexample_awareness": (
            "Does the item account for a relevant counterexample?"
        ),
        "usefulness": "Would this item help a bounded architecture review?",
        "abstention": "Did you abstain because the evidence was insufficient?",
        "reviewer_effort": "What effort level did this review require?",
    }[dimension]


def _instructions() -> list[str]:
    return [
        "Use only the evidence and task material in this packet.",
        "Review independently; do not exchange labels or reviewer identities.",
        "Record unknown when the material does not support a judgment.",
        "Leave a label absent when you did not record it; absent is not unknown.",
        "Record observed timing only; do not estimate or backfill elapsed time.",
        "Retain a short note for a material disagreement or abstention when useful.",
        "These judgments are research observations and do not promote any card.",
    ]


def _adjudication_protocol() -> dict[str, Any]:
    return {
        "trigger": "one or more retained dimension disagreements for a task",
        "order": [
            "Preserve every independent review and its original timing.",
            "Invite an adjudicator who did not submit the independent labels.",
            "Review the cited evidence and scope, then record open, resolved, or "
            "abstained.",
            "Require a rationale for resolved outcomes and preserve unresolved cases.",
        ],
        "allowed_statuses": list(ADJUDICATION_STATUSES),
        "outcome_is_not_promotion": True,
    }


def _opaque_key(seed: str, index: int) -> str:
    digest = hashlib.sha256(f"{seed}\0reviewer\0{index}".encode()).digest()
    words = (OPAQUE_WORDS[byte & 31] for byte in digest[:16])
    return "blind-seat-" + "-".join(words)


def _shuffle_seed(seed: str, reviewer_key: str) -> int:
    return int(hashlib.sha256(f"{seed}\0{reviewer_key}".encode()).hexdigest(), 16)


def _assignment_id(study_id: str, reviewer_key: str, task_id: str) -> str:
    return (
        "assignment-"
        + hashlib.sha256(f"{study_id}\0{reviewer_key}\0{task_id}".encode()).hexdigest()[
            :24
        ]
    )


def _packet_id(study_id: str, reviewer_key: str) -> str:
    return (
        "packet-"
        + hashlib.sha256(f"{study_id}\0{reviewer_key}".encode()).hexdigest()[:24]
    )


def _object(value: dict[str, Any], key: str) -> dict[str, Any]:
    result = value.get(key)
    if not isinstance(result, dict):
        raise StudyError(f"{key} must be an object")
    return result


def _non_empty(value: Any) -> bool:
    return isinstance(value, str) and bool(value)


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as error:
        raise StudyError(f"invalid ISO-8601 timestamp: {value!r}") from error


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise StudyError(f"cannot read JSON {path}: {error}") from error


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    generate = subparsers.add_parser("generate")
    generate.add_argument("input", type=Path, help="JSON object with a tasks list")
    generate.add_argument("--output", type=Path, required=True)
    generate.add_argument("--study-id", required=True)
    generate.add_argument("--assignment-seed", required=True)
    generate.add_argument("--reviewer-count", type=int, default=MIN_REVIEWERS)
    generate.add_argument("--source-ref", default="provided-input")
    generate.add_argument("--source-revision", default="not-recorded")
    validate = subparsers.add_parser("validate")
    validate.add_argument("study", type=Path)
    validate.add_argument("--reviews", type=Path)
    validate.add_argument("--adjudications", type=Path)
    validate.add_argument("--output", type=Path)
    args = parser.parse_args()

    if args.command == "generate":
        input_value = _read_json(args.input)
        tasks = input_value.get("tasks") if isinstance(input_value, dict) else None
        if not isinstance(tasks, list):
            raise StudyError("input must contain a tasks list")
        result = build_study(
            tasks,
            study_id=args.study_id,
            assignment_seed=args.assignment_seed,
            reviewer_count=args.reviewer_count,
            source_ref=args.source_ref,
            source_revision=args.source_revision,
        )
    else:
        result_study = _read_json(args.study)
        if args.reviews:
            reviews = _read_json(args.reviews)
            if not isinstance(reviews, list):
                raise StudyError("reviews input must be a list")
            adjudications = _read_json(args.adjudications) if args.adjudications else []
            if not isinstance(adjudications, list):
                raise StudyError("adjudications input must be a list")
            result = validate_review_records(result_study, reviews, adjudications)
        else:
            validate_study(result_study)
            result = {
                "study_id": result_study["study_id"],
                "valid": True,
                "review_records": [],
                "promotion_decision": "not-determined",
            }
    rendered = json.dumps(result, indent=2, ensure_ascii=False) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

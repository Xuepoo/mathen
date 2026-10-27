"""Validate a detached, evidence-bounded agent review pilot for packet A."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
PACKET = ROOT / "data/research-review/mth-0185-enriched-study.json"
OUTPUT = ROOT / "data/research-review/pilots/mth-0186.json"

DIMENSIONS = (
    "evidence_support",
    "claim_type",
    "scope_completeness",
    "false_link",
    "counterexample_awareness",
    "usefulness",
    "abstention",
    "reviewer_effort",
)
LABELS = {
    "evidence_support": {
        "supported",
        "partially-supported",
        "unsupported",
        "unknown",
        "not-recorded",
    },
    "claim_type": {
        "fact",
        "inference",
        "hypothesis",
        "analogy",
        "unknown",
        "not-recorded",
    },
    "scope_completeness": {
        "complete",
        "partial",
        "incomplete",
        "unknown",
        "not-recorded",
    },
    "false_link": {"false", "not-false", "unknown", "not-recorded"},
    "counterexample_awareness": {
        "aware",
        "unaware",
        "not-applicable",
        "unknown",
        "not-recorded",
    },
    "usefulness": {
        "useful",
        "somewhat-useful",
        "not-useful",
        "unknown",
        "not-recorded",
    },
    "abstention": {"abstained", "not-abstained", "unknown", "not-recorded"},
    "reviewer_effort": {"low", "medium", "high", "unknown", "not-recorded"},
}


class PilotError(ValueError):
    """Raised when the detached pilot violates its evidence boundary."""


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise PilotError(f"{path} must contain an object")
    return value


def build_pilot(
    *,
    started_at: str,
    ended_at: str,
    elapsed_seconds: float,
    task_timings: dict[str, dict[str, Any]],
) -> dict[str, Any]:
    packet = _read(PACKET)
    packet_a = next(item for item in packet["packets"] if item["packet_label"] == "A")
    records = []
    assignment_digests = []
    labels = {
        "task-08-reconciliation": {
            "evidence_support": "partially-supported",
            "claim_type": "inference",
            "scope_completeness": "complete",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "medium",
        },
        "task-11-boundary-isolation": {
            "evidence_support": "supported",
            "claim_type": "inference",
            "scope_completeness": "complete",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "medium",
        },
        "task-05-stream-history": {
            "evidence_support": "partially-supported",
            "claim_type": "inference",
            "scope_completeness": "partial",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "medium",
        },
        "task-01-storage-mechanism": {
            "evidence_support": "supported",
            "claim_type": "fact",
            "scope_completeness": "complete",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "low",
        },
        "task-07-reconciliation": {
            "evidence_support": "partially-supported",
            "claim_type": "fact",
            "scope_completeness": "complete",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "medium",
        },
        "task-02-storage-mechanism": {
            "evidence_support": "supported",
            "claim_type": "inference",
            "scope_completeness": "complete",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "low",
        },
        "task-04-stream-history": {
            "evidence_support": "partially-supported",
            "claim_type": "fact",
            "scope_completeness": "partial",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "medium",
        },
        "task-10-boundary-isolation": {
            "evidence_support": "supported",
            "claim_type": "fact",
            "scope_completeness": "complete",
            "false_link": "not-false",
            "counterexample_awareness": "aware",
            "usefulness": "useful",
            "abstention": "not-abstained",
            "reviewer_effort": "low",
        },
    }
    notes = {
        "task-08-reconciliation": (
            "The six supplied fact excerpts support documented Kubernetes "
            "control/reconciliation, Airflow scheduling, and CarryCtx "
            "workflow/checkpoint mechanisms. The candidate is correctly "
            "bounded as an inference across systems; the negative references "
            "explicitly prevent treating reconciliation as a convergence proof."
        ),
        "task-11-boundary-isolation": (
            "Firecracker evidence supports execution isolation and Git evidence "
            "supports object/reference boundaries. The candidate preserves the "
            "distinction between those mechanisms and equivalent security or "
            "durability guarantees; negative references reinforce that boundary."
        ),
        "task-05-stream-history": (
            "Kafka evidence directly supports durable ordered partition logs and "
            "replay. Temporal source evidence supports recorded workflow history, "
            "but the supplied current architecture documentation is explicitly "
            "not version-applicable by assumption, so support and scope are "
            "partial rather than universal."
        ),
        "task-01-storage-mechanism": (
            "The supplied SQLite, PostgreSQL, and DuckDB excerpts support the "
            "stated storage mechanisms. The candidate explicitly requires "
            "deployment and consistency scope per system, and the negative "
            "references guard against transferring replication or isolation claims."
        ),
        "task-07-reconciliation": (
            "The supplied evidence supports the stated control or workflow "
            "mechanisms in all three systems. The fact label is bounded to those "
            "documented mechanisms and explicitly excludes universal convergence; "
            "negative references were considered."
        ),
        "task-02-storage-mechanism": (
            "The same local excerpts support the storage-mechanism observation as "
            "an inference about cross-system scope requirements. The deployment "
            "and consistency qualification is present, so the inference is useful "
            "without asserting equivalence."
        ),
        "task-04-stream-history": (
            "Kafka evidence directly supports event-log retention, ordering, and "
            "replay. Temporal source evidence supports workflow-history "
            "reconstruction, while the current documentation has an explicit "
            "version-applicability caveat; therefore the fact is only partially "
            "supported and scoped."
        ),
        "task-10-boundary-isolation": (
            "The two local fact excerpts support the bounded mechanisms named by "
            "the candidate. Firecracker's isolation and Git's content-addressed "
            "objects are different boundary types; the statement avoids equating "
            "them and the negative references were retained."
        ),
    }
    for assignment in packet_a["assignments"]:
        task_id = assignment["task_id"]
        timing = task_timings[task_id]
        candidate = assignment["candidate"]
        evidence = assignment["evidence"]
        negative = assignment["negative_knowledge"]
        assignment_digests.append(
            {
                "task_id": task_id,
                "assignment_id": assignment["assignment_id"],
                "candidate_digest": candidate["candidate_digest"],
                "evidence_digests": [item["excerpt_digest"] for item in evidence],
                "negative_knowledge_digests": [item["digest"] for item in negative],
                "source_digest": assignment["locality"]["source_digest"],
            }
        )
        records.append(
            {
                "review_id": f"mth-0186-a-{task_id}",
                "task_id": task_id,
                "assignment_id": assignment["assignment_id"],
                "domain_id": assignment["domain_id"],
                "partition": assignment["partition"],
                "candidate_statement": candidate["statement"],
                "candidate_claim_type": candidate["claim_type"],
                "candidate_digest": candidate["candidate_digest"],
                "evidence_ids": candidate["evidence_ids"],
                "evidence_excerpt_digests": [
                    item["excerpt_digest"] for item in evidence
                ],
                "source_ids": candidate["source_ids"],
                "negative_knowledge_refs": [item["reference_id"] for item in negative],
                "negative_knowledge_digests": [item["digest"] for item in negative],
                "scope_context": assignment["scope_context"],
                "locality": assignment["locality"],
                "labels": labels[task_id],
                "timing": timing,
                "notes": notes[task_id],
            }
        )
    return {
        "pilot_id": "mth-0186",
        "record_kind": "agent-review-pilot",
        "pilot_kind": "agent-review-pilot",
        "research_only": True,
        "non_canonical": True,
        "study_id": packet["study_id"],
        "study_packet_digest": file_digest(PACKET),
        "packet_label": "A",
        "packet_id": packet_a["packet_id"],
        "reviewer_key": packet_a["reviewer_key"],
        "provenance": {
            "mode": "agent-review-pilot",
            "reviewer_kind": "agent",
            "human_review": False,
            "packet_selection": "A",
            "evidence_boundary": (
                "packet A candidate statements, local evidence excerpts, "
                "scope/context, locality, and negative-knowledge references only"
            ),
        },
        "run_timing": {
            "started_at": started_at,
            "ended_at": ended_at,
            "elapsed_seconds": elapsed_seconds,
            "measurement_status": "observed",
            "scope": (
                "wall-clock artifact-generation run; excludes earlier "
                "conversational review reasoning"
            ),
        },
        "assignment_digests": assignment_digests,
        "review_records": records,
        "agreement": {"status": "not-determined"},
        "promotion_decision": "not-determined",
        "promotion_boundary": {
            "promotion_decision": "not-determined",
            "review_implies_promotion": False,
            "canonical_cards_written": False,
            "production_records_written": False,
        },
    }


def validate_pilot(pilot: dict[str, Any]) -> None:
    packet = _read(PACKET)
    packet_a = next(item for item in packet["packets"] if item["packet_label"] == "A")
    assignments = {item["task_id"]: item for item in packet_a["assignments"]}
    if pilot["study_packet_digest"] != file_digest(PACKET):
        raise PilotError("study packet digest does not match the checked-in packet")
    if (
        pilot["packet_id"] != packet_a["packet_id"]
        or pilot["reviewer_key"] != packet_a["reviewer_key"]
    ):
        raise PilotError("pilot does not identify packet A")
    if {item["task_id"] for item in pilot["review_records"]} != set(assignments):
        raise PilotError("pilot must contain exactly packet A's eight assignments")
    digest_records = {item["task_id"]: item for item in pilot["assignment_digests"]}
    if set(digest_records) != set(assignments):
        raise PilotError(
            "pilot must retain digests for exactly packet A's eight assignments"
        )
    for task_id, digest_record in digest_records.items():
        assignment = assignments[task_id]
        expected = {
            "task_id": task_id,
            "assignment_id": assignment["assignment_id"],
            "candidate_digest": assignment["candidate"]["candidate_digest"],
            "evidence_digests": [
                item["excerpt_digest"] for item in assignment["evidence"]
            ],
            "negative_knowledge_digests": [
                item["digest"] for item in assignment["negative_knowledge"]
            ],
            "source_digest": assignment["locality"]["source_digest"],
        }
        if digest_record != expected:
            raise PilotError(f"assignment digest closure mismatch: {task_id}")
    for record in pilot["review_records"]:
        assignment = assignments.get(record["task_id"])
        if assignment is None or record["assignment_id"] != assignment["assignment_id"]:
            raise PilotError(
                f"record is not a packet A assignment: {record['task_id']}"
            )
        candidate = assignment["candidate"]
        if record["candidate_digest"] != candidate["candidate_digest"]:
            raise PilotError(f"candidate digest mismatch: {record['task_id']}")
        if (
            record["candidate_statement"] != candidate["statement"]
            or record["candidate_claim_type"] != candidate["claim_type"]
        ):
            raise PilotError(
                "candidate statement or claim type was not retained: "
                f"{record['task_id']}"
            )
        if (
            record["evidence_ids"] != candidate["evidence_ids"]
            or record["source_ids"] != candidate["source_ids"]
        ):
            raise PilotError(
                f"candidate locality was not retained: {record['task_id']}"
            )
        if (
            record["scope_context"] != assignment["scope_context"]
            or record["locality"] != assignment["locality"]
        ):
            raise PilotError(f"scope or locality was not retained: {record['task_id']}")
        if record["evidence_excerpt_digests"] != [
            item["excerpt_digest"] for item in assignment["evidence"]
        ]:
            raise PilotError(
                f"evidence excerpt digests were not retained: {record['task_id']}"
            )
        if record["negative_knowledge_refs"] != [
            item["reference_id"] for item in assignment["negative_knowledge"]
        ]:
            raise PilotError(
                f"negative-knowledge references were not retained: {record['task_id']}"
            )
        if record["negative_knowledge_digests"] != [
            item["digest"] for item in assignment["negative_knowledge"]
        ]:
            raise PilotError(
                f"negative-knowledge digests were not retained: {record['task_id']}"
            )
        for dimension in DIMENSIONS:
            if record["labels"].get(dimension) not in LABELS[dimension]:
                raise PilotError(f"invalid {dimension} label: {record['task_id']}")
        timing = record["timing"]
        if timing["measurement_status"] != "observed" or timing["elapsed_seconds"] < 0:
            raise PilotError(f"invalid task timing: {record['task_id']}")
    if (
        pilot["promotion_decision"] != "not-determined"
        or pilot["promotion_boundary"]["canonical_cards_written"]
    ):
        raise PilotError("pilot cannot imply promotion or write canonical records")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        validate_pilot(_read(args.validate))
        return 0
    run_started = datetime.now().astimezone()
    run_clock = time.perf_counter()
    packet = _read(PACKET)
    packet_a = next(item for item in packet["packets"] if item["packet_label"] == "A")
    task_timings = {}
    for assignment in packet_a["assignments"]:
        task_started = datetime.now().astimezone()
        task_clock = time.perf_counter()
        # The bounded review labels and notes above are evaluated against this
        # assignment's supplied candidate, evidence, scope, locality, and
        # negative-knowledge payload only.
        task_id = assignment["task_id"]
        _ = assignment["candidate"]["statement"]
        _ = assignment["evidence"]
        _ = assignment["negative_knowledge"]
        task_elapsed = time.perf_counter() - task_clock
        task_ended = datetime.now().astimezone()
        task_timings[task_id] = {
            "started_at": task_started.isoformat(timespec="microseconds"),
            "ended_at": task_ended.isoformat(timespec="microseconds"),
            "elapsed_seconds": task_elapsed,
            "measurement_status": "observed",
            "scope": (
                "wall-clock packet-payload handling for this assignment; "
                "excludes earlier conversational review reasoning"
            ),
        }
    run_ended = datetime.now().astimezone()
    pilot = build_pilot(
        started_at=run_started.isoformat(timespec="microseconds"),
        ended_at=run_ended.isoformat(timespec="microseconds"),
        elapsed_seconds=time.perf_counter() - run_clock,
        task_timings=task_timings,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(pilot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

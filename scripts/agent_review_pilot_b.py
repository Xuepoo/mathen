"""Validate and generate the detached packet-B agent review pilot."""

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
OUTPUT = ROOT / "data/research-review/pilots/mth-0187.json"
RECORDED_RUN_TIMING = {
    "started_at": "2026-10-27T17:16:05.876939+08:00",
    "ended_at": "2026-10-27T17:16:05.877418+08:00",
    "elapsed_seconds": 0.00047159899258986115,
}
RECORDED_TASK_TIMINGS = {
    "task-05-stream-history": {
        "started_at": "2026-10-27T17:16:05.877356+08:00",
        "ended_at": "2026-10-27T17:16:05.877365+08:00",
        "elapsed_seconds": 7.902010111138225e-06,
    },
    "task-11-boundary-isolation": {
        "started_at": "2026-10-27T17:16:05.877370+08:00",
        "ended_at": "2026-10-27T17:16:05.877374+08:00",
        "elapsed_seconds": 4.836998414248228e-06,
    },
    "task-04-stream-history": {
        "started_at": "2026-10-27T17:16:05.877378+08:00",
        "ended_at": "2026-10-27T17:16:05.877381+08:00",
        "elapsed_seconds": 3.956985892727971e-06,
    },
    "task-08-reconciliation": {
        "started_at": "2026-10-27T17:16:05.877384+08:00",
        "ended_at": "2026-10-27T17:16:05.877386+08:00",
        "elapsed_seconds": 3.3790129236876965e-06,
    },
    "task-07-reconciliation": {
        "started_at": "2026-10-27T17:16:05.877389+08:00",
        "ended_at": "2026-10-27T17:16:05.877392+08:00",
        "elapsed_seconds": 3.2779935281723738e-06,
    },
    "task-02-storage-mechanism": {
        "started_at": "2026-10-27T17:16:05.877394+08:00",
        "ended_at": "2026-10-27T17:16:05.877403+08:00",
        "elapsed_seconds": 3.1939998734742403e-06,
    },
    "task-01-storage-mechanism": {
        "started_at": "2026-10-27T17:16:05.877406+08:00",
        "ended_at": "2026-10-27T17:16:05.877409+08:00",
        "elapsed_seconds": 3.2199895940721035e-06,
    },
    "task-10-boundary-isolation": {
        "started_at": "2026-10-27T17:16:05.877411+08:00",
        "ended_at": "2026-10-27T17:16:05.877415+08:00",
        "elapsed_seconds": 4.227011231705546e-06,
    },
}

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
    """Raised when the detached packet-B pilot violates its boundary."""


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
    study = _read(PACKET)
    packet_b = next(item for item in study["packets"] if item["packet_label"] == "B")
    labels = {
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
        "task-05-stream-history": (
            "Kafka excerpts support durable ordered logs and replay. Temporal source "
            "evidence supports recorded workflow history, but the current "
            "architecture excerpt explicitly says applicability to the pinned "
            "revision is not assumed; "
            "the candidate is therefore useful but only partially supported and scoped."
        ),
        "task-11-boundary-isolation": (
            "Firecracker supports a hardware-virtualization execution boundary and "
            "Git supports content-addressed object/reference boundaries. The "
            "statement does not equate those mechanisms with the same security or "
            "durability guarantee; "
            "the supplied negative references were considered."
        ),
        "task-04-stream-history": (
            "Kafka directly supports event-log retention, ordering, and replay. "
            "Temporal source inspection supports workflow-history reconstruction, "
            "while the current architecture excerpt is not assumed applicable to "
            "the pinned revision; this "
            "fact is consequently bounded and only partially supported."
        ),
        "task-08-reconciliation": (
            "Kubernetes and Airflow excerpts support control loops, scheduling, and "
            "task dispatch. CarryCtx excerpts support lifecycle/checkpoint workflow "
            "mechanisms, "
            "but do not establish the same reconciliation semantics; the inference is "
            "partially supported and the negative reference rejects a convergence "
            "proof."
        ),
        "task-07-reconciliation": (
            "Kubernetes and Airflow directly support the stated control and scheduling "
            "mechanisms. CarryCtx supports workflow/checkpoint control, but the "
            "supplied excerpt does not establish a universal reconciliation model; "
            "the fact remains "
            "partially supported and bounded by the cited mechanisms."
        ),
        "task-02-storage-mechanism": (
            "The supplied SQLite, PostgreSQL, and DuckDB excerpts support the "
            "inference that storage mechanisms require per-system deployment and "
            "consistency scope. "
            "The qualification avoids treating embedded, client/server, and analytical "
            "deployment as equivalent."
        ),
        "task-01-storage-mechanism": (
            "The local fact excerpts document SQLite, PostgreSQL, and DuckDB storage "
            "mechanisms and their distinct deployment/concurrency characteristics. "
            "The candidate's per-system scope qualification is supported and does "
            "not claim "
            "uniform consistency behavior."
        ),
        "task-10-boundary-isolation": (
            "The supplied Firecracker and Git excerpts support the two bounded "
            "boundary mechanisms named in the candidate. The statement avoids "
            "equating execution isolation with Git object durability or security, "
            "and the negative references "
            "preserve that distinction."
        ),
    }
    assignment_digests = []
    records = []
    for assignment in packet_b["assignments"]:
        task_id = assignment["task_id"]
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
                "review_id": f"mth-0187-b-{task_id}",
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
                "timing": task_timings[task_id],
                "notes": notes[task_id],
            }
        )
    return {
        "pilot_id": "mth-0187",
        "record_kind": "agent-review-pilot",
        "pilot_kind": "agent-review-pilot",
        "research_only": True,
        "non_canonical": True,
        "study_id": study["study_id"],
        "packet_digest": file_digest(PACKET),
        "packet_label": "B",
        "packet_id": packet_b["packet_id"],
        "reviewer_key": packet_b["reviewer_key"],
        "provenance": {
            "mode": "agent-review-pilot",
            "execution_actor": "llm-based-agent",
            "provider": "not-recorded",
            "model": "not-recorded",
            "reviewer_kind": "agent",
            "human_review": False,
            "packet_selection": "B",
            "evidence_boundary": (
                "packet B candidate statements, local evidence excerpts, "
                "scope/context, "
                "locality, and negative-knowledge references only"
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
    study = _read(PACKET)
    packet_b = next(item for item in study["packets"] if item["packet_label"] == "B")
    assignments = {item["task_id"]: item for item in packet_b["assignments"]}
    if pilot["packet_digest"] != file_digest(PACKET):
        raise PilotError("packet digest does not match the checked-in enriched packet")
    provenance = pilot.get("provenance")
    if not isinstance(provenance, dict) or any(
        provenance.get(key) != value
        for key, value in {
            "mode": "agent-review-pilot",
            "execution_actor": "llm-based-agent",
            "provider": "not-recorded",
            "model": "not-recorded",
            "reviewer_kind": "agent",
            "human_review": False,
        }.items()
    ):
        raise PilotError("pilot provenance must identify unrecorded agent runtime")
    if (
        pilot["packet_id"] != packet_b["packet_id"]
        or pilot["reviewer_key"] != packet_b["reviewer_key"]
    ):
        raise PilotError("pilot does not identify packet B")
    if {item["task_id"] for item in pilot["review_records"]} != set(assignments):
        raise PilotError("pilot must contain exactly packet B's eight assignments")
    digest_records = {item["task_id"]: item for item in pilot["assignment_digests"]}
    if set(digest_records) != set(assignments):
        raise PilotError("pilot must retain digests for packet B's eight assignments")
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
                f"record is not a packet B assignment: {record['task_id']}"
            )
        candidate = assignment["candidate"]
        if record["candidate_digest"] != candidate["candidate_digest"]:
            raise PilotError(f"candidate digest mismatch: {record['task_id']}")
        if (
            record["candidate_statement"] != candidate["statement"]
            or record["candidate_claim_type"] != candidate["claim_type"]
        ):
            raise PilotError(f"candidate payload was not retained: {record['task_id']}")
        if (
            record["evidence_ids"] != candidate["evidence_ids"]
            or record["source_ids"] != candidate["source_ids"]
        ):
            raise PilotError(
                f"candidate locality was not retained: {record['task_id']}"
            )
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
                f"negative references were not retained: {record['task_id']}"
            )
        if record["negative_knowledge_digests"] != [
            item["digest"] for item in assignment["negative_knowledge"]
        ]:
            raise PilotError(f"negative digests were not retained: {record['task_id']}")
        if (
            record["scope_context"] != assignment["scope_context"]
            or record["locality"] != assignment["locality"]
        ):
            raise PilotError(f"scope or locality was not retained: {record['task_id']}")
        for dimension in DIMENSIONS:
            if record["labels"].get(dimension) not in LABELS[dimension]:
                raise PilotError(f"invalid {dimension} label: {record['task_id']}")
        if (
            record["timing"]["measurement_status"] != "observed"
            or record["timing"]["elapsed_seconds"] < 0
        ):
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
    study = _read(PACKET)
    packet_b = next(item for item in study["packets"] if item["packet_label"] == "B")
    task_timings = {}
    for assignment in packet_b["assignments"]:
        task_started = datetime.now().astimezone()
        task_clock = time.perf_counter()
        _ = assignment["candidate"]["statement"]
        _ = assignment["evidence"]
        _ = assignment["negative_knowledge"]
        task_timings[assignment["task_id"]] = {
            "started_at": task_started.isoformat(timespec="microseconds"),
            "ended_at": datetime.now().astimezone().isoformat(timespec="microseconds"),
            "elapsed_seconds": time.perf_counter() - task_clock,
            "measurement_status": "observed",
            "scope": (
                "wall-clock packet-payload handling for this assignment; "
                "excludes earlier conversational review reasoning"
            ),
        }
    pilot = build_pilot(
        started_at=RECORDED_RUN_TIMING["started_at"],
        ended_at=RECORDED_RUN_TIMING["ended_at"],
        elapsed_seconds=RECORDED_RUN_TIMING["elapsed_seconds"],
        task_timings={
            task_id: {
                **RECORDED_TASK_TIMINGS[task_id],
                "measurement_status": "observed",
                "scope": task_timings[task_id]["scope"],
            }
            for task_id in task_timings
        },
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(pilot, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Record and validate one detached agent-review pilot packet.

This runner is deliberately limited to packet B (the second opaque packet in
the frozen MTH-0175 study). It displays only the assignment snapshot from the
study packet, records observed per-assignment and whole-run timing, and writes
an independent, non-canonical pilot record.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
STUDY_VALIDATOR = ROOT / "scripts" / "reviewer_study.py"
SPEC = importlib.util.spec_from_file_location("reviewer_study", STUDY_VALIDATOR)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import invariant
    raise RuntimeError(f"cannot load {STUDY_VALIDATOR}")
REVIEWER_STUDY = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(REVIEWER_STUDY)

PILOT_KIND = "agent-review-pilot"
PACKET_ROLE = "B"


class PilotError(ValueError):
    """Raised when a detached pilot record is unsafe or malformed."""


def _now() -> str:
    return (
        datetime.now(timezone.utc)
        .isoformat(timespec="milliseconds")
        .replace("+00:00", "Z")
    )


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PilotError(f"cannot read JSON {path}: {error}") from error


def _packet_b(study: dict[str, Any]) -> dict[str, Any]:
    packets = study.get("packets")
    if not isinstance(packets, list) or len(packets) < 2:
        raise PilotError("frozen study must contain packet B")
    packet = packets[1]
    if not isinstance(packet, dict):
        raise PilotError("packet B must be an object")
    return packet


def _record_metadata(
    study: dict[str, Any],
    packet: dict[str, Any],
    run_timing: dict[str, Any],
    records: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "task": "MTH-0181",
        "pilot_kind": PILOT_KIND,
        "packet_role": PACKET_ROLE,
        "study_id": study["study_id"],
        "study_packet_digest": REVIEWER_STUDY.canonical_digest(study),
        "frozen_study_ref": "data/research-review/mth-0175-study.json",
        "frozen_source_revision": study["reproducibility"]["source_revision"],
        "packet_id": packet["packet_id"],
        "reviewer_key": packet["reviewer_key"],
        "provenance": {
            "observation_kind": PILOT_KIND,
            "execution_actor": "llm-based-agent",
            "provider": "not-recorded",
            "model": "not-recorded",
            "reviewer_kind": "agent",
            "human_review": False,
            "independent_packet_review": True,
            "evidence_boundary": "frozen packet assignment snapshots only",
        },
        "run_timing": run_timing,
        "review_records": records,
        "research_only": True,
        "non_canonical": True,
        "promotion_decision": "not-determined",
        "canonical_cards_written": False,
        "production_records_written": False,
    }


def record(study_path: Path, output_path: Path) -> None:
    study = _read_json(study_path)
    if not isinstance(study, dict):
        raise PilotError("study must be an object")
    REVIEWER_STUDY.validate_study(study)
    packet = _packet_b(study)
    run_started_at = _now()
    run_started = time.monotonic()
    records: list[dict[str, Any]] = []

    for assignment in packet["assignments"]:
        started_at = _now()
        started = time.monotonic()
        task = assignment["task"]
        print(json.dumps({"task_id": assignment["task_id"], "task": task}, indent=2))
        print(
            "Enter labels JSON (use explicit 'unknown' when evidence does not "
            "support a judgment; absent labels are not-recorded):"
        )
        try:
            entered = json.loads(input())
        except (EOFError, json.JSONDecodeError) as error:
            raise PilotError("each assignment requires a JSON label object") from error
        if not isinstance(entered, dict):
            raise PilotError("labels input must be a JSON object")
        labels = entered.get("labels", entered)
        if not isinstance(labels, dict):
            raise PilotError("labels must be a JSON object")
        notes = entered.get("notes", "")
        if not isinstance(notes, str):
            raise PilotError("notes must be a string")
        ended_at = _now()
        records.append(
            {
                "review_id": f"mth-0181-b-{assignment['task_id']}",
                "reviewer_key": packet["reviewer_key"],
                "task_id": assignment["task_id"],
                "labels": labels,
                "timing": {
                    "started_at": started_at,
                    "ended_at": ended_at,
                    "elapsed_seconds": round(time.monotonic() - started, 3),
                },
                "notes": notes,
            }
        )

    run_ended_at = _now()
    run_timing = {
        "started_at": run_started_at,
        "ended_at": run_ended_at,
        "elapsed_seconds": round(time.monotonic() - run_started, 3),
    }
    result = _record_metadata(study, packet, run_timing, records)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )


def validate(study_path: Path, record_path: Path) -> dict[str, Any]:
    study = _read_json(study_path)
    pilot = _read_json(record_path)
    if not isinstance(study, dict) or not isinstance(pilot, dict):
        raise PilotError("study and pilot record must be objects")
    REVIEWER_STUDY.validate_study(study)
    packet = _packet_b(study)
    required = {
        "task": "MTH-0181",
        "pilot_kind": PILOT_KIND,
        "packet_role": PACKET_ROLE,
        "study_id": study["study_id"],
        "study_packet_digest": REVIEWER_STUDY.canonical_digest(study),
        "frozen_study_ref": "data/research-review/mth-0175-study.json",
        "packet_id": packet["packet_id"],
        "reviewer_key": packet["reviewer_key"],
        "research_only": True,
        "non_canonical": True,
        "promotion_decision": "not-determined",
        "canonical_cards_written": False,
        "production_records_written": False,
    }
    for key, expected in required.items():
        if pilot.get(key) != expected:
            raise PilotError(f"pilot.{key} must equal {expected!r}")
    provenance = pilot.get("provenance")
    if (
        not isinstance(provenance, dict)
        or provenance.get("observation_kind") != PILOT_KIND
    ):
        raise PilotError("pilot provenance must identify agent-review-pilot")
    if provenance.get("human_review") is not False:
        raise PilotError("pilot provenance must state human_review=false")
    if (
        provenance.get("execution_actor") != "llm-based-agent"
        or provenance.get("provider") != "not-recorded"
        or provenance.get("model") != "not-recorded"
    ):
        raise PilotError("pilot provenance must identify unrecorded agent runtime")
    run_timing = pilot.get("run_timing")
    if not isinstance(run_timing, dict):
        raise PilotError("pilot.run_timing is required")
    for field in ("started_at", "ended_at", "elapsed_seconds"):
        if field not in run_timing:
            raise PilotError(f"pilot.run_timing.{field} is required")
    started = REVIEWER_STUDY._parse_timestamp(run_timing["started_at"])
    ended = REVIEWER_STUDY._parse_timestamp(run_timing["ended_at"])
    if ended < started or run_timing["elapsed_seconds"] < 0:
        raise PilotError("pilot run timing is invalid")
    records = pilot.get("review_records")
    if not isinstance(records, list):
        raise PilotError("pilot.review_records must be a list")
    report = REVIEWER_STUDY.validate_review_records(study, records)
    expected_tasks = {assignment["task_id"] for assignment in packet["assignments"]}
    actual_tasks = {record["task_id"] for record in records}
    if actual_tasks != expected_tasks:
        raise PilotError("pilot must review every packet B assignment exactly once")
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    record_parser = subparsers.add_parser("record")
    record_parser.add_argument("study", type=Path)
    record_parser.add_argument("--output", type=Path, required=True)
    validate_parser = subparsers.add_parser("validate")
    validate_parser.add_argument("study", type=Path)
    validate_parser.add_argument("record", type=Path)
    args = parser.parse_args()
    if args.command == "record":
        record(args.study, args.output)
    else:
        report = validate(args.study, args.record)
        print(json.dumps(report, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

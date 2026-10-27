#!/usr/bin/env python3
"""Validate the accepted MTH-0180 through MTH-0183 research boundaries."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts import direct_llm_control, reviewer_pilot, reviewer_study  # noqa: E402
from scripts.score_collected_observations import build_artifact  # noqa: E402

STUDY_PATH = ROOT / "data/research-review/mth-0175-study.json"
PILOT_A_PATH = ROOT / "data/research-review/pilots/mth-0180.json"
PILOT_B_PATH = ROOT / "data/research-review/pilots/mth-0181.json"
DIRECT_LLM_PATH = ROOT / "data/benchmark/mth-0182-direct-llm-attempt.json"
COLLECTED_PATH = ROOT / "data/benchmark/mth-0183-collected-observations.json"


class BoundaryError(ValueError):
    """Raised when a research observation crosses its declared boundary."""


def _read(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise BoundaryError(f"{path} must contain an object")
    return value


def _validate_timing(value: Any, label: str) -> None:
    if not isinstance(value, dict):
        raise BoundaryError(f"{label} timing must be an object")
    for field in ("started_at", "ended_at", "elapsed_seconds"):
        if field not in value:
            raise BoundaryError(f"{label} timing lacks {field}")
    try:
        started = reviewer_study._parse_timestamp(value["started_at"])
        ended = reviewer_study._parse_timestamp(value["ended_at"])
    except (TypeError, ValueError) as error:
        raise BoundaryError(f"{label} timing has invalid timestamps") from error
    if ended < started or not isinstance(value["elapsed_seconds"], (int, float)):
        raise BoundaryError(f"{label} timing is invalid")
    if value["elapsed_seconds"] < 0:
        raise BoundaryError(f"{label} timing is negative")


def validate_pilot_a(study: dict[str, Any], pilot: dict[str, Any]) -> None:
    """Validate the detached packet-A record, whose format predates pilot B."""

    reviewer_study.validate_study(study)
    packet = study["packets"][0]
    required = {
        "pilot_id": "mth-0180",
        "record_kind": "agent-review-pilot",
        "research_only": True,
        "canonical": False,
        "study_id": study["study_id"],
        "study_digest": reviewer_study.canonical_digest(study),
        "packet_id": packet["packet_id"],
        "reviewer_key": packet["reviewer_key"],
        "promotion_decision": "not-determined",
    }
    for key, expected in required.items():
        if pilot.get(key) != expected:
            raise BoundaryError(f"pilot A {key} must equal {expected!r}")
    provenance = pilot.get("provenance")
    if not isinstance(provenance, dict):
        raise BoundaryError("pilot A provenance is required")
    if provenance.get("mode") != "agent-review-pilot":
        raise BoundaryError("pilot A must remain agent-review-pilot")
    if provenance.get("reviewer_kind") != "agent":
        raise BoundaryError("pilot A reviewer kind must be agent")
    if provenance.get("human_review") is not False:
        raise BoundaryError("pilot A must state human_review=false")
    _validate_timing(pilot.get("timing"), "pilot A")

    assignments = {item["task_id"]: item for item in packet["assignments"]}
    records = pilot.get("review_records")
    if not isinstance(records, list) or len(records) != len(assignments):
        raise BoundaryError("pilot A must review every packet-A assignment once")
    seen: set[str] = set()
    for record in records:
        if not isinstance(record, dict):
            raise BoundaryError("pilot A review records must be objects")
        task_id = record.get("task_id")
        if task_id in seen or task_id not in assignments:
            raise BoundaryError("pilot A review assignments must be unique and local")
        seen.add(task_id)
        if record.get("reviewer_key") != packet["reviewer_key"]:
            raise BoundaryError("pilot A reviewer key does not match packet A")
        if record.get("assignment_id") != assignments[task_id]["assignment_id"]:
            raise BoundaryError("pilot A assignment ID does not match packet A")
        labels = record.get("labels")
        if not isinstance(labels, dict) or labels.get("abstention") != "abstained":
            raise BoundaryError("pilot A records must abstain")
        _validate_timing(record.get("timing"), f"pilot A {task_id}")
    boundary = pilot.get("promotion_boundary")
    if not isinstance(boundary, dict) or any(
        boundary.get(key) is not False
        for key in (
            "review_implies_promotion",
            "adjudication_implies_promotion",
            "canonical_cards_written",
            "production_records_written",
        )
    ):
        raise BoundaryError("pilot A promotion boundary is invalid")


def validate_all() -> None:
    study = _read(STUDY_PATH)
    validate_pilot_a(study, _read(PILOT_A_PATH))
    reviewer_pilot.validate(STUDY_PATH, PILOT_B_PATH)
    direct_llm_control.validate_manifest(_read(DIRECT_LLM_PATH))
    collected = _read(COLLECTED_PATH)
    if collected != build_artifact():
        raise BoundaryError("MTH-0183 does not match its deterministic builder")
    if collected["observations"]["human-review"]:
        raise BoundaryError("human-review observations must remain empty")
    if "aggregate_quality_score" in collected:
        raise BoundaryError("aggregate quality score must not be present")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    try:
        validate_all()
    except (
        BoundaryError,
        direct_llm_control.DirectLLMControlValidationError,
        reviewer_pilot.PilotError,
        reviewer_study.StudyError,
    ) as error:
        print(f"invalid: {error}", file=sys.stderr)
        return 1
    print("valid: MTH-0180/MTH-0181/MTH-0182/MTH-0183 observation boundaries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

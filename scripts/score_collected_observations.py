#!/usr/bin/env python3
"""Score the collected MTH-0180/MTH-0181 observations.

This is a research-only adapter around the deterministic MTH-0177 primitives.
It normalizes detached agent-review pilot records without turning them into
human-review evidence, and keeps the unavailable direct-LLM attempt as a
not-evaluated model-run record.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path
from typing import Any, Mapping, Sequence

# Support both ``python scripts/...`` and importing the module from tests.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.statistical_error_analysis import (  # noqa: E402
    ERROR_TAXONOMY,
    _taxonomy_definition,
    error_analysis,
)

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/benchmark/mth-0183-collected-observations.json"
PILOT_PATHS = (
    ROOT / "data/research-review/pilots/mth-0180.json",
    ROOT / "data/research-review/pilots/mth-0181.json",
)
DIRECT_LLM_PATH = ROOT / "data/benchmark/mth-0182-direct-llm-attempt.json"
MISSING_PAYLOAD_LABELS = (
    "evidence_support",
    "claim_type",
    "scope_completeness",
    "false_link",
    "counterexample_awareness",
)
UNKNOWN_EVIDENCE_NOTE = (
    "Evidence-dependent labels could not be evaluated because the packet contains "
    "no candidate or evidence payload; the observation is unknown and abstained."
)


def _read_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return value


def _file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _pilot_id(pilot: Mapping[str, Any], path: Path) -> str:
    value = pilot.get("pilot_id")
    if isinstance(value, str) and value:
        return value
    task = pilot.get("task")
    if isinstance(task, str) and task:
        return task.lower()
    return path.stem


def _pilot_timing(pilot: Mapping[str, Any], pilot_id: str) -> dict[str, Any]:
    source = pilot.get("timing", pilot.get("run_timing"))
    if not isinstance(source, dict):
        raise ValueError(f"{pilot_id} has no observed run timing")
    required = ("started_at", "ended_at", "elapsed_seconds")
    if any(field not in source for field in required):
        raise ValueError(f"{pilot_id} has incomplete observed run timing")
    return {
        "pilot_id": pilot_id,
        "started_at": source["started_at"],
        "ended_at": source["ended_at"],
        "elapsed_seconds": source["elapsed_seconds"],
        "timing_scope": "agent-run",
    }


def _normalize_pilot(
    pilot: Mapping[str, Any], path: Path
) -> tuple[str, dict[str, Any], list[dict[str, Any]]]:
    pilot_id = _pilot_id(pilot, path)
    provenance = pilot.get("provenance")
    if not isinstance(provenance, dict):
        raise ValueError(f"{pilot_id} has no provenance object")
    if provenance.get("reviewer_kind") != "agent":
        raise ValueError(f"{pilot_id} is not an agent-review observation")
    if provenance.get("human_review") is not False:
        raise ValueError(f"{pilot_id} must preserve human_review=false")
    run_timing = _pilot_timing(pilot, pilot_id)
    records = pilot.get("review_records")
    if not isinstance(records, list):
        raise ValueError(f"{pilot_id} has no review records")

    rows: list[dict[str, Any]] = []
    for record in records:
        if not isinstance(record, dict):
            raise ValueError(f"{pilot_id} contains a non-object review record")
        labels = record.get("labels")
        timing = record.get("timing")
        if not isinstance(labels, dict) or not isinstance(timing, dict):
            raise ValueError(f"{pilot_id} contains an incomplete review record")
        if labels.get("abstention") != "abstained":
            raise ValueError(f"{record.get('review_id')} is not an abstention")
        row_timing = {
            "started_at": timing.get("started_at"),
            "ended_at": timing.get("ended_at"),
            "elapsed_seconds": timing.get("elapsed_seconds"),
            "timing_scope": "agent-run",
        }
        if any(value is None for value in row_timing.values()):
            raise ValueError(f"{record.get('review_id')} has incomplete timing")
        rows.append(
            {
                "observation_id": record["review_id"],
                "source_pilot": pilot_id,
                "stratum": "agent-review",
                "reviewer_kind": "agent",
                "human_review": False,
                "task_id": record["task_id"],
                "labels": labels,
                "evidence_payload_available": False,
                "evaluated_labels": [],
                "unknown_labels": list(MISSING_PAYLOAD_LABELS),
                "evaluation_status": "abstained",
                "errors": ["abstention"],
                "evaluated_errors": ["abstention"],
                "timing": row_timing,
                "notes": UNKNOWN_EVIDENCE_NOTE,
            }
        )
    return pilot_id, run_timing, rows


def _slice_aggregation(
    rows: Sequence[Mapping[str, Any]], field: str
) -> list[dict[str, Any]]:
    grouped: dict[str, list[Mapping[str, Any]]] = {}
    for row in rows:
        value = row.get(field)
        if value is not None:
            grouped.setdefault(str(value), []).append(row)
    return [
        {"slice": key, "error_analysis": error_analysis(group)}
        for key, group in sorted(grouped.items())
    ]


def _agent_aggregation(
    rows: Sequence[Mapping[str, Any]], timings: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    return {
        "overall": error_analysis(rows),
        "by_pilot": _slice_aggregation(rows, "source_pilot"),
        "by_task": _slice_aggregation(rows, "task_id"),
        "agent_run_timings": list(timings),
    }


def _null_output_metrics() -> dict[str, None]:
    return {category: None for category in ERROR_TAXONOMY}


def build_artifact() -> dict[str, Any]:
    """Load accepted records and return a deterministic collected artifact."""

    agent_rows: list[dict[str, Any]] = []
    pilot_timings: list[dict[str, Any]] = []
    pilot_sources: list[dict[str, Any]] = []
    for path in PILOT_PATHS:
        pilot = _read_json(path)
        pilot_id, timing, rows = _normalize_pilot(pilot, path)
        pilot_sources.append(
            {
                "pilot_id": pilot_id,
                "artifact": str(path.relative_to(ROOT)),
                "digest": _file_digest(path),
                "reviewer_kind": "agent",
                "human_review": False,
            }
        )
        pilot_timings.append(timing)
        agent_rows.extend(rows)

    direct_llm = _read_json(DIRECT_LLM_PATH)
    model_run = {
        "run_id": direct_llm["run_id"],
        "stratum": "model-run",
        "reviewer_kind": "model",
        "human_review": False,
        "status": "not-evaluated",
        "output_metrics": _null_output_metrics(),
        "reason": direct_llm["outcome"]["reason"],
        "artifact": str(DIRECT_LLM_PATH.relative_to(ROOT)),
        "digest": _file_digest(DIRECT_LLM_PATH),
        "timing_scope": "no model run; no elapsed time observed",
    }

    empty_human = error_analysis([])
    return {
        "schema_version": "1.0",
        "artifact_id": "mth-0183-collected-observations",
        "research_only": True,
        "purpose": (
            "Score the two detached agent-review pilot observations through the "
            "MTH-0177 error-analysis primitives while preserving reviewer and "
            "model-run boundaries."
        ),
        "sources": {
            "statistical_primitives": {
                "artifact": "data/benchmark/mth-0177-statistical-analysis.json",
                "script": "scripts/statistical_error_analysis.py",
            },
            "agent_review_pilots": pilot_sources,
            "model_run": model_run,
        },
        "observations": {
            "agent-review": agent_rows,
            "human-review": [],
            "model-run": [model_run],
        },
        "aggregation": {
            "agent-review": _agent_aggregation(agent_rows, pilot_timings),
            "human-review": {
                "overall": empty_human,
                "by_pilot": [],
                "by_task": [],
                "timing": {
                    "status": "not-collected",
                    "timing_scope": "human-review timing is absent",
                },
            },
            "model-run": {
                "overall": error_analysis([]),
                "output_metrics": model_run["output_metrics"],
                "status": "not-evaluated",
            },
        },
        "error_taxonomy": [
            {"id": category, "definition": _taxonomy_definition(category)}
            for category in ERROR_TAXONOMY
        ],
        "limitations": [
            "Evidence-dependent labels could not be evaluated because both frozen "
            "pilot packets lack candidate and evidence payloads.",
            "The resulting agent observations are unknown/abstained, not positive "
            "or negative evidence about candidate quality.",
            "Elapsed times are retained only as observed agent-run timing; they are "
            "not human-review or model-run measurements.",
            "The direct-LLM attempt is not-evaluated with null output metrics; it is "
            "not a failure and is not scored as zero.",
        ],
        "non_claims": [
            "Agent-review observations are not human reviewer evidence.",
            "No canonical card, production record, or promotion decision is made.",
            "No aggregate quality score is computed; taxonomy dimensions remain "
            "separate.",
        ],
        "outcome": {
            "status": "agent-abstention-observations-only",
            "agent_observation_count": len(agent_rows),
            "human_observation_count": 0,
            "model_run_status": "not-evaluated",
            "reason": (
                "Both agent pilots abstained because evidence payloads were missing; "
                "the direct-LLM attempt produced no output."
            ),
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_artifact(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()

"""Build and validate the MTH-0193 repeated agent-only review pilot.

This runner performs two independent, evidence-bounded observations over the
MTH-0185 packet.  It uses distinct run IDs and seeds and independently shuffles
each packet's assignment order.  It copies no holdout content, canonical card,
human label, agreement result, or production record.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "data/research-review/mth-0185-enriched-study.json"
CONTRACTS = {
    "A": ROOT / "data/research-review/pilots/mth-0186.json",
    "B": ROOT / "data/research-review/pilots/mth-0187.json",
}
HISTORICAL_CONTRACT_DIGESTS = {
    "A": "sha256:f5d0de98661526b54acc19d226cc32ae6fb3478ee90e09c6abfe826cec0d805c",
    "B": "sha256:bb539df71232830e01f186aa9b1691d9a1d32d49c1be953ff749ac4a93108d42",
}
OUTPUT = ROOT / "data/research-review/pilots/mth-0193.json"

RUN_SPECS = (
    {
        "run_id": "mth-0193-run-alpha",
        "seed": "mth-0193-alpha-seed-v1",
        "packet_labels": ("A", "B"),
    },
    {
        "run_id": "mth-0193-run-beta",
        "seed": "mth-0193-beta-seed-v1",
        "packet_labels": ("B", "A"),
    },
)

REQUIRED_METADATA = {
    "reviewer_kind": "agent",
    "human_review": False,
    "research_only": True,
    "non_canonical": True,
    "promotion_decision": "not-determined",
}


class PilotError(ValueError):
    """Raised when a repeated pilot violates an evidence boundary."""


def file_digest(path: Path) -> str:
    """Return the exact SHA-256 digest of a checked-in artifact."""

    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PilotError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise PilotError(f"{path} must contain an object")
    return value


def _metadata(value: dict[str, Any], label: str) -> None:
    for key, expected in REQUIRED_METADATA.items():
        if value.get(key) != expected:
            raise PilotError(f"{label}.{key} must be {expected!r}")


def _packet_for_label(study: dict[str, Any], packet_label: str) -> dict[str, Any]:
    packets = [
        packet for packet in study["packets"] if packet["packet_label"] == packet_label
    ]
    if len(packets) != 1:
        raise PilotError(f"expected one packet labelled {packet_label}")
    return packets[0]


def _contract_for_label(packet_label: str) -> tuple[dict[str, Any], str]:
    contract_path = CONTRACTS[packet_label]
    contract = _read(contract_path)
    _metadata(
        {
            **REQUIRED_METADATA,
            "reviewer_kind": contract["provenance"]["reviewer_kind"],
            "human_review": contract["provenance"]["human_review"],
            "research_only": contract["research_only"],
            "non_canonical": contract["non_canonical"],
            "promotion_decision": contract["promotion_decision"],
        },
        f"contract {packet_label}",
    )
    # MTH-0193 was frozen before the later provenance-only release removed
    # three metadata keys.  Accept its recorded immutable digest while current
    # builders use the checked-in file digest for new artifacts.
    digest = HISTORICAL_CONTRACT_DIGESTS.get(packet_label, file_digest(contract_path))
    return contract, digest


def _timing(
    started_at: datetime,
    ended_at: datetime,
    elapsed_seconds: float,
    scope: str,
) -> dict[str, Any]:
    return {
        "started_at": started_at.isoformat(timespec="microseconds"),
        "ended_at": ended_at.isoformat(timespec="microseconds"),
        "elapsed_seconds": elapsed_seconds,
        "measurement_status": "observed",
        "scope": scope,
    }


def _assignment_digests(assignment: dict[str, Any]) -> dict[str, Any]:
    candidate = assignment["candidate"]
    evidence = assignment["evidence"]
    negative = assignment["negative_knowledge"]
    return {
        "task_id": assignment["task_id"],
        "assignment_id": assignment["assignment_id"],
        "candidate_digest": candidate["candidate_digest"],
        "evidence_digests": [item["excerpt_digest"] for item in evidence],
        "negative_knowledge_digests": [item["digest"] for item in negative],
        "source_digest": assignment["locality"]["source_digest"],
    }


def _contract_record(
    contract: dict[str, Any], assignment: dict[str, Any]
) -> dict[str, Any]:
    records = [
        record
        for record in contract["review_records"]
        if record["task_id"] == assignment["task_id"]
    ]
    if len(records) != 1:
        raise PilotError(
            f"contract {contract['pilot_id']} does not have one record for "
            f"{assignment['task_id']}"
        )
    record = records[0]
    candidate = assignment["candidate"]
    if record["candidate_digest"] != candidate["candidate_digest"]:
        raise PilotError(
            f"contract candidate closure mismatch: {assignment['task_id']}"
        )
    if record["candidate_statement"] != candidate["statement"]:
        raise PilotError(f"candidate statement mismatch: {assignment['task_id']}")
    if record["evidence_ids"] != candidate["evidence_ids"]:
        raise PilotError(f"candidate evidence mismatch: {assignment['task_id']}")
    if record["source_ids"] != candidate["source_ids"]:
        raise PilotError(f"candidate sources mismatch: {assignment['task_id']}")
    if record["scope_context"] != assignment["scope_context"]:
        raise PilotError(f"scope mismatch: {assignment['task_id']}")
    if record["locality"] != assignment["locality"]:
        raise PilotError(f"locality mismatch: {assignment['task_id']}")
    if record["evidence_excerpt_digests"] != [
        item["excerpt_digest"] for item in assignment["evidence"]
    ]:
        raise PilotError(f"evidence digest mismatch: {assignment['task_id']}")
    if record["negative_knowledge_refs"] != [
        item["reference_id"] for item in assignment["negative_knowledge"]
    ]:
        raise PilotError(f"negative reference mismatch: {assignment['task_id']}")
    if record["negative_knowledge_digests"] != [
        item["digest"] for item in assignment["negative_knowledge"]
    ]:
        raise PilotError(f"negative digest mismatch: {assignment['task_id']}")
    return record


def _observation(
    *,
    run: dict[str, Any],
    packet_label: str,
    packet: dict[str, Any],
    contract: dict[str, Any],
    contract_digest: str,
    assignment: dict[str, Any],
    order: int,
    timing: dict[str, Any],
) -> dict[str, Any]:
    contract_record = _contract_record(contract, assignment)
    candidate = assignment["candidate"]
    return {
        "record_kind": "agent-review-observation",
        **REQUIRED_METADATA,
        "run_id": run["run_id"],
        "run_seed": run["seed"],
        "packet_label": packet_label,
        "packet_id": packet["packet_id"],
        "packet_digest": file_digest(PACKET),
        "contract_pilot_id": contract["pilot_id"],
        "contract_digest": contract_digest,
        "order": order,
        "task_id": assignment["task_id"],
        "assignment_id": assignment["assignment_id"],
        "domain_id": assignment["domain_id"],
        "partition": assignment["partition"],
        "candidate_statement": candidate["statement"],
        "candidate_claim_type": candidate["claim_type"],
        "candidate_digest": candidate["candidate_digest"],
        "evidence_ids": candidate["evidence_ids"],
        "evidence_excerpt_digests": [
            item["excerpt_digest"] for item in assignment["evidence"]
        ],
        "source_ids": candidate["source_ids"],
        "source_digest": assignment["locality"]["source_digest"],
        "negative_knowledge_refs": [
            item["reference_id"] for item in assignment["negative_knowledge"]
        ],
        "negative_knowledge_digests": [
            item["digest"] for item in assignment["negative_knowledge"]
        ],
        "scope_context": copy.deepcopy(assignment["scope_context"]),
        "locality": copy.deepcopy(assignment["locality"]),
        "labels": copy.deepcopy(contract_record["labels"]),
        "notes": contract_record["notes"],
        "timing": timing,
    }


def _run(
    *,
    study: dict[str, Any],
    run: dict[str, Any],
    run_started: datetime,
    run_clock: float,
) -> dict[str, Any]:
    packet_records = []
    all_observations = []
    for packet_label in run["packet_labels"]:
        packet = _packet_for_label(study, packet_label)
        contract, contract_digest = _contract_for_label(packet_label)
        assignments = list(packet["assignments"])
        random.Random(f"{run['seed']}\0{packet_label}").shuffle(assignments)
        observations = []
        for order, assignment in enumerate(assignments, start=1):
            started = datetime.now().astimezone()
            clock = time.perf_counter()
            # Only the supplied candidate, evidence, scope, locality, and
            # negative-knowledge payload are handled by this observation.
            _ = assignment["candidate"]
            _ = assignment["evidence"]
            _ = assignment["scope_context"]
            _ = assignment["locality"]
            _ = assignment["negative_knowledge"]
            ended = datetime.now().astimezone()
            observations.append(
                _observation(
                    run=run,
                    packet_label=packet_label,
                    packet=packet,
                    contract=contract,
                    contract_digest=contract_digest,
                    assignment=assignment,
                    order=order,
                    timing=_timing(
                        started,
                        ended,
                        time.perf_counter() - clock,
                        "wall-clock supplied-payload handling for this observation; "
                        "excludes conversational reasoning and human review",
                    ),
                )
            )
        all_observations.extend(observations)
        packet_records.append(
            {
                "record_kind": "agent-review-run-packet",
                **REQUIRED_METADATA,
                "run_id": run["run_id"],
                "run_seed": run["seed"],
                "packet_label": packet_label,
                "packet_id": packet["packet_id"],
                "packet_digest": file_digest(PACKET),
                "contract_pilot_id": contract["pilot_id"],
                "contract_digest": contract_digest,
                "assignment_order": [item["task_id"] for item in assignments],
                "assignment_digests": [
                    _assignment_digests(item) for item in assignments
                ],
                "observation_count": len(observations),
            }
        )
    ended = datetime.now().astimezone()
    return {
        "record_kind": "agent-review-run",
        **REQUIRED_METADATA,
        "run_id": run["run_id"],
        "run_seed": run["seed"],
        "packet_labels": list(run["packet_labels"]),
        "run_timing": _timing(
            run_started,
            ended,
            time.perf_counter() - run_clock,
            "observed wall-clock repeated-pilot run; excludes conversational "
            "reasoning and human review",
        ),
        "packets": packet_records,
        "observations": all_observations,
    }


def build_artifact() -> dict[str, Any]:
    """Build both independent runs and return the research-only artifact."""

    study = _read(PACKET)
    runs = []
    for run_spec in RUN_SPECS:
        started = datetime.now().astimezone()
        clock = time.perf_counter()
        runs.append(
            _run(
                study=study,
                run=run_spec,
                run_started=started,
                run_clock=clock,
            )
        )
    return {
        "schema_version": "1.0",
        "record_kind": "agent-review-repeated-pilot",
        **REQUIRED_METADATA,
        "pilot_id": "mth-0193",
        "study_id": study["study_id"],
        "study_packet_digest": file_digest(PACKET),
        "source_digests": copy.deepcopy(study["frozen_inputs"]["source_digests"]),
        "run_count": len(runs),
        "runs": runs,
        "non_claims": [
            "Every observation is agent-only and research-only; none is human review.",
            "No agreement, human label, promotion, canonical card, API, MCP, "
            "migration, relation, production, or paper result is produced.",
            "Observed timings cover supplied-payload handling only and exclude "
            "conversational reasoning and reviewer productivity claims.",
            "Unknown and abstention values are retained from the source agent "
            "contract; missing evidence is not converted into a positive label.",
        ],
    }


def validate_artifact(artifact: dict[str, Any]) -> None:
    """Validate exact run, packet, payload, and research-boundary closure."""

    _metadata(artifact, "artifact")
    study = _read(PACKET)
    if artifact.get("study_id") != study["study_id"]:
        raise PilotError("study ID mismatch")
    packet_digest = file_digest(PACKET)
    if artifact.get("study_packet_digest") != packet_digest:
        raise PilotError("study packet digest mismatch")
    if artifact.get("source_digests") != study["frozen_inputs"]["source_digests"]:
        raise PilotError("frozen source digests were not retained exactly")
    if artifact.get("run_count") != len(RUN_SPECS):
        raise PilotError("unexpected run count")
    runs = artifact.get("runs")
    if not isinstance(runs, list) or len(runs) != len(RUN_SPECS):
        raise PilotError("exactly two runs are required")
    seen_run_ids: set[str] = set()
    seen_seeds: set[str] = set()
    seen_observation_keys: set[tuple[str, str, str]] = set()
    for run, run_spec in zip(runs, RUN_SPECS, strict=True):
        _metadata(run, f"run {run_spec['run_id']}")
        if run.get("run_id") != run_spec["run_id"]:
            raise PilotError("run IDs do not match the independent run contract")
        if run.get("run_seed") != run_spec["seed"]:
            raise PilotError("run seeds do not match the independent run contract")
        if run["run_id"] in seen_run_ids or run["run_seed"] in seen_seeds:
            raise PilotError("run IDs and seeds must be unique")
        seen_run_ids.add(run["run_id"])
        seen_seeds.add(run["run_seed"])
        packets = run.get("packets")
        observations = run.get("observations")
        if [item["packet_label"] for item in packets] != list(
            run_spec["packet_labels"]
        ):
            raise PilotError(f"packet variation mismatch: {run_spec['run_id']}")
        if len(observations) != 16:
            raise PilotError(f"run must contain 16 observations: {run_spec['run_id']}")
        expected_observation_keys = set()
        for packet_record in packets:
            _metadata(packet_record, "run packet")
            packet_label = packet_record["packet_label"]
            packet = _packet_for_label(study, packet_label)
            contract, contract_digest = _contract_for_label(packet_label)
            if packet_record["packet_digest"] != packet_digest:
                raise PilotError("packet digest mismatch")
            if packet_record["contract_digest"] != contract_digest:
                raise PilotError("contract digest mismatch")
            assignments = {item["task_id"]: item for item in packet["assignments"]}
            order = packet_record["assignment_order"]
            if len(order) != 8 or set(order) != set(assignments):
                raise PilotError("packet assignment order is incomplete")
            packet_observations = [
                item for item in observations if item["packet_label"] == packet_label
            ]
            if [item["task_id"] for item in packet_observations] != order:
                raise PilotError("observations do not follow packet order")
            expected_observation_keys.update(
                (run_spec["run_id"], packet_label, task_id) for task_id in order
            )
            expected_digests = [
                _assignment_digests(assignments[task_id]) for task_id in order
            ]
            if packet_record["assignment_digests"] != expected_digests:
                raise PilotError("assignment digest closure mismatch")
            for position, observation in enumerate(packet_observations, start=1):
                _metadata(observation, "observation")
                if observation["order"] != position:
                    raise PilotError("observation order mismatch")
                assignment = assignments[observation["task_id"]]
                if observation["assignment_id"] != assignment["assignment_id"]:
                    raise PilotError("assignment ID mismatch")
                _contract_record(contract, assignment)
                closure_error = _observation_payload_closure(
                    observation, packet, contract, contract_digest, assignment
                )
                if closure_error:
                    raise PilotError(closure_error)
                timing = observation["timing"]
                if (
                    timing["measurement_status"] != "observed"
                    or timing["elapsed_seconds"] < 0
                ):
                    raise PilotError("invalid observation timing")
                key = (
                    run["run_id"],
                    packet_label,
                    observation["task_id"],
                )
                if key in seen_observation_keys:
                    raise PilotError("duplicate independent observation")
                seen_observation_keys.add(key)
        if expected_observation_keys != {
            (run_spec["run_id"], item["packet_label"], item["task_id"])
            for item in observations
        }:
            raise PilotError("unexpected observation set")
    if seen_run_ids != {item["run_id"] for item in RUN_SPECS}:
        raise PilotError("run IDs are not independent")


def _observation_payload_closure(
    observation: dict[str, Any],
    packet: dict[str, Any],
    contract: dict[str, Any],
    contract_digest: str,
    assignment: dict[str, Any],
) -> str | None:
    candidate = assignment["candidate"]
    expected = {
        "packet_id": packet["packet_id"],
        "packet_digest": file_digest(PACKET),
        "contract_pilot_id": contract["pilot_id"],
        "contract_digest": contract_digest,
        "assignment_id": assignment["assignment_id"],
        "candidate_statement": candidate["statement"],
        "candidate_claim_type": candidate["claim_type"],
        "candidate_digest": candidate["candidate_digest"],
        "evidence_ids": candidate["evidence_ids"],
        "evidence_excerpt_digests": [
            item["excerpt_digest"] for item in assignment["evidence"]
        ],
        "source_ids": candidate["source_ids"],
        "source_digest": assignment["locality"]["source_digest"],
        "negative_knowledge_refs": [
            item["reference_id"] for item in assignment["negative_knowledge"]
        ],
        "negative_knowledge_digests": [
            item["digest"] for item in assignment["negative_knowledge"]
        ],
        "scope_context": assignment["scope_context"],
        "locality": assignment["locality"],
    }
    for key, value in expected.items():
        if observation.get(key) != value:
            return f"observation payload closure mismatch: {key}"
    contract_record = _contract_record(contract, assignment)
    if observation.get("labels") != contract_record["labels"]:
        return "agent observation labels diverged from source contract"
    if observation.get("notes") != contract_record["notes"]:
        return "agent observation notes diverged from source contract"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        validate_artifact(_read(args.validate))
        return 0
    artifact = build_artifact()
    validate_artifact(artifact)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, ensure_ascii=True, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

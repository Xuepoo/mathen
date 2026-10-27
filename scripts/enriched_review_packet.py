# ruff: noqa: E501
"""Build and validate the research-only MTH-0185 enriched review packet.

The packet is a deterministic, offline enrichment of the accepted MTH-0174
task set and frozen MTH-0175 assignment protocol.  It copies small, local
evidence payloads from reviewed cards into every assignment so a reviewer does
not need to resolve an external reference.  Holdout task content is never
copied into packets; its isolation is represented only by boundary metadata.
No labels, human evidence, model output, or promotion decision is generated.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import random
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data/research-review/mth-0185-enriched-study.json"
NEGATIVE_KNOWLEDGE = ROOT / "data/negative-knowledge/contract-boundaries.json"
BENCHMARK_REF = "data/benchmark/mth-0174-cross-system.json"
STUDY_REF = "data/research-review/mth-0175-study.json"
ACCEPTED_BENCHMARK_DIGEST = (
    "sha256:0079440b630a7319b73d0934fd01610b2773854047ab62787a8b3560bfb0b2e1"
)
ACCEPTED_STUDY_DIGEST = (
    "sha256:df743e79fc96a8b0b3f7b6f8fc48880241ad903c18d8b46ae911af1b23ca553a"
)
SCHEMA_VERSION = "1.0"
PROTOCOL_VERSION = "mth-0185-enriched-review-v1"
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
CLAIM_TYPES = ("fact", "inference", "hypothesis", "analogy")
SYSTEMS = {
    "storage": ["sqlite", "postgresql", "duckdb"],
    "streaming": ["kafka", "temporal"],
    "orchestration": ["kubernetes", "airflow", "carryctx"],
    "isolation": ["firecracker", "git"],
}
CARD_EVIDENCE = {
    "sqlite": ["sqlite-appropriate-uses", "sqlite-architecture"],
    "postgresql": ["postgresql-architecture", "postgresql-mvcc"],
    "duckdb": ["duckdb-why"],
    "kafka": ["kafka-introduction", "kafka-repository-commit"],
    "temporal": ["temporal-source-commit", "temporal-server-architecture"],
    "kubernetes": ["kubernetes-architecture-doc", "kubernetes-controller-doc"],
    "airflow": ["airflow-source-commit", "airflow-architecture-doc"],
    "carryctx": ["carryctx-cli-fixed-commit", "carryctx-readme-fixed"],
    "firecracker": ["firecracker-design"],
    "git": ["git-data-model"],
}
TASK_SPECS = (
    ("task-01-storage-mechanism", "storage-mechanism", "train", "storage"),
    ("task-02-storage-mechanism", "storage-mechanism", "evaluation", "storage"),
    ("task-03-storage-mechanism", "storage-mechanism", "holdout", "storage"),
    ("task-04-stream-history", "stream-history", "train", "streaming"),
    ("task-05-stream-history", "stream-history", "evaluation", "streaming"),
    ("task-06-stream-history", "stream-history", "holdout", "streaming"),
    ("task-07-reconciliation", "reconciliation", "train", "orchestration"),
    ("task-08-reconciliation", "reconciliation", "evaluation", "orchestration"),
    ("task-09-reconciliation", "reconciliation", "holdout", "orchestration"),
    ("task-10-boundary-isolation", "boundary-isolation", "train", "isolation"),
    ("task-11-boundary-isolation", "boundary-isolation", "evaluation", "isolation"),
    ("task-12-boundary-isolation", "boundary-isolation", "holdout", "isolation"),
)


class PacketError(ValueError):
    """Raised when the enriched packet violates a research boundary."""


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(payload.encode()).hexdigest()


def file_digest(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _read(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise PacketError(f"cannot read JSON {path}: {error}") from error
    if not isinstance(value, dict):
        raise PacketError(f"{path} must contain an object")
    return value


def _opaque_key(seed: str, index: int) -> str:
    digest = hashlib.sha256(f"{seed}\0reviewer\0{index}".encode()).digest()
    return "blind-seat-" + "-".join(OPAQUE_WORDS[byte & 31] for byte in digest[:16])


def _packet_id(study_id: str, reviewer_key: str) -> str:
    return (
        "packet-"
        + hashlib.sha256(f"{study_id}\0{reviewer_key}".encode()).hexdigest()[:24]
    )


def _assignment_id(study_id: str, reviewer_key: str, task_id: str) -> str:
    value = f"{study_id}\0{reviewer_key}\0{task_id}"
    return "assignment-" + hashlib.sha256(value.encode()).hexdigest()[:24]


def _candidate(
    task: dict[str, Any], card_map: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    systems = task["systems"]
    if task["partition"] == "holdout":
        raise PacketError("holdout candidate content must not be materialized")
    statements = {
        "storage-mechanism": "The reviewed systems expose storage mechanisms whose deployment and consistency scope must be stated per system.",
        "stream-history": "The reviewed systems retain event or workflow history, with ordering and replay claims bounded to the cited mechanism.",
        "reconciliation": "The reviewed systems schedule or reconcile work through documented control or workflow mechanisms, without a universal convergence claim.",
        "boundary-isolation": "The reviewed systems define execution or object boundaries, without implying equivalent security or durability guarantees.",
    }
    claim_type = "inference" if task["replicate"] == 2 else "fact"
    evidence_ids = task["evidence_ids"]
    return {
        "candidate_id": f"candidate-{task['id']}",
        "statement": statements[task["task_key"]],
        "claim_type": claim_type,
        "proven": False,
        "scope": task["scope"],
        "system_ids": systems,
        "task_id": task["id"],
        "evidence_ids": evidence_ids,
        "source_ids": [f"system:{system}" for system in systems],
        "candidate_digest": canonical_digest(
            {
                "task_id": task["id"],
                "statement": statements[task["task_key"]],
                "claim_type": claim_type,
                "scope": task["scope"],
                "evidence_ids": evidence_ids,
            }
        ),
        "notes": "Authored review candidate; not a label, proof, model output, or promoted card.",
    }


def _local_evidence(
    task: dict[str, Any], cards: dict[str, dict[str, Any]]
) -> list[dict[str, Any]]:
    output = []
    by_id = {
        record["id"]: record
        for system in cards.values()
        for record in system.get("evidence", [])
    }
    for evidence_id in task["evidence_ids"]:
        system, local_id = evidence_id.split(":", 1)
        card = cards[system]
        evidence = by_id.get(local_id)
        if evidence is None:
            raise PacketError(f"missing local evidence {evidence_id}")
        excerpt = {
            "summary": card["summary"],
            "evidence_title": evidence["title"],
            "evidence_kind": evidence["kind"],
            "evidence_notes": evidence.get("notes", ""),
        }
        output.append(
            {
                "evidence_id": evidence_id,
                "card_id": system,
                "source_id": f"system:{system}",
                "claim_type": "fact",
                "source_ref": f"data/systems/{system}.json#evidence/{local_id}",
                "excerpt": excerpt,
                "excerpt_digest": canonical_digest(excerpt),
            }
        )
    return output


def _negative_refs(
    negative: dict[str, Any], task: dict[str, Any]
) -> list[dict[str, str]]:
    refs = []
    for item in negative["counterexamples"]:
        refs.append(
            {
                "negative_knowledge_id": negative["id"],
                "reference_id": item["id"],
                "claim_type": item["claim_type"],
                "digest": canonical_digest(item),
            }
        )
    if task["partition"] == "holdout":
        refs.append(
            {
                "negative_knowledge_id": "mth-0174-holdout-boundary",
                "reference_id": task["id"],
                "claim_type": "hypothesis",
                "digest": canonical_digest(
                    {"task_id": task["id"], "boundary": "holdout content withheld"}
                ),
            }
        )
    return refs


def build_packet() -> dict[str, Any]:
    negative = _read(NEGATIVE_KNOWLEDGE)
    cards = {
        system: _read(ROOT / f"data/systems/{system}.json") for system in CARD_EVIDENCE
    }
    source_digests = {
        "benchmark": ACCEPTED_BENCHMARK_DIGEST,
        "frozen_study": ACCEPTED_STUDY_DIGEST,
        "negative_knowledge": file_digest(NEGATIVE_KNOWLEDGE),
        **{
            f"card:{system}": file_digest(ROOT / f"data/systems/{system}.json")
            for system in sorted(cards)
        },
    }
    seed = "mth-0185-enriched-seed-1"
    reviewer_keys = [_opaque_key(seed, index) for index in range(2)]
    benchmark_tasks = []
    for task_id, task_key, partition, domain in TASK_SPECS:
        systems = SYSTEMS[domain]
        evidence_ids = [
            f"{system}:{evidence_id}"
            for system in systems
            for evidence_id in CARD_EVIDENCE[system]
        ]
        benchmark_tasks.append(
            {
                "id": task_id,
                "task_key": task_key,
                "replicate": {"train": 1, "evaluation": 2, "holdout": 3}[partition],
                "partition": partition,
                "domain": domain,
                "systems": systems,
                "evidence_ids": evidence_ids,
                "scope": {
                    "systems": systems,
                    "workload": "authored cross-system architecture exploration",
                    "time": "frozen reviewed-card snapshot",
                    "deployment": "offline review fixture",
                },
            }
        )
    tasks = [task for task in benchmark_tasks if task["partition"] != "holdout"]
    task_map = {}
    for task in tasks:
        candidate = _candidate(task, cards)
        evidence = _local_evidence(task, cards)
        task_map[task["id"]] = {
            "task_id": task["id"],
            "domain_id": task["domain"],
            "partition": task["partition"],
            "candidate": candidate,
            "evidence": evidence,
            "negative_knowledge": _negative_refs(negative, task),
            "locality": {
                "candidate_evidence_local": True,
                "candidate_evidence_ids": task["evidence_ids"],
                "source_ids": candidate["source_ids"],
                "source_digest": canonical_digest(source_digests),
            },
        }
    packets = []
    for packet_index, reviewer_key in enumerate(reviewer_keys):
        ordered = list(tasks)
        random.Random(
            int(hashlib.sha256(f"{seed}\0{reviewer_key}".encode()).hexdigest(), 16)
        ).shuffle(ordered)
        assignments = []
        for order, task in enumerate(ordered, 1):
            material = task_map[task["id"]]
            assignments.append(
                {
                    "assignment_id": _assignment_id(
                        "mth-0185-enriched", reviewer_key, task["id"]
                    ),
                    "reviewer_key": reviewer_key,
                    "task_id": task["id"],
                    "domain_id": task["domain"],
                    "partition": task["partition"],
                    "order": order,
                    "candidate": material["candidate"],
                    "evidence": material["evidence"],
                    "negative_knowledge": material["negative_knowledge"],
                    "scope_context": material["candidate"]["scope"],
                    "locality": material["locality"],
                }
            )
        packets.append(
            {
                "packet_id": _packet_id("mth-0185-enriched", reviewer_key),
                "packet_label": ["A", "B"][packet_index],
                "reviewer_key": reviewer_key,
                "assignments": assignments,
                "review_records": [],
            }
        )
    all_holdout = [
        task["id"] for task in benchmark_tasks if task["partition"] == "holdout"
    ]
    return {
        "study_kind": "blinded_enriched_reviewer_study",
        "schema_version": SCHEMA_VERSION,
        "protocol_version": PROTOCOL_VERSION,
        "study_id": "mth-0185-enriched-study",
        "research_only": True,
        "purpose": "Supply each blind reviewer with a self-contained candidate and local evidence payload while preserving holdout isolation.",
        "frozen_inputs": {
            "benchmark_ref": BENCHMARK_REF,
            "benchmark_version": "mth-0174-v1",
            "study_ref": STUDY_REF,
            "study_version": "mth-0175-reviewer-study-v1",
            "negative_knowledge_ref": "data/negative-knowledge/contract-boundaries.json",
            "source_digests": source_digests,
            "source_digest_semantics": "Digests identify packet inputs; candidate and evidence digests identify payloads and excerpts separately.",
        },
        "reproducibility": {
            "assignment_seed": seed,
            "reviewer_count": 2,
            "generated_at": "not-recorded",
        },
        "reviewer_pool": {
            "count": 2,
            "independent": True,
            "identity_visibility": "opaque",
            "reviewer_keys": reviewer_keys,
        },
        "balance": {
            "balanced": True,
            "packet_labels": ["A", "B"],
            "tasks_per_reviewer": len(tasks),
            "overlap_policy": "all-reviewers-review-all-non-holdout-tasks",
            "domain_task_counts": {
                domain: sum(task["domain"] == domain for task in tasks)
                for domain in sorted({task["domain"] for task in tasks})
            },
        },
        "holdout_isolation": {
            "partition": "holdout",
            "task_ids": all_holdout,
            "candidate_content_in_packets": False,
            "evidence_content_in_packets": False,
            "negative_knowledge_content_in_packets": False,
            "allowed_reference": "opaque boundary reference only",
            "reason": "Holdout prompts and evidence are withheld to prevent leakage into review packets.",
        },
        "instructions": [
            "Review only the assigned candidate and local evidence payload.",
            "Do not infer or request holdout content; holdout tasks are withheld.",
            "Record unknown when supplied material does not support a judgment.",
            "Review independently; reviewer identity and packet labels remain opaque.",
            "These observations do not promote a candidate or canonical card.",
        ],
        "packets": packets,
        "review_records": [],
        "results": {
            "status": "not-started",
            "agreement": "not-determined",
            "promotion_decision": "not-determined",
        },
        "non_claims": [
            "No human labels, human evidence, LLM output, empirical result, or promotion is included.",
            "Candidate and evidence payloads are research fixtures, not canonical cards or proofs.",
        ],
    }


def validate_packet(packet: dict[str, Any]) -> None:
    if packet != build_packet():
        raise PacketError("fixture differs from deterministic builder output")
    if packet["results"]["promotion_decision"] != "not-determined":
        raise PacketError("promotion must remain not-determined")
    if len(packet["packets"]) != 2 or packet["balance"]["packet_labels"] != ["A", "B"]:
        raise PacketError("exactly balanced opaque packets A/B are required")
    holdout = packet["holdout_isolation"]
    if any(
        holdout[key]
        for key in (
            "candidate_content_in_packets",
            "evidence_content_in_packets",
            "negative_knowledge_content_in_packets",
        )
    ):
        raise PacketError("holdout content leaked into packet")
    expected = set(range(1, packet["balance"]["tasks_per_reviewer"] + 1))
    for item in packet["packets"]:
        if {assignment["order"] for assignment in item["assignments"]} != expected:
            raise PacketError("assignment order is not contiguous")
        for assignment in item["assignments"]:
            candidate = assignment["candidate"]
            if candidate["claim_type"] not in CLAIM_TYPES or candidate["proven"]:
                raise PacketError("candidate claim contract is invalid")
            if candidate["candidate_digest"] != canonical_digest(
                {
                    "task_id": candidate["task_id"],
                    "statement": candidate["statement"],
                    "claim_type": candidate["claim_type"],
                    "scope": candidate["scope"],
                    "evidence_ids": candidate["evidence_ids"],
                }
            ):
                raise PacketError("candidate digest mismatch")
            for evidence in assignment["evidence"]:
                excerpt = evidence["excerpt"]
                if evidence["excerpt_digest"] != canonical_digest(excerpt):
                    raise PacketError("evidence excerpt digest mismatch")
            if not assignment["locality"]["candidate_evidence_local"]:
                raise PacketError("candidate/evidence locality must be explicit")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        validate_packet(_read(args.validate))
    else:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(build_packet(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

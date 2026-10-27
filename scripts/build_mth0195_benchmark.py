# ruff: noqa: E501
"""Build and validate the MTH-0195 independent exploration task set.

This is an offline, research-only artifact.  It reads reviewed cards and
negative-knowledge evidence, freezes their byte digests, and emits authored
tasks.  It never calls a model, evaluates a candidate, or changes a card.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = Path("data/benchmark/mth-0195-independent-exploration.json")
SCHEMA_VERSION = "1.0"

CARD_IDS = (
    "airflow",
    "carryctx",
    "crossplane",
    "duckdb",
    "firecracker",
    "git",
    "kafka",
    "kubernetes",
    "postgresql",
    "sqlite",
    "temporal",
)

SOURCE_REFS = (
    (
        "mth-0118-contract",
        "docs/mth-0118-benchmark-harness.md",
        "research-only benchmark and candidate boundary",
    ),
    (
        "scope-context-contract",
        "docs/scope-context-contract.md",
        "scope and evidence preservation contract",
    ),
    (
        "contract-boundaries",
        "data/negative-knowledge/contract-boundaries.json",
        "reviewed negative-knowledge boundary record",
    ),
)

CARD_EVIDENCE = {
    "sqlite": (
        "sqlite-appropriate-uses",
        "sqlite-architecture",
        "sqlite-wal",
        "sqlite-atomic-commit",
    ),
    "postgresql": (
        "postgresql-architecture",
        "postgresql-mvcc",
        "postgresql-transaction-isolation",
    ),
    "duckdb": ("duckdb-why",),
    "kafka": ("kafka-introduction", "kafka-repository-commit"),
    "temporal": (
        "temporal-server-architecture",
        "temporal-workflow-execution",
        "temporal-determinism",
        "temporal-task-queues",
    ),
    "kubernetes": (
        "kubernetes-architecture-doc",
        "kubernetes-controller-doc",
        "kubernetes-controller-source",
    ),
    "airflow": (
        "airflow-architecture-doc",
        "airflow-source-commit",
        "airflow-executor-doc",
    ),
    "crossplane": (
        "crossplane-composition-doc",
        "crossplane-composition-source",
        "crossplane-managed-doc",
        "crossplane-managed-source",
    ),
    "firecracker": ("firecracker-design",),
    "git": ("git-data-model",),
    "carryctx": (
        "carryctx-readme-fixed",
        "carryctx-vcs-backend-source",
        "carryctx-worktrees-doc",
        "carryctx-merge-design-doc",
    ),
}

# Each row is a different question, evidence slice, and input.  The partition
# is part of the authored protocol, not a post-hoc label on a repeated key.
TASK_SPECS = (
    (
        "storage-local-transaction",
        "storage",
        "positive",
        "train",
        ("sqlite", "postgresql"),
        (
            "sqlite-appropriate-uses",
            "sqlite-architecture",
            "postgresql-architecture",
            "postgresql-mvcc",
        ),
        "Identify bounded local and client/server transaction mechanisms without merging their deployment scopes.",
        "positive-evidence",
    ),
    (
        "storage-replay-analytics",
        "storage",
        "positive",
        "train",
        ("sqlite", "duckdb"),
        ("sqlite-wal", "duckdb-why"),
        "Contrast SQLite's WAL reader snapshot with DuckDB's embedded analytical execution using only cited evidence.",
        "positive-evidence",
    ),
    (
        "storage-embedded-composition",
        "storage",
        "composition",
        "evaluation",
        ("sqlite", "duckdb"),
        ("sqlite-architecture", "sqlite-wal", "duckdb-why"),
        "Draft a bounded SQLite-to-DuckDB analytical handoff candidate; state the interface, workload, and unverified obligations.",
        "candidate",
    ),
    (
        "storage-universal-isolation",
        "storage",
        "negative",
        "holdout",
        ("sqlite", "postgresql", "duckdb"),
        (
            "sqlite-wal",
            "postgresql-transaction-isolation",
            "duckdb-why",
            "contract-review",
        ),
        "Does a shared storage interface establish one universal isolation guarantee across these systems?",
        "abstain-boundary",
    ),
    (
        "storage-cross-file-snapshot",
        "storage",
        "unknown",
        "holdout",
        ("sqlite", "duckdb"),
        ("sqlite-wal", "sqlite-atomic-commit", "duckdb-why", "contract-review"),
        "Is a crash-consistent snapshot preserved when SQLite WAL state and a separate DuckDB file are read as one unit?",
        "unknown",
    ),
    (
        "storage-wal-order-counterexample",
        "storage",
        "counterexample",
        "holdout",
        ("sqlite",),
        ("sqlite-wal", "contract-review"),
        "Give a bounded counterexample to treating a SQLite WAL reader snapshot as a cross-file or global total-order guarantee.",
        "counterexample",
    ),
    (
        "stream-kafka-replay",
        "streaming",
        "positive",
        "train",
        ("kafka",),
        ("kafka-introduction", "kafka-repository-commit"),
        "Locate the bounded retention and replay mechanism in Kafka and name the ordering scope it actually documents.",
        "positive-evidence",
    ),
    (
        "stream-temporal-history",
        "streaming",
        "positive",
        "train",
        ("temporal",),
        (
            "temporal-server-architecture",
            "temporal-workflow-execution",
            "temporal-determinism",
        ),
        "Locate Temporal's workflow-history and deterministic-replay boundary without treating it as a generic event log.",
        "positive-evidence",
    ),
    (
        "stream-workflow-composition",
        "streaming",
        "composition",
        "evaluation",
        ("kafka", "temporal"),
        ("kafka-introduction", "temporal-server-architecture", "temporal-task-queues"),
        "Draft a bounded Kafka-to-Temporal event handoff candidate and list delivery, ordering, and replay obligations that remain untested.",
        "candidate",
    ),
    (
        "stream-global-order",
        "streaming",
        "negative",
        "holdout",
        ("kafka", "temporal"),
        ("kafka-introduction", "temporal-workflow-execution", "contract-review"),
        "Does retained Kafka or Temporal history establish one total order across every partition, consumer, and workflow?",
        "abstain-boundary",
    ),
    (
        "stream-cross-history",
        "streaming",
        "unknown",
        "holdout",
        ("kafka", "temporal"),
        (
            "kafka-introduction",
            "temporal-workflow-execution",
            "temporal-determinism",
            "contract-review",
        ),
        "Is replay behavior equivalent when a Kafka event stream is used to trigger a Temporal workflow across retries and version changes?",
        "unknown",
    ),
    (
        "stream-partition-counterexample",
        "streaming",
        "counterexample",
        "holdout",
        ("kafka",),
        ("kafka-introduction", "contract-review"),
        "Give a bounded counterexample to upgrading Kafka per-partition ordering into a topic-wide total order.",
        "counterexample",
    ),
    (
        "orchestration-kubernetes-reconcile",
        "orchestration",
        "positive",
        "train",
        ("kubernetes",),
        (
            "kubernetes-architecture-doc",
            "kubernetes-controller-doc",
            "kubernetes-controller-source",
        ),
        "Describe Kubernetes controller reconciliation as an evidence-backed control-loop mechanism, not a convergence proof.",
        "positive-evidence",
    ),
    (
        "orchestration-airflow-dag",
        "orchestration",
        "positive",
        "train",
        ("airflow",),
        ("airflow-architecture-doc", "airflow-source-commit", "airflow-executor-doc"),
        "Describe Airflow's DAG scheduling and executor boundary while preserving its workload and deployment scope.",
        "positive-evidence",
    ),
    (
        "orchestration-provider-composition",
        "orchestration",
        "composition",
        "evaluation",
        ("kubernetes", "crossplane"),
        (
            "kubernetes-controller-doc",
            "crossplane-composition-doc",
            "crossplane-composition-source",
            "crossplane-managed-doc",
        ),
        "Draft a bounded Kubernetes-Crossplane managed-resource composition candidate with explicit provider and reconciliation obligations.",
        "candidate",
    ),
    (
        "orchestration-convergence-proof",
        "orchestration",
        "negative",
        "holdout",
        ("kubernetes", "airflow", "crossplane"),
        (
            "kubernetes-controller-doc",
            "airflow-architecture-doc",
            "crossplane-managed-doc",
            "contract-review",
        ),
        "Does the presence of a reconciliation or scheduling loop prove convergence under every failure condition?",
        "abstain-boundary",
    ),
    (
        "orchestration-exactly-once",
        "orchestration",
        "unknown",
        "holdout",
        ("kubernetes", "airflow"),
        ("kubernetes-controller-doc", "airflow-executor-doc", "contract-review"),
        "Is exactly-once execution preserved when Airflow work is launched through a Kubernetes control path?",
        "unknown",
    ),
    (
        "orchestration-reconcile-counterexample",
        "orchestration",
        "counterexample",
        "holdout",
        ("kubernetes", "crossplane"),
        ("kubernetes-controller-doc", "crossplane-managed-doc", "contract-review"),
        "Give a bounded counterexample in which reconciliation runs but unresolved conflict or non-idempotent behavior prevents a convergence claim.",
        "counterexample",
    ),
    (
        "boundary-firecracker",
        "isolation",
        "positive",
        "train",
        ("firecracker",),
        ("firecracker-design",),
        "Describe Firecracker's deliberately minimal machine boundary and its stated target workload without inferring a universal security result.",
        "positive-evidence",
    ),
    (
        "boundary-carryctx-worktree",
        "isolation",
        "positive",
        "train",
        ("carryctx", "git"),
        ("carryctx-vcs-backend-source", "carryctx-worktrees-doc", "git-data-model"),
        "Contrast CarryCtx worktree coordination with Git object storage without equating workspace scope with object isolation.",
        "positive-evidence",
    ),
    (
        "boundary-collaboration-composition",
        "isolation",
        "composition",
        "evaluation",
        ("carryctx", "git"),
        ("carryctx-merge-design-doc", "carryctx-vcs-backend-source", "git-data-model"),
        "Draft a bounded CarryCtx-Git collaboration composition candidate and state its merge, provenance, and workspace obligations.",
        "candidate",
    ),
    (
        "boundary-formal-security",
        "isolation",
        "negative",
        "holdout",
        ("firecracker", "git", "carryctx"),
        (
            "firecracker-design",
            "git-data-model",
            "carryctx-worktrees-doc",
            "contract-review",
        ),
        "Does naming an execution, object, or workspace boundary establish a formal security or correctness proof?",
        "abstain-boundary",
    ),
    (
        "boundary-cross-layer-isolation",
        "isolation",
        "unknown",
        "holdout",
        ("firecracker", "git"),
        ("firecracker-design", "git-data-model", "contract-review"),
        "Would a Git repository inside a Firecracker microVM preserve a single isolation contract across host, VM, filesystem, and object layers?",
        "unknown",
    ),
    (
        "boundary-reference-counterexample",
        "isolation",
        "counterexample",
        "holdout",
        ("git",),
        ("git-data-model", "contract-review"),
        "Give a bounded counterexample to treating Git's mutable references as immutable content-addressed objects.",
        "counterexample",
    ),
)


def canonical_digest(value: Any) -> str:
    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return f"sha256:{hashlib.sha256(payload.encode()).hexdigest()}"


def file_digest(relative_path: str) -> str:
    return (
        f"sha256:{hashlib.sha256((REPO_ROOT / relative_path).read_bytes()).hexdigest()}"
    )


def load_cards() -> dict[str, dict[str, Any]]:
    return {
        card_id: json.loads(
            (REPO_ROOT / "data/systems" / f"{card_id}.json").read_text(encoding="utf-8")
        )
        for card_id in CARD_IDS
    }


def source_revisions() -> list[dict[str, str]]:
    revisions = [
        {"id": ident, "source_ref": path, "digest": file_digest(path), "scope": scope}
        for ident, path, scope in SOURCE_REFS
    ]
    revisions.append(
        {
            "id": "reviewed-cards",
            "source_ref": "data/systems/*.json",
            "digest": canonical_digest(
                {
                    card_id: file_digest(f"data/systems/{card_id}.json")
                    for card_id in CARD_IDS
                }
            ),
            "scope": "frozen reviewed Architecture Cards used as references only",
        }
    )
    return revisions


def evidence_records(cards: dict[str, dict[str, Any]]) -> list[dict[str, str]]:
    records: list[dict[str, str]] = []
    for card_id in sorted(CARD_IDS):
        by_id = {item["id"]: item for item in cards[card_id].get("evidence", [])}
        for evidence_id in CARD_EVIDENCE[card_id]:
            item = by_id[evidence_id]
            records.append(
                {
                    "id": f"{card_id}:{evidence_id}",
                    "card_id": card_id,
                    "card_evidence_id": evidence_id,
                    "source_revision_id": "reviewed-cards",
                    "kind": item["kind"],
                    "claim_type": "fact",
                    "description": f"{item['title']}; frozen reviewed-card reference only.",
                }
            )
    records.append(
        {
            "id": "negative-knowledge:contract-review",
            "card_id": "negative-knowledge",
            "card_evidence_id": "contract-review",
            "source_revision_id": "contract-boundaries",
            "kind": "secondary",
            "claim_type": "inference",
            "description": "Reviewed bounded contract boundary; not a universal theorem.",
        }
    )
    return records


def build_tasks(
    cards: dict[str, dict[str, Any]],
    evidence: list[dict[str, str]],
    revisions: list[dict[str, str]],
) -> list[dict[str, Any]]:
    evidence_lookup = {
        (row["card_id"], row["card_evidence_id"]): row["id"] for row in evidence
    }
    source_by_id = {row["id"]: row for row in revisions}
    card_digests = {
        card_id: file_digest(f"data/systems/{card_id}.json") for card_id in CARD_IDS
    }
    tasks = []
    for index, (
        task_key,
        domain,
        kind,
        partition,
        systems,
        evidence_ids,
        question,
        answer_contract,
    ) in enumerate(TASK_SPECS, 1):
        task_evidence = []
        for evidence_id in evidence_ids:
            if evidence_id == "contract-review":
                task_evidence.append("negative-knowledge:contract-review")
                continue
            owners = [
                system for system in systems if (system, evidence_id) in evidence_lookup
            ]
            if len(owners) != 1:
                raise ValueError(
                    f"{task_key}: evidence {evidence_id!r} is not unique to its systems"
                )
            task_evidence.append(evidence_lookup[(owners[0], evidence_id)])
        source_revision_ids = ["mth-0118-contract", "scope-context-contract"]
        if kind in {"negative", "unknown", "counterexample"}:
            source_revision_ids.append("contract-boundaries")
        task_sources = {
            source_id: source_by_id[source_id]["digest"]
            for source_id in source_revision_ids
        }
        task_cards = [
            {
                "system_id": system,
                "path": f"data/systems/{system}.json",
                "digest": card_digests[system],
            }
            for system in systems
        ]
        input_payload = {
            "question": question,
            "systems": systems,
            "evidence_ids": task_evidence,
            "kind": kind,
            "partition": partition,
        }
        task = {
            "id": f"task-{index:02d}-{task_key}",
            "task_key": task_key,
            "kind": kind,
            "partition": partition,
            "domain": domain,
            "systems": list(systems),
            "question": question,
            "input_text": f"{domain} {' '.join(systems)} {' '.join(evidence_ids)} {answer_contract}",
            "input_digest": canonical_digest(input_payload),
            "source_revision_ids": source_revision_ids,
            "source_digest": canonical_digest(task_sources),
            "card_digests": task_cards,
            "evidence_ids": task_evidence,
            "negative_knowledge": kind in {"negative", "counterexample"},
            "candidate_generation_allowed": kind in {"positive", "composition"},
            "answer_contract": answer_contract,
            "scope": {
                "systems": list(systems),
                "workload": "authored cross-system architecture exploration",
                "time": "frozen reviewed-card snapshot",
                "deployment": "offline research fixture",
            },
        }
        tasks.append(task)
    return tasks


def empty_metric(name: str) -> dict[str, Any]:
    return {
        "name": name,
        "numerator": 0,
        "denominator": 0,
        "value": None,
        "status": "not-evaluated",
        "reason": "No reviewer labels, model outputs, or prototype runs are included in this authored task set.",
    }


def build_manifest() -> dict[str, Any]:
    cards = load_cards()
    revisions = source_revisions()
    evidence = evidence_records(cards)
    tasks = build_tasks(cards, evidence, revisions)
    partitions = {
        partition: [task["id"] for task in tasks if task["partition"] == partition]
        for partition in ("train", "evaluation", "holdout")
    }
    card_digests = [
        {
            "system_id": card_id,
            "path": f"data/systems/{card_id}.json",
            "digest": file_digest(f"data/systems/{card_id}.json"),
        }
        for card_id in sorted(CARD_IDS)
    ]
    domain_slices = []
    for domain in sorted({task["domain"] for task in tasks}):
        domain_tasks = [task for task in tasks if task["domain"] == domain]
        systems = sorted(
            {system for task in domain_tasks for system in task["systems"]}
        )
        domain_slices.append(
            {
                "domain": domain,
                "system_ids": systems,
                "task_ids": [task["id"] for task in domain_tasks],
                "digest": canonical_digest(
                    {
                        "domain": domain,
                        "system_ids": systems,
                        "task_ids": [task["id"] for task in domain_tasks],
                    }
                ),
            }
        )
    negative_ids = [task["id"] for task in tasks if task["negative_knowledge"]]
    excluded_ids = [
        task["id"] for task in tasks if not task["candidate_generation_allowed"]
    ]
    reviewed_card_digest_map = {
        item["system_id"]: item["digest"] for item in card_digests
    }
    evidence_digest = canonical_digest(evidence)
    return {
        "schema_version": SCHEMA_VERSION,
        "benchmark_id": "mth-0195-independent-cross-system-exploration",
        "protocol_version": "mth-0195-v1",
        "research_only": True,
        "purpose": "Author independent, evidence-bounded cross-system exploration tasks without asserting empirical results or superiority.",
        "source_revisions": revisions,
        "reviewed_card_digests": card_digests,
        "reviewed_cards_digest": canonical_digest(reviewed_card_digest_map),
        "task_cards": tasks,
        "task_card_digests": [
            {"id": task["id"], "digest": canonical_digest(task)} for task in tasks
        ],
        "domain_slices": domain_slices,
        "evidence_bundle": {
            "id": "mth-0195-frozen-reviewed-evidence",
            "records": evidence,
            "digest": evidence_digest,
            "source_revision_digests": {
                revision["id"]: revision["digest"] for revision in revisions
            },
        },
        "partitions": {
            "sets": partitions,
            "exhaustive": True,
            "disjoint": True,
            "digest": canonical_digest(partitions),
        },
        "negative_knowledge": {
            "holdout_ids": negative_ids,
            "candidate_generation_exclusions": excluded_ids,
            "source_ids": ["contract-boundaries"],
            "exclusion_reason": "Negative, unknown, and counterexample tasks are held out from candidate generation; negative-knowledge boundaries are never candidate labels.",
        },
        "candidate_contract": {
            "proven": False,
            "claim_status": "proposed",
            "canonical": False,
            "promotion_requires_human_review": True,
        },
        "conditions": [
            {
                "id": "bounded-lexical",
                "kind": "discovery",
                "status": "protocol-defined",
                "definition": "Normalized unique token overlap with deterministic ordering, positive scores only, and bounded top-k=10.",
                "input_partition": "evaluation",
                "output_bound": 10,
                "provenance": {
                    "provider": None,
                    "exact_model_id": None,
                    "prompt_digest": None,
                    "input_bundle_digest": evidence_digest,
                },
                "secret_safe_output": True,
            },
            {
                "id": "structured-evidence-bounded",
                "kind": "synthesis",
                "status": "protocol-defined",
                "definition": "Future candidates preserve task-specific evidence IDs, typed claims, scope, task kind, and proven=false.",
                "input_partition": "evaluation",
                "output_bound": 10,
                "provenance": {
                    "provider": "deterministic-fixture",
                    "exact_model_id": "none",
                    "prompt_digest": None,
                    "input_bundle_digest": evidence_digest,
                },
                "secret_safe_output": True,
            },
            {
                "id": "direct-llm",
                "kind": "direct-llm",
                "status": "not-evaluated",
                "definition": "Direct-LLM evaluation requires exact provider, model, prompt, input, runtime, and secret-safe output provenance.",
                "input_partition": "evaluation",
                "output_bound": 10,
                "provenance": {
                    "provider": None,
                    "exact_model_id": None,
                    "prompt_digest": None,
                    "input_bundle_digest": None,
                    "runtime_digest": None,
                },
                "secret_safe_output": False,
                "not_evaluated_reason": "No model, prompt, runtime provenance, or model output was supplied.",
            },
        ],
        "future_hooks": {
            "reviewer_labels": {
                "status": "reserved",
                "artifact": None,
                "expected_fields": [
                    "task_id",
                    "candidate_id",
                    "label",
                    "reviewer_id_digest",
                ],
            },
            "llm_runs": {
                "status": "reserved",
                "artifact": None,
                "required_provenance": [
                    "provider",
                    "exact_model_id",
                    "prompt_digest",
                    "input_bundle_digest",
                    "runtime_digest",
                ],
            },
            "prototype_runs": {
                "status": "reserved",
                "artifact": None,
                "expected_fields": [
                    "task_id",
                    "implementation_digest",
                    "run_digest",
                    "result_status",
                ],
            },
        },
        "metrics": [
            empty_metric(name)
            for name in (
                "evidence_locality",
                "claim_discipline",
                "scope_preservation",
                "false_link_rate",
                "abstention_rate",
                "counterexample_recall",
                "composition_obligation_satisfaction",
            )
        ],
        "review_budget": {
            "planned_reviewer_count": 2,
            "max_candidate_records": 48,
            "max_minutes": 150,
            "labeling_status": "not-started",
            "budget_is_not_result": True,
        },
        "non_claims": [
            "This authored task set does not measure truth, compatibility, causality, originality, production readiness, or model quality.",
            "Every task is an independent authored instance with its own question, evidence slice, input digest, and source/card digest; independence is a task-design property, not statistical power.",
            "Direct-LLM remains not-evaluated; no model output, reviewer label, empirical score, or superiority claim is asserted.",
            "Candidates remain proposed, non-canonical, and proven=false; a bounded composition candidate is not a compatibility proof.",
        ],
        "outcome": {
            "status": "not-evaluated",
            "reason": "The task set and provenance digests are frozen; labels, model outputs, and prototype results were intentionally not supplied.",
        },
    }


def validate_manifest(path: Path) -> None:
    value = json.loads(path.read_text(encoding="utf-8"))
    expected = build_manifest()
    if value != expected:
        raise ValueError(f"{path}: fixture differs from deterministic builder output")
    tasks = value["task_cards"]
    if len(tasks) != 24 or len({task["id"] for task in tasks}) != len(tasks):
        raise ValueError("MTH-0195 requires 24 unique task instances")
    if len({task["task_key"] for task in tasks}) != len(tasks):
        raise ValueError(
            "task keys must be unique; repeated keys are not independent instances"
        )
    if {task["kind"] for task in tasks} != {
        "positive",
        "negative",
        "unknown",
        "counterexample",
        "composition",
    }:
        raise ValueError("all five bounded task kinds are required")
    if {task["partition"] for task in tasks} != {"train", "evaluation", "holdout"}:
        raise ValueError("all partitions are required")
    sets = value["partitions"]["sets"]
    if set().union(*(set(ids) for ids in sets.values())) != {
        task["id"] for task in tasks
    } or sum(len(ids) for ids in sets.values()) != len(tasks):
        raise ValueError("partitions must be exhaustive and disjoint")
    if any(
        task["candidate_generation_allowed"]
        for task in tasks
        if task["partition"] == "holdout"
    ):
        raise ValueError("holdout tasks cannot allow candidate generation")
    negative = set(value["negative_knowledge"]["holdout_ids"])
    if negative != {task["id"] for task in tasks if task["negative_knowledge"]}:
        raise ValueError("negative-knowledge holdout IDs do not match task flags")
    if not negative <= set(sets["holdout"]):
        raise ValueError("negative-knowledge tasks must be holdout-only")
    if any(
        candidate["proven"] is not False for candidate in [value["candidate_contract"]]
    ):
        raise ValueError("candidate contract must retain proven=false")
    if any(
        metric["denominator"] != 0 or metric["value"] is not None
        for metric in value["metrics"]
    ):
        raise ValueError(
            "authored task metrics must retain zero denominators and null values"
        )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        validate_manifest(args.validate)
        return
    output = args.output if args.output.is_absolute() else REPO_ROOT / args.output
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(
        json.dumps(build_manifest(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

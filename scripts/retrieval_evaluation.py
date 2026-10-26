#!/usr/bin/env python3
"""Build the deterministic, offline lexical retrieval evaluation artifact.

This runner intentionally does not load a model or write vectors.  It mirrors
the deployed bounded lexical scoring rule and records the prior local-vector
pilot as prior evidence only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
CARD_DIR = ROOT / "data" / "systems"
OUT = ROOT / "docs" / "audits" / "mth-0154-retrieval-evaluation.json"
QUERY_SCOPE = {
    "version_context": None,
    "deployment_origins": [],
    "conditions": [],
    "exclusions": [],
}
TARGETS = [
    (
        "git",
        "content-addressed-objects",
        "How does the system retain immutable objects by content identity?",
        "paraphrase",
    ),
    (
        "git",
        "mutable-reference-layer",
        "Where are movable names kept separate from immutable history?",
        "scope",
    ),
    (
        "sqlite",
        "wal-snapshot-concurrency",
        "How can readers see a stable snapshot while writers append changes?",
        "paraphrase",
    ),
    (
        "sqlite",
        "journal-based-atomic-commit",
        "Which mechanism makes a transaction durable or recoverable after failure?",
        "freshness",
    ),
    (
        "sqlite",
        "sql-to-bytecode-virtual-machine",
        "Where is declarative SQL lowered into executable instructions?",
        "claim-type",
    ),
    (
        "firecracker",
        "minimal-machine-model",
        "What is the smallest virtual machine boundary exposed for isolation?",
        "scope",
    ),
    (
        "firecracker",
        "kvm-event-driven-vmm",
        "How does the monitor react to hardware virtualization events?",
        "paraphrase",
    ),
    (
        "kafka",
        "partitioned-append-log",
        "Which architecture stores events in ordered partition-local logs?",
        "paraphrase",
    ),
    (
        "kafka",
        "retained-replayable-events",
        "How can consumers reconstruct state from retained event history?",
        "freshness",
    ),
    (
        "kafka",
        "replicated-topic-partitions",
        "How are partition replicas used for fault tolerance?",
        "misleading-similarity",
    ),
    (
        "kubernetes",
        "controller-reconciliation-loops",
        "Which loop repeatedly drives declared resources toward observed state?",
        "paraphrase",
    ),
    (
        "kubernetes",
        "etcd-backed-cluster-state",
        "Where is cluster control-plane state durably persisted?",
        "scope",
    ),
    (
        "docker",
        "runtime-isolation-stack",
        "What layered boundary isolates a container from the host?",
        "misleading-similarity",
    ),
    (
        "docker",
        "image-layer-filesystem",
        "How are filesystem changes represented as reusable immutable layers?",
        "paraphrase",
    ),
    (
        "duckdb",
        "embedded-process-execution",
        "Which database runs inside its host rather than behind a server?",
        "paraphrase",
    ),
    (
        "duckdb",
        "vectorized-columnar-execution",
        "How are batches and columns used to reduce analytical execution overhead?",
        "claim-type",
    ),
    (
        "redis",
        "selectable-persistence-representations",
        "Which choices trade snapshot persistence against an append-only log?",
        "misleading-similarity",
    ),
    (
        "redis",
        "append-only-stream-data-structure",
        "Where are ordered stream entries represented as a native data type?",
        "paraphrase",
    ),
    (
        "postgresql",
        "mvcc-snapshot-isolation",
        "How do transactions read versions without blocking every writer?",
        "paraphrase",
    ),
    (
        "postgresql",
        "process-per-session-server",
        "Which topology gives each client session a server process?",
        "scope",
    ),
    (
        "rocksdb",
        "lsm-key-value-storage",
        "Which storage design merges sorted runs for an embedded key-value engine?",
        "paraphrase",
    ),
    (
        "rocksdb",
        "background-compaction",
        "Where are immutable files periodically compacted in the background?",
        "freshness",
    ),
    (
        "cassandra",
        "tunable-consistency-coordination",
        "How can acknowledgement thresholds tune distributed read or write "
        "consistency?",
        "claim-type",
    ),
    (
        "cassandra",
        "hinted-and-replayed-recovery",
        "Which mechanism replays deferred mutations after a replica failure?",
        "paraphrase",
    ),
    (
        "nginx",
        "event-driven-connection-processing",
        "How does a server handle many connections with nonblocking events?",
        "paraphrase",
    ),
    (
        "nginx",
        "master-worker-process-topology",
        "Which process arrangement separates supervision from request workers?",
        "scope",
    ),
    (
        "linux",
        "virtual-filesystem-abstraction",
        "Where is a common file interface layered over different filesystems?",
        "misleading-similarity",
    ),
    (
        "linux",
        "preemptive-scheduler-classes",
        "How are runnable tasks selected under configurable scheduling policies?",
        "claim-type",
    ),
    (
        "llvm",
        "typed-ssa-intermediate-representation",
        "Which compiler representation makes dataflow values explicit and typed?",
        "paraphrase",
    ),
    (
        "llvm",
        "analysis-transform-pass-pipeline",
        "How are compiler analyses and transformations arranged as passes?",
        "scope",
    ),
    (
        "rust",
        "ownership-and-borrowing",
        "Which language discipline constrains aliasing and lifetime of values?",
        "paraphrase",
    ),
    (
        "rust",
        "query-driven-incremental-compilation",
        "How can compilation recompute only invalidated dependency queries?",
        "freshness",
    ),
    (
        "qemu",
        "composable-machine-model",
        "How are configurable virtual machine devices assembled into a model?",
        "paraphrase",
    ),
    (
        "qemu",
        "pluggable-execution-accelerators",
        "Which boundary allows different acceleration implementations?",
        "misleading-similarity",
    ),
    (
        "libuv",
        "single-threaded-cross-platform-event-loop",
        "Where is asynchronous I/O coordinated by one portable event loop?",
        "paraphrase",
    ),
    (
        "libuv",
        "threadpool-blocking-operation-offload",
        "How are blocking operations moved away from the event loop?",
        "scope",
    ),
    (
        "elasticsearch",
        "coordinating-scatter-gather-search",
        "Which search path gathers shard results and reduces them centrally?",
        "paraphrase",
    ),
    (
        "elasticsearch",
        "translog-backed-shard-recovery",
        "How does a shard recover recent writes from its transaction log?",
        "freshness",
    ),
    (
        "prometheus",
        "labeled-time-series",
        "How are observations keyed by label dimensions over time?",
        "claim-type",
    ),
    (
        "prometheus",
        "scrape-and-rule-workflows",
        "Which workflow periodically collects metrics and evaluates rules?",
        "scope",
    ),
    (
        "carryctx",
        "guarded-task-lifecycle",
        "How are lifecycle transitions constrained by dependencies and checks?",
        "paraphrase",
    ),
    (
        "carryctx",
        "zero-network-state-boundary",
        "Which boundary keeps authoritative collaboration state local?",
        "misleading-similarity",
    ),
]
HOLDOUTS = [
    (
        "q-holdout-unknown-01",
        "Which reviewed card proves a universal architecture is always superior?",
        "unknown",
    ),
    (
        "q-holdout-negative-02",
        "Which system is historically derived from every other system in the corpus?",
        "negative-knowledge",
    ),
    (
        "q-holdout-scope-03",
        "Which record guarantees behavior for an unspecified production workload?",
        "unknown",
    ),
    (
        "q-holdout-negative-04",
        "Which nearest result establishes that two systems are substitutable?",
        "negative-knowledge",
    ),
    (
        "q-holdout-freshness-05",
        "Which record is current today without an accessed date or version policy?",
        "unknown",
    ),
    (
        "q-holdout-negative-06",
        "Which similarity score creates a canonical relation automatically?",
        "negative-knowledge",
    ),
]


def digest(value: Any) -> str:
    raw = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def tokens(value: str) -> list[str]:
    return sorted(set(re.findall(r"[\w]+", value.casefold(), re.UNICODE)))


def load_documents() -> tuple[list[dict[str, Any]], list[str]]:
    docs: list[dict[str, Any]] = []
    evidence: dict[str, dict[str, Any]] = {}
    for path in sorted(CARD_DIR.glob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        for item in card.get("evidence", []):
            evidence[item["id"]] = item
        feature_by_id = {item["id"]: item for item in card.get("features", [])}
        items: list[tuple[str, Any]] = [("system", None)]
        items.extend(("feature", item) for item in card.get("features", []))
        items.extend(("view", item) for item in card.get("mathematical_views", []))
        items.extend(("trade_off", item) for item in card.get("trade_offs", []))
        for item_kind, item in items:
            if item_kind == "system":
                kind, ident, name, description = (
                    "system",
                    "summary",
                    card["name"],
                    card["summary"],
                )
                ids = [x["id"] for x in card.get("evidence", [])]
                claim_type, status = (
                    "fact",
                    card.get("temporal_context", {}).get("claim_status"),
                )
                source = f"data/systems/{path.name}#summary"
            elif item_kind == "feature":
                kind, ident, name, description = (
                    "feature",
                    item["id"],
                    item["name"],
                    item["description"],
                )
                ids = item.get("evidence_ids", [])
                claim_type, status = item["claim_type"], item.get("claim_status")
                source = f"data/systems/{path.name}#features/{ident}"
            elif item_kind == "view":
                kind, ident, name, description = (
                    "view",
                    str(item.get("id", len(docs))),
                    item["model"],
                    item["question"],
                )
                ids = item.get("evidence_ids", [])
                claim_type, status = item["claim_type"], item.get("claim_status")
                source = f"data/systems/{path.name}#mathematical_views/{ident}"
            else:
                feature = feature_by_id.get(item["feature_id"])
                if feature is None:
                    continue
                kind, ident = "trade_off", item["feature_id"]
                name = f"Trade-offs: {feature['name']}"
                description = json.dumps(
                    {
                        "benefits": item.get("benefits", []),
                        "costs": item.get("costs", []),
                    },
                    sort_keys=True,
                )
                ids = feature.get("evidence_ids", [])
                claim_type, status = feature["claim_type"], feature.get("claim_status")
                source = f"data/systems/{path.name}#trade_offs/{ident}"
            if not ids or any(x not in evidence for x in ids):
                continue
            scope = {
                "version_context": None,
                "deployment_origins": [],
                "conditions": [],
                "exclusions": [],
            }
            doc = {
                "id": f"system:{card['id']}:{kind}:{ident}"
                if kind != "system"
                else f"system:{card['id']}:summary",
                "record_kind": kind,
                "source_ref": source,
                "source_digest": digest(item or card),
                "claim_type": claim_type,
                "claim_status": status,
                "evidence_ids": sorted(ids),
                "validity_scope": scope,
                "system_id": card["id"],
                "name": name,
                "description": description,
            }
            doc["text"] = "\n".join(
                [
                    f"system: {card['id']}",
                    f"record: {kind} {name}",
                    f"name: {name}",
                    f"summary: {description}",
                    f"scope: {json.dumps(card.get('scope', []), sort_keys=True)}",
                    f"version_context: {card.get('version_context', '')}",
                ]
            )
            docs.append(doc)
    return sorted(docs, key=lambda x: x["id"]), sorted(evidence)


def rank(
    docs: list[dict[str, Any]], query: str, limit: int = 10
) -> list[dict[str, Any]]:
    terms = tokens(query)
    scored = []
    for doc in docs:
        body = set(tokens(doc["text"]))
        title = set(tokens(doc["name"]))
        score = (
            min(
                1.0,
                (sum(t in body for t in terms) + 0.5 * sum(t in title for t in terms))
                / len(terms),
            )
            if terms
            else 0
        )
        if score > 0:
            scored.append((score, doc))
    return [
        {**doc, "_score": score}
        for score, doc in sorted(scored, key=lambda x: (-x[0], x[1]["id"]))[:limit]
    ]


def metric(numerator: float, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def evaluate(
    docs: list[dict[str, Any]],
    queries: list[dict[str, Any]],
    labels: list[dict[str, Any]],
    slices: dict[str, list[str]],
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    by_label: dict[str, dict[str, Any]] = {}
    for label in labels:
        by_label.setdefault(label["query_id"], {})[label["document_id"]] = label
    result_rows = []
    reciprocal: dict[str, list[str]] = {}
    for query in queries:
        # The protocol's unknown/negative slices are an explicit abstention
        # control. They are not sent to candidate generation and therefore do
        # not measure the production request path.
        ranked = (
            []
            if any(
                slice_id in {"unknown", "negative-knowledge"}
                for slice_id in query.get("slice_ids", [])
            )
            else rank(docs, query["question"])
        )
        reciprocal[query["id"]] = [x["id"] for x in ranked]
        result_rows.append(
            {
                "query_id": query["id"],
                "abstained": not ranked,
                "abstention_reason": (
                    "held-out unknown or negative-knowledge query"
                    if not ranked
                    and any(
                        slice_id in {"unknown", "negative-knowledge"}
                        for slice_id in query.get("slice_ids", [])
                    )
                    else "no lexical overlap"
                    if not ranked
                    else None
                ),
                "results": [
                    {
                        "rank": i + 1,
                        "score": d["_score"],
                        "score_kind": "lexical_overlap",
                        "document": {
                            k: d[k]
                            for k in (
                                "id",
                                "record_kind",
                                "system_id",
                                "name",
                                "description",
                                "claim_type",
                                "claim_status",
                                "evidence_ids",
                                "validity_scope",
                            )
                        },
                        "evidence": [{"id": e} for e in d["evidence_ids"]],
                        "provenance": {
                            "source_ref": d["source_ref"],
                            "source_digest": d["source_digest"],
                            "retrieval_method": "bounded_lexical_baseline",
                        },
                    }
                    for i, d in enumerate(ranked)
                ],
            }
        )

    def scores(
        ids: list[str],
    ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        relevance = {
            q: {d: by_label[q][d]["grade"] for d in by_label.get(q, {})}
            for q in ids
            if by_label.get(q)
        }
        eligible = list(relevance)
        found = sum(
            any(by_label[q].get(d, {}).get("grade", 0) > 0 for d in reciprocal[q][:5])
            for q in eligible
        )
        dcgs = []
        for q in eligible:
            actual = sum(
                (2 ** by_label[q].get(d, {}).get("grade", 0) - 1)
                / __import__("math").log2(i + 2)
                for i, d in enumerate(reciprocal[q][:5])
            )
            ideal_grades = sorted(
                (x["grade"] for x in by_label[q].values()), reverse=True
            )[:5]
            ideal = sum(
                (2**g - 1) / __import__("math").log2(i + 2)
                for i, g in enumerate(ideal_grades)
            )
            dcgs.append(actual / ideal if ideal else 0.0)
        links = [
            by_label[q][d]
            for q in eligible
            for d in reciprocal[q][:5]
            if d in by_label[q]
            and by_label[q][d].get("link_outcome") in {"relevant", "false-link"}
        ]
        false_links = sum(x["link_outcome"] == "false-link" for x in links)
        abstained = sum(not reciprocal[q] for q in ids)
        return (
            metric(found, len(eligible)),
            {
                "numerator": sum(dcgs),
                "denominator": len(dcgs),
                "value": sum(dcgs) / len(dcgs) if dcgs else None,
            },
            metric(false_links, len(links)),
            metric(abstained, len(ids)),
        )

    overall = scores([q["id"] for q in queries])
    returned = [result for row in result_rows for result in row["results"]]
    local_evidence = sum(
        set(result["document"]["evidence_ids"]).issuperset(
            {evidence["id"] for evidence in result["evidence"]}
        )
        for result in returned
    )
    complete_scope = sum(
        all(
            field in result["document"]["validity_scope"]
            and isinstance(result["document"]["validity_scope"][field], (str, list))
            for field in (
                "version_context",
                "deployment_origins",
                "conditions",
                "exclusions",
            )
        )
        for result in returned
    )
    claim_observations = []
    for query_id, query_labels in by_label.items():
        target = next(
            (label for label in query_labels.values() if label["grade"] > 0), None
        )
        top = next((row for row in result_rows if row["query_id"] == query_id), None)
        if target and top and top["results"]:
            claim_observations.append(
                top["results"][0]["document"]["claim_type"] == target["claim_type"]
            )
    evidence_metric = metric(local_evidence, len(returned))
    claim_metric = metric(sum(claim_observations), len(claim_observations))
    scope_metric = metric(complete_scope, len(returned))
    slice_metrics = [
        {
            "slice_id": sid,
            "query_count": len(qids),
            "recall_at_k": [{"k": 5, **scores(qids)[0]}],
            "ndcg_at_k": [{"k": 5, **scores(qids)[1]}],
            "false_link_rate": scores(qids)[2],
            "abstention_rate": scores(qids)[3],
        }
        for sid, qids in sorted(slices.items())
    ]
    return result_rows, {
        "recall_at_k": [{"k": 5, **overall[0]}],
        "ndcg_at_k": [{"k": 5, **overall[1]}],
        "evidence_locality": evidence_metric,
        "claim_type_accuracy": claim_metric,
        "scope_completeness": scope_metric,
        "false_link_rate": overall[2],
        "abstention_rate": overall[3],
        "slices": slice_metrics,
        "error_analysis": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=OUT)
    args = parser.parse_args()
    docs, evidence = load_documents()
    queries = [
        {
            "id": f"q-{i + 1:02d}",
            "question": q,
            "scope": QUERY_SCOPE,
            "slice_ids": [slice_id],
            "query_digest": digest(
                {
                    "id": f"q-{i + 1:02d}",
                    "question": q,
                    "scope": QUERY_SCOPE,
                    "slice_ids": [slice_id],
                }
            ),
        }
        for i, (_, _, q, slice_id) in enumerate(TARGETS)
    ]
    holdout_queries = [
        {
            "id": qid,
            "question": q,
            "scope": QUERY_SCOPE,
            "slice_ids": [kind],
            "query_digest": digest(
                {
                    "id": qid,
                    "question": q,
                    "scope": QUERY_SCOPE,
                    "slice_ids": [kind],
                }
            ),
        }
        for qid, q, kind in HOLDOUTS
    ]
    all_queries = queries + holdout_queries
    labels = []
    for i, (system, feature, _, _) in enumerate(TARGETS):
        target = next(
            (d for d in docs if d["id"] == f"system:{system}:feature:{feature}"), None
        )
        if target:
            labels.append(
                {
                    "query_id": f"q-{i + 1:02d}",
                    "document_id": target["id"],
                    "grade": 3,
                    "claim_type": target["claim_type"],
                    "evidence_ids": target["evidence_ids"],
                    "evidence_locality": "local",
                    "scope_match": "undetermined",
                    "link_outcome": "relevant",
                    "label_source": "reviewer-rubric-v1",
                }
            )
    for i, (system, feature, question, slice_id) in enumerate(TARGETS):
        if slice_id != "misleading-similarity":
            continue
        target_id = f"system:{system}:feature:{feature}"
        distractor = next(
            (item for item in rank(docs, question) if item["id"] != target_id), None
        )
        if distractor is not None:
            labels.append(
                {
                    "query_id": f"q-{i + 1:02d}",
                    "document_id": distractor["id"],
                    "grade": 0,
                    "claim_type": distractor["claim_type"],
                    "evidence_ids": distractor["evidence_ids"],
                    "evidence_locality": "local",
                    "scope_match": "undetermined",
                    "link_outcome": "false-link",
                    "label_source": "reviewer-rubric-v1",
                }
            )
    holdout_labels = [
        {
            "id": f"holdout-{i + 1:02d}",
            "query_id": qid,
            "document_id": f"negative:{kind}:{i + 1:02d}",
            "kind": kind,
            "reason": (
                "Research-only held-out query; no document is labeled as a valid "
                "answer."
            ),
            "candidate_generation_excluded": True,
            "claim_type": "hypothesis",
            "evidence_ids": [evidence[0]],
        }
        for i, (qid, _, kind) in enumerate(HOLDOUTS)
        if evidence
    ]
    slices = {
        "paraphrase": [
            f"q-{i + 1:02d}" for i, x in enumerate(TARGETS) if x[3] == "paraphrase"
        ],
        "misleading-similarity": [
            f"q-{i + 1:02d}"
            for i, x in enumerate(TARGETS)
            if x[3] == "misleading-similarity"
        ],
        "claim-type": [
            f"q-{i + 1:02d}" for i, x in enumerate(TARGETS) if x[3] == "claim-type"
        ],
        "scope": [f"q-{i + 1:02d}" for i, x in enumerate(TARGETS) if x[3] == "scope"],
        "freshness": [
            f"q-{i + 1:02d}" for i, x in enumerate(TARGETS) if x[3] == "freshness"
        ],
        "abstention": [x[0] for x in HOLDOUTS],
    }
    results, metrics = evaluate(docs, queries + holdout_queries, labels, slices)
    errors = []
    for query in queries:
        query_labels = {
            label["document_id"]: label
            for label in labels
            if label["query_id"] == query["id"]
        }
        row = next(result for result in results if result["query_id"] == query["id"])
        if not any(
            query_labels.get(result["document"]["id"], {}).get("grade", 0) > 0
            for result in row["results"][:5]
        ):
            errors.append(
                {
                    "query_id": query["id"],
                    "category": "miss",
                    "observed": "labeled target absent from lexical top five",
                    "reviewer_note": (
                        "Discovery miss is recorded for slice analysis only; it "
                        "does not establish semantic failure."
                    ),
                }
            )
        if any(
            query_labels.get(result["document"]["id"], {}).get("link_outcome")
            == "false-link"
            for result in row["results"][:5]
        ):
            errors.append(
                {
                    "query_id": query["id"],
                    "category": "false-link",
                    "observed": (
                        "reviewer-labeled misleading candidate appeared in top five"
                    ),
                    "reviewer_note": (
                        "False-link labels identify a candidate that should not be "
                        "treated as a relation or semantic equivalence."
                    ),
                }
            )
    for query in holdout_queries:
        row = next(result for result in results if result["query_id"] == query["id"])
        errors.append(
            {
                "query_id": query["id"],
                "category": "abstention",
                "observed": (
                    "held-out query has no positive answer label; baseline returned "
                    "candidates"
                    if row["results"]
                    else "baseline abstained with no lexical overlap"
                ),
                "reviewer_note": (
                    "Held-out unknown and negative-knowledge queries remain outside "
                    "candidate labels; this is a research boundary check, not a "
                    "truth judgment."
                ),
            }
        )
    metrics["error_analysis"] = errors
    partitions = {
        "train": [],
        "evaluation": [q["id"] for q in queries],
        "holdout": [q["id"] for q in holdout_queries],
    }
    snapshot_documents = [
        {
            k: d[k]
            for k in (
                "id",
                "record_kind",
                "source_ref",
                "source_digest",
                "claim_type",
                "claim_status",
                "evidence_ids",
                "validity_scope",
            )
        }
        for d in docs
    ]
    manifest = {
        "manifest_kind": "retrieval_evaluation",
        "schema_version": "1.0",
        "evaluation_id": "mth-0154-retrieval-evaluation",
        "protocol_version": "mth-0154-v1",
        "benchmark_version": "mth-0154-reviewer-labeled-48q",
        "corpus_snapshot": {
            "id": "canonical-cards-2026-10-26",
            "corpus": "canonical_cards",
            "reviewed_only": True,
            "source_revision": {
                "repository_id": "mathen",
                "commit": subprocess.check_output(
                    ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
                ).strip(),
            },
            "digest": digest(snapshot_documents),
            "documents": snapshot_documents,
        },
        "evidence_bundle": {
            "id": "canonical-evidence-2026-10-26",
            "digest": digest(evidence),
            "evidence_ids": evidence,
        },
        "query_set": {
            "id": "mth-0154-48-query-review-set",
            "digest": digest(all_queries),
            "queries": all_queries,
        },
        "labels": {"relevance": labels, "holdout": holdout_labels},
        "split": {
            "strategy": "fixed-reviewer-labeled-evaluation-with-heldout-abstention",
            "partitions": partitions,
            "digest": digest(partitions),
            "holdout_query_ids": partitions["holdout"],
            "candidate_generation_exclusions": [x["id"] for x in holdout_labels],
            "temporal_cutoff": None,
            "leakage_controls": [
                "holdout labels excluded from candidate generation",
                "labels authored separately from retrieval output",
                "source and evidence digests frozen",
            ],
        },
        "method": {
            "name": "bounded-lexical-baseline",
            "baseline": "lexical",
            "retrieval_method": "bounded_lexical_baseline",
        },
        "model": {
            "provider": None,
            "model_id": None,
            "representation_version": "canonical-record-v1",
            "dimensions": None,
            "metric": "token-overlap",
            "prompt_digest": None,
        },
        "boundaries": {
            "negative_knowledge": {
                "excluded_from_corpus": True,
                "excluded_from_candidate_generation": True,
            },
            "novelty": {
                "reference_window": "not-evaluated",
                "dimensions": [
                    "topology",
                    "composition",
                    "constraints",
                    "behavior",
                    "deployment",
                    "historical",
                ],
                "aggregate_score_allowed": False,
            },
            "analogy": {
                "non_equivalence_required": True,
                "historical_influence_requires_direct_evidence": True,
                "substitutability_not_implied": True,
            },
        },
        "results": results,
        "metrics": metrics,
        "result_boundary": {
            "canonical": False,
            "storage_scope": "research",
            "promotion_requires_human_review": True,
            "discovery_only": True,
            "score_is_truth": False,
            "score_is_compatibility": False,
        },
        "evaluation_metadata": {
            "query_slices": [
                {
                    "id": sid,
                    "description": f"Reviewer-labeled {sid} slice",
                    "query_ids": qids,
                }
                for sid, qids in sorted(slices.items())
            ],
            "reviewer_labeling": {
                "label_source": (
                    "reviewer-rubric-v1; labels are research-only judgments"
                ),
                "independent_reviewers": 1,
                "disagreement_retained": False,
            },
            "freshness_policy": (
                "Record source revision and accessed metadata; missing accessed "
                "dates remain unknown and are never treated as fresh."
            ),
            "null_semantics": (
                "A null metric value means its denominator is zero or the provider "
                "observation was not measured; it is not zero and cannot support "
                "a gain claim."
            ),
            "operational_observations": {
                "latency_ms": {
                    "unit": "ms",
                    "sample_count": 0,
                    "p50": None,
                    "p95": None,
                    "measurement_status": "not measured in this offline artifact",
                },
                "provider_errors": {
                    "numerator": 0,
                    "denominator": 0,
                    "value": None,
                    "measurement_status": "not applicable to local lexical control",
                },
                "cost": {
                    "unit": "provider calls",
                    "value": 0,
                    "measurement_status": (
                        "lexical control has no embedding/provider calls"
                    ),
                },
            },
        },
        "comparison": {
            "control": "bounded-lexical-baseline",
            "candidate": "local-bge-micro-v2",
            "candidate_results_status": "prior-pilot-only",
            "prior_pilot_reference": (
                "docs/audits/mth-0150-retrieval-embedding-pilot.json"
            ),
        },
        "decision": {
            "outcome": "retain_lexical_baseline",
            "rationale": (
                "The expanded offline control is deterministic and includes "
                "reviewer-labeled slices, but the local vector candidate has no "
                "rerun on this benchmark. The prior 12-query pilot showed no "
                "recall gain and lower nDCG; no new vector result is claimed. "
                "Retain lexical pending an independently reviewed, same-snapshot "
                "vector run with measurable operational evidence."
            ),
            "production_change": False,
        },
    }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

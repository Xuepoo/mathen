"""Research-only manifests and deterministic metrics for MTH-0118.

This module intentionally does not run models, contact deployment origins, or
promote any candidate.  It validates an audit manifest and computes metrics
from already-normalized, reviewed inputs.  The metric functions use explicit
judgments (for example, ``supported`` or ``expected_claim_type``); they do not
infer evidence support from names, URLs, or prose similarity.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .scope import ScopeContextValidationError, validate_scope_context

BENCHMARK_MANIFEST_SCHEMA_VERSION = "1.1"
RETRIEVAL_EVALUATION_MANIFEST_SCHEMA_VERSION = "1.0"
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)
OUTCOMES = frozenset(
    {"accepted", "rejected", "undetermined", "falsified", "not-evaluated"}
)
CLASSIFICATION_OUTCOMES = frozenset({"valid", "invalid", "undetermined"})
INPUT_ID_FIELDS = (
    "systems",
    "features",
    "views",
    "microstructures",
    "compositions",
    "analogies",
    "negative_knowledge",
)
NOVELTY_DIMENSIONS = frozenset(
    {
        "topology",
        "composition",
        "constraints",
        "behavior",
        "deployment",
        "historical",
    }
)
SPLIT_PARTITIONS = ("train", "evaluation", "holdout")
RETRIEVAL_BASELINES = frozenset(
    {
        "lexical",
        "vector",
        "graph",
        "vector-plus-graph",
        "structured",
        "direct-llm",
        "human",
        "other",
    }
)
RETRIEVAL_RECORD_KINDS = frozenset(
    {"system", "feature", "view", "trade_off", "relation", "composition"}
)
RETRIEVAL_NOVELTY_DIMENSIONS = frozenset(
    {"topology", "composition", "constraints", "behavior", "deployment", "historical"}
)


class BenchmarkManifestValidationError(ValueError):
    """Raised when a benchmark run manifest violates the research contract."""


@dataclass(frozen=True, slots=True)
class Metric:
    """A numerator/denominator metric with an explicit empty denominator."""

    name: str
    numerator: int | float
    denominator: int

    @property
    def value(self) -> float | None:
        """Return ``None`` when no observations were eligible for the metric."""

        if self.denominator == 0:
            return None
        return self.numerator / self.denominator

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "numerator": self.numerator,
            "denominator": self.denominator,
            "value": self.value,
        }


@dataclass(frozen=True, slots=True)
class BenchmarkRunManifest:
    """Immutable model of one validated benchmark run manifest."""

    value: dict[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "BenchmarkRunManifest":
        validate_benchmark_manifest(value)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        return copy.deepcopy(self.value)


@dataclass(frozen=True, slots=True)
class RetrievalEvaluationManifest:
    """Immutable model of one validated retrieval discovery evaluation."""

    value: dict[str, Any]

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "RetrievalEvaluationManifest":
        validate_retrieval_evaluation_manifest(value)
        return cls(copy.deepcopy(dict(value)))

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        return copy.deepcopy(self.value)


def load_benchmark_manifest(path: Path) -> BenchmarkRunManifest:
    """Load and validate a single JSON benchmark manifest."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BenchmarkManifestValidationError(
            f"{path}: invalid JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise BenchmarkManifestValidationError(f"{path}: manifest must be an object")
    try:
        return BenchmarkRunManifest.from_dict(value)
    except BenchmarkManifestValidationError as error:
        raise BenchmarkManifestValidationError(f"{path}: {error}") from error


def load_retrieval_evaluation_manifest(path: Path) -> RetrievalEvaluationManifest:
    """Load and validate one research-only retrieval evaluation manifest."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise BenchmarkManifestValidationError(
            f"{path}: invalid JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise BenchmarkManifestValidationError(f"{path}: manifest must be an object")
    try:
        return RetrievalEvaluationManifest.from_dict(value)
    except BenchmarkManifestValidationError as error:
        raise BenchmarkManifestValidationError(f"{path}: {error}") from error


def discover_benchmark_manifests(path: Path) -> list[Path]:
    """Return benchmark manifest files in deterministic order."""

    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(
        candidate for candidate in path.rglob("*.json") if candidate.is_file()
    )


def discover_retrieval_evaluation_manifests(path: Path) -> list[Path]:
    """Return retrieval evaluation manifests in deterministic order."""

    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(
        candidate for candidate in path.rglob("*.json") if candidate.is_file()
    )


def retrieval_digest(value: Any) -> str:
    """Return the stable digest used by retrieval manifests."""

    encoded = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(encoded).hexdigest()}"


def validate_retrieval_evaluation_manifest(value: Mapping[str, Any]) -> None:
    """Validate the reproducible, discovery-only retrieval contract."""

    required = {
        "manifest_kind",
        "schema_version",
        "evaluation_id",
        "protocol_version",
        "benchmark_version",
        "corpus_snapshot",
        "evidence_bundle",
        "query_set",
        "labels",
        "split",
        "method",
        "model",
        "boundaries",
        "results",
        "metrics",
        "result_boundary",
    }
    _object("retrieval manifest", value)
    _allowed("retrieval manifest", value, required)
    if set(value) != required:
        raise BenchmarkManifestValidationError(
            f"retrieval manifest fields must be exactly {sorted(required)}"
        )
    if value["manifest_kind"] != "retrieval_evaluation":
        raise BenchmarkManifestValidationError("invalid retrieval manifest_kind")
    if value["schema_version"] != RETRIEVAL_EVALUATION_MANIFEST_SCHEMA_VERSION:
        raise BenchmarkManifestValidationError(
            "unsupported retrieval evaluation schema_version"
        )
    for field in ("evaluation_id", "protocol_version", "benchmark_version"):
        _text(value, field, "retrieval manifest")

    corpus = value["corpus_snapshot"]
    _object("corpus_snapshot", corpus)
    _allowed(
        "corpus_snapshot",
        corpus,
        {"id", "corpus", "reviewed_only", "source_revision", "digest", "documents"},
    )
    _text(corpus, "id", "corpus_snapshot")
    if corpus.get("corpus") != "canonical_cards":
        raise BenchmarkManifestValidationError(
            "corpus_snapshot.corpus must be canonical_cards"
        )
    if corpus.get("reviewed_only") is not True:
        raise BenchmarkManifestValidationError(
            "corpus_snapshot.reviewed_only must remain true"
        )
    revision = corpus.get("source_revision")
    _object("corpus_snapshot.source_revision", revision)
    _allowed(
        "corpus_snapshot.source_revision",
        revision,
        {"repository_id", "commit", "archive_digest"},
    )
    _text(revision, "repository_id", "corpus_snapshot.source_revision")
    if "commit" in revision:
        _text(revision, "commit", "corpus_snapshot.source_revision")
    if "commit" not in revision and "archive_digest" not in revision:
        raise BenchmarkManifestValidationError(
            "corpus_snapshot.source_revision needs commit or archive_digest"
        )
    if "archive_digest" in revision:
        _digest(revision, "archive_digest", "corpus_snapshot.source_revision")
    _digest(corpus, "digest", "corpus_snapshot")
    documents = _list(corpus, "documents", "corpus_snapshot")
    document_ids: set[str] = set()
    document_evidence: dict[str, set[str]] = {}
    document_metadata: dict[str, Mapping[str, Any]] = {}
    for index, document in enumerate(documents):
        label = f"corpus_snapshot.documents[{index}]"
        _validate_retrieval_document(document, label)
        document_id = document["id"]
        if document_id in document_ids:
            raise BenchmarkManifestValidationError(
                f"duplicate corpus document id: {document_id}"
            )
        document_ids.add(document_id)
        document_evidence[document_id] = set(document["evidence_ids"])
        document_metadata[document_id] = document
    if corpus["digest"] != retrieval_digest(documents):
        raise BenchmarkManifestValidationError(
            "corpus_snapshot.digest does not match documents"
        )

    evidence_bundle = value["evidence_bundle"]
    _object("evidence_bundle", evidence_bundle)
    _allowed("evidence_bundle", evidence_bundle, {"id", "digest", "evidence_ids"})
    _text(evidence_bundle, "id", "evidence_bundle")
    _digest(evidence_bundle, "digest", "evidence_bundle")
    bundle_evidence = set(
        _non_empty_string_list(evidence_bundle, "evidence_ids", "evidence_bundle")
    )
    if evidence_bundle["digest"] != retrieval_digest(sorted(bundle_evidence)):
        raise BenchmarkManifestValidationError(
            "evidence_bundle.digest does not match evidence_ids"
        )
    if not all(
        evidence.issubset(bundle_evidence) for evidence in document_evidence.values()
    ):
        raise BenchmarkManifestValidationError(
            "evidence_bundle must close every corpus document"
        )

    query_set = value["query_set"]
    _object("query_set", query_set)
    _allowed("query_set", query_set, {"id", "digest", "queries"})
    _text(query_set, "id", "query_set")
    _digest(query_set, "digest", "query_set")
    queries = _list(query_set, "queries", "query_set")
    query_ids: set[str] = set()
    for index, query in enumerate(queries):
        label = f"query_set.queries[{index}]"
        _validate_retrieval_query(query, label)
        query_id = query["id"]
        if query_id in query_ids:
            raise BenchmarkManifestValidationError(f"duplicate query id: {query_id}")
        query_ids.add(query_id)
        if query["query_digest"] != retrieval_digest(
            {key: query[key] for key in ("id", "question", "scope")}
        ):
            raise BenchmarkManifestValidationError(
                f"{label}.query_digest does not match query"
            )
    if query_set["digest"] != retrieval_digest(queries):
        raise BenchmarkManifestValidationError(
            "query_set.digest does not match queries"
        )

    labels = value["labels"]
    _object("labels", labels)
    _allowed("labels", labels, {"relevance", "holdout"})
    relevance = _list(labels, "relevance", "labels")
    relevance_pairs: set[tuple[str, str]] = set()
    for index, label_record in enumerate(relevance):
        label = f"labels.relevance[{index}]"
        _validate_relevance_label(
            label_record,
            label,
            query_ids,
            document_ids,
            document_evidence,
            bundle_evidence,
        )
        pair = (label_record["query_id"], label_record["document_id"])
        if pair in relevance_pairs:
            raise BenchmarkManifestValidationError(f"duplicate relevance label: {pair}")
        relevance_pairs.add(pair)
    holdout = _list(labels, "holdout", "labels")
    holdout_ids: set[str] = set()
    for index, holdout_record in enumerate(holdout):
        label = f"labels.holdout[{index}]"
        _validate_holdout_label(holdout_record, label, query_ids, bundle_evidence)
        if holdout_record["id"] in holdout_ids:
            raise BenchmarkManifestValidationError(
                f"duplicate holdout label id: {holdout_record['id']}"
            )
        holdout_ids.add(holdout_record["id"])
        if holdout_record["document_id"] in document_ids:
            raise BenchmarkManifestValidationError(
                "holdout documents must remain outside the canonical corpus"
            )

    split = value["split"]
    _validate_retrieval_split(split, query_ids, holdout, holdout_ids)
    method = value["method"]
    _validate_retrieval_method(method)
    model = value["model"]
    _validate_retrieval_model(model)
    _validate_retrieval_boundaries(value["boundaries"])

    results = _list(value, "results")
    result_query_ids: set[str] = set()
    for index, query_result in enumerate(results):
        label = f"results[{index}]"
        _validate_query_result(
            query_result,
            label,
            query_ids,
            document_ids,
            document_evidence,
            document_metadata,
        )
        query_id = query_result["query_id"]
        if query_id in result_query_ids:
            raise BenchmarkManifestValidationError(
                f"duplicate query result: {query_id}"
            )
        result_query_ids.add(query_id)
    if result_query_ids != query_ids:
        raise BenchmarkManifestValidationError(
            "results must cover every query exactly once"
        )
    _validate_retrieval_metrics(value["metrics"])
    _validate_retrieval_result_boundary(value["result_boundary"])


def recall_at_k(
    relevance: Mapping[str, Mapping[str, int]],
    ranked_document_ids: Mapping[str, Iterable[str]],
    k: int,
) -> Metric:
    """Compute discovery recall@k over queries with at least one relevant item."""

    if k < 1:
        raise ValueError("k must be positive")
    eligible = {
        query_id: labels
        for query_id, labels in relevance.items()
        if any(labels.values())
    }
    found = sum(
        any(
            relevance[query_id].get(document_id, 0) > 0
            for document_id in list(ranked_document_ids.get(query_id, ()))[:k]
        )
        for query_id in eligible
    )
    return _metric(f"recall@{k}", found, len(eligible))


def retrieval_scope_completeness(records: Iterable[Mapping[str, Any]]) -> Metric:
    """Measure returned records with complete declared validity scope."""

    observations = list(records)
    complete = sum(
        all(
            isinstance(record.get(field), (str, list))
            and (record[field] if isinstance(record[field], str) else True)
            for field in (
                "version_context",
                "deployment_origins",
                "conditions",
                "exclusions",
            )
        )
        for record in observations
    )
    return _metric("scope_completeness", complete, len(observations))


def retrieval_claim_type_accuracy(records: Iterable[Mapping[str, Any]]) -> Metric:
    """Measure agreement with independently supplied claim-type labels."""

    observations = [
        record for record in records if record.get("expected_claim_type") in CLAIM_TYPES
    ]
    correct = sum(
        record.get("claim_type") == record["expected_claim_type"]
        for record in observations
    )
    return _metric("claim_type_accuracy", correct, len(observations))


def retrieval_false_link_rate(records: Iterable[Mapping[str, Any]]) -> Metric:
    """Measure independently labelled false links among evaluated links."""

    observations = [
        record
        for record in records
        if record.get("link_outcome") in {"relevant", "false-link"}
    ]
    false_links = sum(record["link_outcome"] == "false-link" for record in observations)
    return _metric("false_link_rate", false_links, len(observations))


def retrieval_abstention_rate(query_results: Iterable[Mapping[str, Any]]) -> Metric:
    """Measure explicit abstentions over all evaluated queries."""

    observations = list(query_results)
    abstained = sum(record.get("abstained") is True for record in observations)
    return _metric("abstention_rate", abstained, len(observations))


def ndcg_at_k(
    relevance: Mapping[str, Mapping[str, int]],
    ranked_document_ids: Mapping[str, Iterable[str]],
    k: int,
) -> dict[str, Any]:
    """Compute bounded discovery nDCG@k without interpreting relevance as truth."""

    if k < 1:
        raise ValueError("k must be positive")
    values: list[float] = []
    for query_id, labels in relevance.items():
        if not labels:
            continue
        ranked = list(ranked_document_ids.get(query_id, ()))[:k]
        actual = sum(
            (2 ** labels.get(document_id, 0) - 1) / math.log2(rank + 2)
            for rank, document_id in enumerate(ranked)
        )
        ideal_grades = sorted(labels.values(), reverse=True)[:k]
        ideal = sum(
            (2**grade - 1) / math.log2(rank + 2)
            for rank, grade in enumerate(ideal_grades)
        )
        values.append(actual / ideal if ideal else 0.0)
    return _float_metric("nDCG@%d" % k, sum(values), len(values))


def validate_benchmark_manifest(value: Mapping[str, Any]) -> None:
    """Validate shape, immutable provenance, evidence locality, and candidate state."""

    if not isinstance(value, Mapping):
        raise BenchmarkManifestValidationError("manifest must be an object")
    required = {
        "schema_version",
        "run_id",
        "protocol_version",
        "benchmark_version",
        "source_revisions",
        "evidence_bundle",
        "input_ids",
        "input_evidence",
        "split",
        "method",
        "provenance",
        "deployment",
        "randomness",
        "novelty",
        "analogy_policy",
        "candidates",
        "review",
        "result_boundary",
        "outcome",
    }
    _allowed("manifest", value, required | {"observation_evidence_ids"})
    missing = required - value.keys()
    if missing:
        raise BenchmarkManifestValidationError(f"missing fields: {sorted(missing)}")
    _text(value, "schema_version")
    if value["schema_version"] != BENCHMARK_MANIFEST_SCHEMA_VERSION:
        raise BenchmarkManifestValidationError("unsupported schema_version")
    for field in ("run_id", "protocol_version", "benchmark_version"):
        _text(value, field)

    revisions = _list(value, "source_revisions")
    if not revisions:
        raise BenchmarkManifestValidationError("source_revisions must not be empty")
    revision_ids: set[str] = set()
    for index, revision in enumerate(revisions):
        label = f"source_revisions[{index}]"
        _object(label, revision)
        _allowed(label, revision, {"repository_id", "commit", "archive_digest"})
        for field in ("repository_id",):
            _text(revision, field, label)
        if revision["repository_id"] in revision_ids:
            raise BenchmarkManifestValidationError(
                f"duplicate source repository: {revision['repository_id']}"
            )
        revision_ids.add(revision["repository_id"])
        for field in ("commit", "archive_digest"):
            if field in revision and (
                not isinstance(revision[field], str) or not revision[field]
            ):
                raise BenchmarkManifestValidationError(
                    f"{label}.{field} needs a non-empty string"
                )
        commit = revision.get("commit")
        digest = revision.get("archive_digest")
        if not (isinstance(commit, str) and commit) and not (
            isinstance(digest, str) and digest
        ):
            raise BenchmarkManifestValidationError(
                f"{label} needs commit or archive_digest"
            )

    bundle = value["evidence_bundle"]
    _object("evidence_bundle", bundle)
    _allowed(
        "evidence_bundle",
        bundle,
        {"id", "digest", "evidence_ids", "source_revision_digests"},
    )
    for field in ("id", "digest"):
        _text(bundle, field, "evidence_bundle")
    source_revision_digests = bundle.get("source_revision_digests")
    _object("evidence_bundle.source_revision_digests", source_revision_digests)
    if set(source_revision_digests) != revision_ids:
        raise BenchmarkManifestValidationError(
            "evidence_bundle.source_revision_digests must cover exactly "
            "source repositories"
        )
    for repository_id, digest in source_revision_digests.items():
        if not isinstance(digest, str) or not digest:
            raise BenchmarkManifestValidationError(
                f"evidence_bundle.source_revision_digests[{repository_id}] "
                "needs a non-empty string"
            )
        revision = next(
            item for item in revisions if item["repository_id"] == repository_id
        )
        archive_digest = revision.get("archive_digest")
        if archive_digest is not None and digest != archive_digest:
            raise BenchmarkManifestValidationError(
                f"source digest mismatch for repository: {repository_id}"
            )
    evidence_ids = _string_list(bundle, "evidence_ids", "evidence_bundle")
    if len(set(evidence_ids)) != len(evidence_ids):
        raise BenchmarkManifestValidationError(
            "evidence_bundle.evidence_ids must be unique"
        )
    evidence_set = set(evidence_ids)
    observation_evidence_ids = value.get("observation_evidence_ids")
    if observation_evidence_ids is not None:
        observation_evidence_ids = _string_list(
            value, "observation_evidence_ids", "manifest"
        )
        if not observation_evidence_ids:
            raise BenchmarkManifestValidationError(
                "observation_evidence_ids must not be empty when supplied"
            )
        if len(set(observation_evidence_ids)) != len(observation_evidence_ids):
            raise BenchmarkManifestValidationError(
                "observation_evidence_ids must be unique"
            )
        if not set(observation_evidence_ids).issubset(evidence_set):
            raise BenchmarkManifestValidationError(
                "observation_evidence_ids must be local to evidence_bundle"
            )

    inputs = value["input_ids"]
    _object("input_ids", inputs)
    if set(inputs) != set(INPUT_ID_FIELDS):
        raise BenchmarkManifestValidationError(
            f"input_ids must contain exactly {list(INPUT_ID_FIELDS)}"
        )
    for field in INPUT_ID_FIELDS:
        _string_list(inputs, field, "input_ids")

    input_evidence = value["input_evidence"]
    _object("input_evidence", input_evidence)
    expected_input_refs = {
        f"{field}:{item}" for field in INPUT_ID_FIELDS for item in inputs[field]
    }
    if set(input_evidence) != expected_input_refs:
        raise BenchmarkManifestValidationError(
            "input_evidence must contain exactly one entry for every input ID"
        )
    for input_ref in expected_input_refs:
        _evidence_ids(input_evidence, input_ref, evidence_set, "input_evidence")

    split = value["split"]
    _object("split", split)
    _allowed(
        "split",
        split,
        {
            "strategy",
            "partitions",
            "temporal_cutoff",
            "leakage_controls",
            "negative_knowledge_holdout_ids",
            "candidate_generation_exclusions",
        },
    )
    _text(split, "strategy", "split")
    partitions = split.get("partitions")
    _object("split.partitions", partitions)
    if set(partitions) != set(SPLIT_PARTITIONS):
        raise BenchmarkManifestValidationError(
            f"split.partitions must contain exactly {list(SPLIT_PARTITIONS)}"
        )
    partition_refs: list[str] = []
    for partition in SPLIT_PARTITIONS:
        refs = _string_list(partitions, partition, "split.partitions")
        partition_refs.extend(refs)
    if len(set(partition_refs)) != len(partition_refs):
        raise BenchmarkManifestValidationError("split partitions must be disjoint")
    if set(partition_refs) != expected_input_refs:
        raise BenchmarkManifestValidationError(
            "split partitions must cover exactly all input IDs"
        )
    temporal_cutoff = split.get("temporal_cutoff")
    if temporal_cutoff is not None and (
        not isinstance(temporal_cutoff, str) or not temporal_cutoff
    ):
        raise BenchmarkManifestValidationError(
            "split.temporal_cutoff must be a non-empty string or null"
        )
    if "temporal" in split["strategy"].lower() and temporal_cutoff is None:
        raise BenchmarkManifestValidationError(
            "temporal split strategies require split.temporal_cutoff"
        )
    _string_list(split, "leakage_controls", "split")
    holdout_negative = _string_list(split, "negative_knowledge_holdout_ids", "split")
    if set(holdout_negative) != set(inputs["negative_knowledge"]):
        raise BenchmarkManifestValidationError(
            "all negative-knowledge inputs must be held out exactly"
        )
    holdout_refs = set(partitions["holdout"])
    if any(
        f"negative_knowledge:{item}" not in holdout_refs for item in holdout_negative
    ):
        raise BenchmarkManifestValidationError(
            "all negative-knowledge inputs must be in the holdout partition"
        )
    exclusions = set(_string_list(split, "candidate_generation_exclusions", "split"))
    required_exclusions = {f"negative_knowledge:{item}" for item in holdout_negative}
    if not required_exclusions.issubset(exclusions):
        raise BenchmarkManifestValidationError(
            "candidate_generation_exclusions must include every "
            "negative-knowledge holdout"
        )

    method = value["method"]
    _object("method", method)
    _allowed("method", method, {"name", "baseline"})
    _text(method, "name", "method")
    _text(method, "baseline", "method")

    provenance = value["provenance"]
    _object("provenance", provenance)
    _allowed(
        "provenance",
        provenance,
        {
            "provider",
            "exact_model_id",
            "prompt_digest",
            "input_bundle_digest",
            "deterministic_inspector",
        },
    )
    for field in ("provider", "exact_model_id", "prompt_digest"):
        if provenance.get(field) is not None and (
            not isinstance(provenance[field], str) or not provenance[field]
        ):
            raise BenchmarkManifestValidationError(
                f"provenance.{field} must be a non-empty string or null"
            )
    for field in ("input_bundle_digest", "deterministic_inspector"):
        _text(provenance, field, "provenance")
    if bool(provenance.get("provider")) != bool(provenance.get("exact_model_id")):
        raise BenchmarkManifestValidationError(
            "provenance.provider and exact_model_id must be supplied together"
        )
    if provenance["input_bundle_digest"] != bundle["digest"]:
        raise BenchmarkManifestValidationError(
            "provenance.input_bundle_digest must equal evidence_bundle.digest"
        )

    deployment = value["deployment"]
    _object("deployment", deployment)
    _allowed(
        "deployment",
        deployment,
        {
            "origin",
            "version",
            "conditions",
            "exclusions",
            "workload",
            "scope_context",
        },
    )
    for field in ("origin", "version"):
        _text(deployment, field, "deployment")
    for field in ("conditions", "exclusions"):
        _string_list(deployment, field, "deployment")
    if deployment.get("workload") is not None and not isinstance(
        deployment["workload"], str
    ):
        raise BenchmarkManifestValidationError(
            "deployment.workload must be a string or null"
        )
    if "scope_context" in deployment:
        _validate_scope_context(
            deployment["scope_context"], "deployment.scope_context", evidence_set
        )

    randomness = value["randomness"]
    _object("randomness", randomness)
    _allowed("randomness", randomness, {"seed", "decoding_parameters"})
    if not isinstance(randomness.get("seed"), int) or isinstance(
        randomness.get("seed"), bool
    ):
        raise BenchmarkManifestValidationError("randomness.seed must be an integer")
    if not isinstance(randomness.get("decoding_parameters"), Mapping):
        raise BenchmarkManifestValidationError(
            "randomness.decoding_parameters must be an object"
        )

    novelty = value["novelty"]
    _object("novelty", novelty)
    _allowed(
        "novelty",
        novelty,
        {
            "reference_window",
            "representation",
            "dimensions",
            "strata",
            "aggregate_score_allowed",
        },
    )
    _text(novelty, "reference_window", "novelty")
    _text(novelty, "representation", "novelty")
    dimensions = _string_list(novelty, "dimensions", "novelty")
    if set(dimensions) != NOVELTY_DIMENSIONS:
        raise BenchmarkManifestValidationError(
            "novelty.dimensions must declare all six novelty dimensions exactly"
        )
    if len(dimensions) != len(set(dimensions)):
        raise BenchmarkManifestValidationError("novelty.dimensions must be unique")
    if not _string_list(novelty, "strata", "novelty"):
        raise BenchmarkManifestValidationError("novelty.strata must not be empty")
    if novelty.get("aggregate_score_allowed") is not False:
        raise BenchmarkManifestValidationError(
            "novelty.aggregate_score_allowed must remain false"
        )

    analogy_policy = value["analogy_policy"]
    _object("analogy_policy", analogy_policy)
    _allowed(
        "analogy_policy",
        analogy_policy,
        {
            "non_equivalence_required",
            "historical_influence_requires_direct_evidence",
            "substitutability_not_implied",
        },
    )
    for field in (
        "non_equivalence_required",
        "historical_influence_requires_direct_evidence",
        "substitutability_not_implied",
    ):
        if analogy_policy.get(field) is not True:
            raise BenchmarkManifestValidationError(
                f"analogy_policy.{field} must remain true"
            )

    candidates = _list(value, "candidates")
    candidate_ids: set[str] = set()
    for index, candidate in enumerate(candidates):
        label = f"candidates[{index}]"
        _object(label, candidate)
        _allowed(
            label,
            candidate,
            {"id", "evidence_ids", "claims", "validation_logs", "proven"},
        )
        _text(candidate, "id", label)
        if candidate["id"] in candidate_ids:
            raise BenchmarkManifestValidationError(
                f"duplicate candidate id: {candidate['id']}"
            )
        candidate_ids.add(candidate["id"])
        if candidate.get("proven") is not False:
            raise BenchmarkManifestValidationError(f"{label}.proven must remain false")
        _evidence_ids(candidate, "evidence_ids", evidence_set, label)
        claims = _list(candidate, "claims", label)
        claim_ids: set[str] = set()
        for claim_index, claim in enumerate(claims):
            claim_label = f"{label}.claims[{claim_index}]"
            _validate_claim(claim, claim_label, evidence_set, claim_ids)
        logs = _list(candidate, "validation_logs", label)
        for log_index, log in enumerate(logs):
            log_label = f"{label}.validation_logs[{log_index}]"
            _object(log_label, log)
            for field in ("check", "result", "reason"):
                _text(log, field, log_label)

    review = value["review"]
    _object("review", review)
    _allowed(
        "review",
        review,
        {
            "reviewer_pool",
            "rubric_version",
            "blinded_assignment",
            "adjudication_record",
        },
    )
    _string_list(review, "reviewer_pool", "review")
    _text(review, "rubric_version", "review")
    if not isinstance(review.get("blinded_assignment"), bool):
        raise BenchmarkManifestValidationError(
            "review.blinded_assignment must be boolean"
        )
    if not isinstance(review.get("adjudication_record"), list):
        raise BenchmarkManifestValidationError(
            "review.adjudication_record must be a list"
        )

    result_boundary = value["result_boundary"]
    _object("result_boundary", result_boundary)
    _allowed(
        "result_boundary",
        result_boundary,
        {"canonical", "promotion_requires_human_review", "storage_scope"},
    )
    if result_boundary.get("canonical") is not False:
        raise BenchmarkManifestValidationError(
            "result_boundary.canonical must remain false"
        )
    if result_boundary.get("promotion_requires_human_review") is not True:
        raise BenchmarkManifestValidationError(
            "result_boundary.promotion_requires_human_review must remain true"
        )
    if result_boundary.get("storage_scope") not in {"research", "draft"}:
        raise BenchmarkManifestValidationError(
            "result_boundary.storage_scope must be research or draft"
        )

    outcome = value["outcome"]
    _object("outcome", outcome)
    _allowed("outcome", outcome, {"status", "reason"})
    _text(outcome, "reason", "outcome")
    if outcome.get("status") not in OUTCOMES:
        raise BenchmarkManifestValidationError("outcome.status is invalid")


def evidence_locality(
    claims: Iterable[Mapping[str, Any]],
    supplied_evidence_ids: Iterable[str],
    contract_evidence_ids: Iterable[str] = (),
) -> Metric:
    """Measure claims whose cited evidence is local to the supplied bundle."""

    available = set(supplied_evidence_ids) | set(contract_evidence_ids)
    records = list(claims)
    local = sum(
        bool(record.get("evidence_ids"))
        and set(record.get("evidence_ids", ())).issubset(available)
        for record in records
    )
    return _metric("evidence_locality", local, len(records))


def citation_precision(citations: Iterable[Mapping[str, Any]]) -> Metric:
    """Measure independently judged supporting citations among all citations."""

    records = list(citations)
    supported = sum(record.get("supported") is True for record in records)
    return _metric("citation_precision", supported, len(records))


def claim_discipline(claims: Iterable[Mapping[str, Any]]) -> dict[str, Metric]:
    """Return claim-type accuracy and unsupported-claim rates by claim type."""

    records = list(claims)
    typed = [
        record for record in records if record.get("expected_claim_type") in CLAIM_TYPES
    ]
    result = {
        "claim_type_accuracy": _metric(
            "claim_type_accuracy",
            sum(
                record.get("claim_type") == record["expected_claim_type"]
                for record in typed
            ),
            len(typed),
        )
    }
    for claim_type in sorted(CLAIM_TYPES):
        typed_records = [
            record for record in records if record.get("claim_type") == claim_type
        ]
        unsupported = sum(record.get("supported") is False for record in typed_records)
        result[f"unsupported_{claim_type}_rate"] = _metric(
            f"unsupported_{claim_type}_rate", unsupported, len(typed_records)
        )
    return result


def classification_metrics(
    records: Iterable[Mapping[str, Any]],
) -> dict[str, Any]:
    """Score reviewed ``valid``/``invalid``/``undetermined`` classifications."""

    observations = list(records)
    for record in observations:
        if record.get("expected") not in CLASSIFICATION_OUTCOMES:
            raise ValueError(
                "classification expected must be valid, invalid, or undetermined"
            )
        if record.get("predicted") not in CLASSIFICATION_OUTCOMES:
            raise ValueError(
                "classification predicted must be valid, invalid, or undetermined"
            )
    confusion = {
        expected: {
            predicted: sum(
                record["expected"] == expected and record["predicted"] == predicted
                for record in observations
            )
            for predicted in sorted(CLASSIFICATION_OUTCOMES)
        }
        for expected in sorted(CLASSIFICATION_OUTCOMES)
    }
    by_outcome: dict[str, dict[str, Metric]] = {}
    for outcome in sorted(CLASSIFICATION_OUTCOMES):
        true_positive = confusion[outcome][outcome]
        expected_total = sum(confusion[outcome].values())
        predicted_total = sum(row[outcome] for row in confusion.values())
        by_outcome[outcome] = {
            "recall": _metric(f"{outcome}_recall", true_positive, expected_total),
            "precision": _metric(
                f"{outcome}_precision", true_positive, predicted_total
            ),
        }
    abstentions = sum(record["predicted"] == "undetermined" for record in observations)
    scored = [
        record
        for record in observations
        if record["expected"] != "undetermined"
        and record["predicted"] != "undetermined"
    ]
    unknown_reference = sum(
        record["expected"] == "undetermined" for record in observations
    )
    unknown_correct = sum(
        record["expected"] == "undetermined" and record["predicted"] == "undetermined"
        for record in observations
    )
    return {
        "accuracy": _metric(
            "classification_accuracy",
            sum(record["expected"] == record["predicted"] for record in observations),
            len(observations),
        ),
        "confusion": confusion,
        "by_outcome": by_outcome,
        "abstention_rate": _metric("abstention_rate", abstentions, len(observations)),
        "coverage": _metric(
            "classification_coverage",
            len(observations) - abstentions,
            len(observations),
        ),
        "known_accuracy": _metric(
            "known_accuracy",
            sum(record["expected"] == record["predicted"] for record in scored),
            len(scored),
        ),
        "unknown_recall": _metric("unknown_recall", unknown_correct, unknown_reference),
    }


def typed_obligation_satisfaction(
    requirements: Iterable[str],
    provisions: Iterable[str],
    adapters: Iterable[Mapping[str, Any]] = (),
) -> Metric:
    """Measure requirements met by exact provisions or explicit adapters."""

    required = sorted(set(requirements))
    provided = set(provisions)
    adapted: set[str] = set()
    for adapter in adapters:
        if not isinstance(adapter, Mapping):
            raise ValueError("adapters must contain objects")
        requirement = adapter.get("requirement", adapter.get("requires"))
        provision = adapter.get("provision", adapter.get("provides"))
        if isinstance(requirement, str) and isinstance(provision, str):
            if provision in provided:
                adapted.add(requirement)
    satisfied = sum(
        requirement in provided or requirement in adapted for requirement in required
    )
    return _metric("typed_obligation_satisfaction", satisfied, len(required))


def counterexample_recall(
    known_counterexample_ids: Iterable[str], found_counterexample_ids: Iterable[str]
) -> Metric:
    """Measure held-out counterexamples discovered or explicitly cited."""

    known = set(known_counterexample_ids)
    found = set(found_counterexample_ids)
    return _metric("counterexample_recall", len(known & found), len(known))


def heldout_counterexample_recall(
    held_out_ids: Iterable[str],
    found_ids: Iterable[str],
    exposed_ids: Iterable[str] = (),
) -> Metric:
    """Score held-out negative knowledge and reject generator leakage."""

    held_out = set(held_out_ids)
    found = set(found_ids)
    exposed = set(exposed_ids)
    leaked = held_out & exposed
    if leaked:
        raise ValueError(f"held-out counterexamples were exposed: {sorted(leaked)}")
    return _metric(
        "heldout_counterexample_recall", len(held_out & found), len(held_out)
    )


def novelty_scope_completeness(records: Iterable[Mapping[str, Any]]) -> Metric:
    """Measure novelty records with bounded comparison and falsifier scope."""

    observations = list(records)
    complete = 0
    for record in observations:
        fields = (
            "dimension",
            "reference_window",
            "representation",
            "scope",
            "falsifiers",
        )
        if all(record.get(field) for field in fields) and record.get("claim_type") in {
            "hypothesis",
            "inference",
            "analogy",
        }:
            complete += 1
    return _metric("novelty_scope_completeness", complete, len(observations))


def _metric(name: str, numerator: int, denominator: int) -> Metric:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("metric counts must satisfy 0 <= numerator <= denominator")
    return Metric(name, numerator, denominator)


def _float_metric(name: str, numerator: float, denominator: int) -> Metric:
    if numerator < 0 or denominator < 0 or numerator > denominator:
        raise ValueError("metric counts must satisfy 0 <= numerator <= denominator")
    return Metric(name, numerator, denominator)


def _digest(value: Mapping[str, Any], field: str, label: str) -> None:
    digest = value.get(field)
    if not isinstance(digest, str) or not digest.startswith("sha256:"):
        raise BenchmarkManifestValidationError(f"{label}.{field} needs a sha256 digest")
    try:
        hexadecimal = digest.removeprefix("sha256:")
        if len(hexadecimal) != 64:
            raise ValueError
        int(hexadecimal, 16)
    except ValueError as error:
        raise BenchmarkManifestValidationError(
            f"{label}.{field} needs a sha256 digest"
        ) from error


def _validate_retrieval_document(document: Any, label: str) -> None:
    _object(label, document)
    _allowed(
        label,
        document,
        {
            "id",
            "record_kind",
            "source_ref",
            "source_digest",
            "claim_type",
            "claim_status",
            "evidence_ids",
            "validity_scope",
            "scope_context",
        },
    )
    for field in ("id", "source_ref"):
        _text(document, field, label)
    if document.get("record_kind") not in RETRIEVAL_RECORD_KINDS:
        raise BenchmarkManifestValidationError(f"{label}.record_kind is invalid")
    _digest(document, "source_digest", label)
    if document.get("claim_type") not in CLAIM_TYPES:
        raise BenchmarkManifestValidationError(f"{label}.claim_type is invalid")
    if document.get("claim_status") not in CLAIM_STATUSES:
        raise BenchmarkManifestValidationError(f"{label}.claim_status is invalid")
    _non_empty_string_list(document, "evidence_ids", label)
    _validate_scope(document.get("validity_scope"), f"{label}.validity_scope")
    if "scope_context" in document:
        _validate_scope_context(
            document["scope_context"],
            f"{label}.scope_context",
            set(document["evidence_ids"]),
        )


def _validate_scope(scope: Any, label: str) -> None:
    _object(label, scope)
    _allowed(
        label,
        scope,
        {"version_context", "deployment_origins", "conditions", "exclusions"},
    )
    if scope.get("version_context") is not None:
        _text(scope, "version_context", label)
    for field in ("deployment_origins", "conditions", "exclusions"):
        _string_list(scope, field, label)


def _validate_scope_context(value: Any, label: str, evidence_ids: set[str]) -> None:
    try:
        validate_scope_context(value, evidence_ids=evidence_ids, label=label)
    except ScopeContextValidationError as error:
        raise BenchmarkManifestValidationError(str(error)) from error


def _validate_retrieval_query(query: Any, label: str) -> None:
    _object(label, query)
    _allowed(label, query, {"id", "query_digest", "question", "scope"})
    _text(query, "id", label)
    _digest(query, "query_digest", label)
    question = query.get("question")
    if not isinstance(question, str) or not 1 <= len(question) <= 1000:
        raise BenchmarkManifestValidationError(
            f"{label}.question must be 1-1000 characters"
        )
    _validate_scope(query.get("scope"), f"{label}.scope")


def _validate_relevance_label(
    record: Any,
    label: str,
    query_ids: set[str],
    document_ids: set[str],
    document_evidence: Mapping[str, set[str]],
    bundle_evidence: set[str],
) -> None:
    _object(label, record)
    _allowed(
        label,
        record,
        {
            "query_id",
            "document_id",
            "grade",
            "claim_type",
            "evidence_ids",
            "evidence_locality",
            "scope_match",
            "link_outcome",
            "label_source",
        },
    )
    for field, known in (("query_id", query_ids), ("document_id", document_ids)):
        _text(record, field, label)
        if record[field] not in known:
            raise BenchmarkManifestValidationError(f"{label}.{field} is unknown")
    if (
        not isinstance(record.get("grade"), int)
        or isinstance(record["grade"], bool)
        or not 0 <= record["grade"] <= 3
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.grade must be an integer from 0 to 3"
        )
    if record.get("claim_type") not in CLAIM_TYPES:
        raise BenchmarkManifestValidationError(f"{label}.claim_type is invalid")
    _non_empty_string_list(record, "evidence_ids", label)
    if not set(record["evidence_ids"]).issubset(bundle_evidence):
        raise BenchmarkManifestValidationError(
            f"{label}.evidence_ids are outside evidence bundle"
        )
    if not set(record["evidence_ids"]).issubset(
        document_evidence[record["document_id"]]
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.evidence_ids must be local to the document"
        )
    if record.get("evidence_locality") not in {"local", "not-local", "undetermined"}:
        raise BenchmarkManifestValidationError(f"{label}.evidence_locality is invalid")
    if record.get("scope_match") not in {"match", "mismatch", "undetermined"}:
        raise BenchmarkManifestValidationError(f"{label}.scope_match is invalid")
    if record.get("link_outcome") is not None and record["link_outcome"] not in {
        "relevant",
        "false-link",
        "undetermined",
    }:
        raise BenchmarkManifestValidationError(f"{label}.link_outcome is invalid")
    _text(record, "label_source", label)


def _validate_holdout_label(
    record: Any, label: str, query_ids: set[str], bundle_evidence: set[str]
) -> None:
    _object(label, record)
    _allowed(
        label,
        record,
        {
            "id",
            "query_id",
            "document_id",
            "kind",
            "reason",
            "candidate_generation_excluded",
            "claim_type",
            "evidence_ids",
        },
    )
    for field in ("id", "query_id", "document_id", "reason"):
        _text(record, field, label)
    if record["query_id"] not in query_ids:
        raise BenchmarkManifestValidationError(f"{label}.query_id is unknown")
    if record.get("kind") not in {"negative-knowledge", "counterexample", "unknown"}:
        raise BenchmarkManifestValidationError(f"{label}.kind is invalid")
    if record.get("candidate_generation_excluded") is not True:
        raise BenchmarkManifestValidationError(
            f"{label}.candidate_generation_excluded must remain true"
        )
    if record.get("claim_type") not in CLAIM_TYPES:
        raise BenchmarkManifestValidationError(f"{label}.claim_type is invalid")
    _non_empty_string_list(record, "evidence_ids", label)
    if not set(record["evidence_ids"]).issubset(bundle_evidence):
        raise BenchmarkManifestValidationError(
            f"{label}.evidence_ids are outside evidence bundle"
        )


def _validate_retrieval_split(
    split: Any,
    query_ids: set[str],
    holdout: list[Any],
    holdout_ids: set[str],
) -> None:
    _object("split", split)
    _allowed(
        "split",
        split,
        {
            "strategy",
            "partitions",
            "digest",
            "holdout_query_ids",
            "candidate_generation_exclusions",
            "temporal_cutoff",
            "leakage_controls",
        },
    )
    _text(split, "strategy", "split")
    partitions = split.get("partitions")
    _object("split.partitions", partitions)
    _allowed("split.partitions", partitions, set(SPLIT_PARTITIONS))
    refs: list[str] = []
    for partition in SPLIT_PARTITIONS:
        refs.extend(_string_list(partitions, partition, "split.partitions"))
    if len(refs) != len(set(refs)):
        raise BenchmarkManifestValidationError(
            "retrieval split partitions must be disjoint"
        )
    if set(refs) != query_ids:
        raise BenchmarkManifestValidationError(
            "retrieval split partitions must cover all query IDs"
        )
    _digest(split, "digest", "split")
    if split["digest"] != retrieval_digest(partitions):
        raise BenchmarkManifestValidationError("split.digest does not match partitions")
    holdout_query_ids = set(_string_list(split, "holdout_query_ids", "split"))
    expected_holdout_queries = {record["query_id"] for record in holdout}
    if holdout_query_ids != expected_holdout_queries:
        raise BenchmarkManifestValidationError(
            "split.holdout_query_ids must match holdout labels"
        )
    if not holdout_query_ids.issubset(set(partitions["holdout"])):
        raise BenchmarkManifestValidationError(
            "holdout queries must be in holdout partition"
        )
    exclusions = set(_string_list(split, "candidate_generation_exclusions", "split"))
    if not holdout_ids.issubset(exclusions):
        raise BenchmarkManifestValidationError(
            "all holdout labels must be excluded from candidate generation"
        )
    temporal_cutoff = split.get("temporal_cutoff")
    if temporal_cutoff is not None and (
        not isinstance(temporal_cutoff, str) or not temporal_cutoff
    ):
        raise BenchmarkManifestValidationError(
            "split.temporal_cutoff must be a non-empty string or null"
        )
    _string_list(split, "leakage_controls", "split")


def _validate_retrieval_method(method: Any) -> None:
    _object("method", method)
    _allowed("method", method, {"name", "baseline", "retrieval_method"})
    for field in ("name", "retrieval_method"):
        _text(method, field, "method")
    if method.get("baseline") not in RETRIEVAL_BASELINES:
        raise BenchmarkManifestValidationError("method.baseline is invalid")


def _validate_retrieval_model(model: Any) -> None:
    _object("model", model)
    _allowed(
        "model",
        model,
        {
            "provider",
            "model_id",
            "representation_version",
            "dimensions",
            "metric",
            "prompt_digest",
        },
    )
    for field in ("provider", "model_id", "prompt_digest"):
        if model.get(field) is not None and (
            not isinstance(model[field], str) or not model[field]
        ):
            raise BenchmarkManifestValidationError(
                f"model.{field} must be non-empty or null"
            )
    _text(model, "representation_version", "model")
    dimensions = model.get("dimensions")
    if dimensions is not None and (
        not isinstance(dimensions, int)
        or isinstance(dimensions, bool)
        or dimensions < 1
    ):
        raise BenchmarkManifestValidationError(
            "model.dimensions must be positive or null"
        )
    _text(model, "metric", "model")
    if model.get("prompt_digest") is not None:
        _digest(model, "prompt_digest", "model")
    if bool(model.get("provider")) != bool(model.get("model_id")):
        raise BenchmarkManifestValidationError(
            "model.provider and model_id must be supplied together"
        )


def _validate_retrieval_boundaries(boundaries: Any) -> None:
    _object("boundaries", boundaries)
    _allowed("boundaries", boundaries, {"negative_knowledge", "novelty", "analogy"})
    negative = boundaries.get("negative_knowledge")
    _object("boundaries.negative_knowledge", negative)
    _allowed(
        "boundaries.negative_knowledge",
        negative,
        {"excluded_from_corpus", "excluded_from_candidate_generation"},
    )
    if (
        negative.get("excluded_from_corpus") is not True
        or negative.get("excluded_from_candidate_generation") is not True
    ):
        raise BenchmarkManifestValidationError("negative-knowledge must be excluded")
    novelty = boundaries.get("novelty")
    _object("boundaries.novelty", novelty)
    _allowed(
        "boundaries.novelty",
        novelty,
        {"reference_window", "dimensions", "aggregate_score_allowed"},
    )
    _text(novelty, "reference_window", "boundaries.novelty")
    dimensions = set(_string_list(novelty, "dimensions", "boundaries.novelty"))
    if dimensions != RETRIEVAL_NOVELTY_DIMENSIONS:
        raise BenchmarkManifestValidationError(
            "novelty must declare all six dimensions"
        )
    if novelty.get("aggregate_score_allowed") is not False:
        raise BenchmarkManifestValidationError(
            "novelty.aggregate_score_allowed must remain false"
        )
    analogy = boundaries.get("analogy")
    _object("boundaries.analogy", analogy)
    _allowed(
        "boundaries.analogy",
        analogy,
        {
            "non_equivalence_required",
            "historical_influence_requires_direct_evidence",
            "substitutability_not_implied",
        },
    )
    for field in (
        "non_equivalence_required",
        "historical_influence_requires_direct_evidence",
        "substitutability_not_implied",
    ):
        if analogy.get(field) is not True:
            raise BenchmarkManifestValidationError(
                f"boundaries.analogy.{field} must remain true"
            )


def _validate_query_result(
    query_result: Any,
    label: str,
    query_ids: set[str],
    document_ids: set[str],
    document_evidence: Mapping[str, set[str]],
    document_metadata: Mapping[str, Mapping[str, Any]],
) -> None:
    _object(label, query_result)
    _allowed(
        label, query_result, {"query_id", "abstained", "abstention_reason", "results"}
    )
    _text(query_result, "query_id", label)
    if query_result["query_id"] not in query_ids:
        raise BenchmarkManifestValidationError(f"{label}.query_id is unknown")
    if not isinstance(query_result.get("abstained"), bool):
        raise BenchmarkManifestValidationError(f"{label}.abstained must be boolean")
    if query_result.get("abstention_reason") is not None and (
        not isinstance(query_result["abstention_reason"], str)
        or not query_result["abstention_reason"]
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.abstention_reason must be non-empty or null"
        )
    results = _list(query_result, "results", label)
    if query_result["abstained"] and results:
        raise BenchmarkManifestValidationError(
            f"{label} cannot return results after abstention"
        )
    previous_rank = 0
    seen: set[str] = set()
    for index, result in enumerate(results):
        result_label = f"{label}.results[{index}]"
        _validate_retrieval_result(
            result,
            result_label,
            document_ids,
            document_evidence,
            document_metadata,
        )
        if result["rank"] != previous_rank + 1:
            raise BenchmarkManifestValidationError(
                f"{result_label}.rank must be contiguous and deterministic"
            )
        previous_rank = result["rank"]
        document_id = result["document"]["id"]
        if document_id in seen:
            raise BenchmarkManifestValidationError(
                f"duplicate result document: {document_id}"
            )
        seen.add(document_id)


def _validate_retrieval_result(
    result: Any,
    label: str,
    document_ids: set[str],
    document_evidence: Mapping[str, set[str]],
    document_metadata: Mapping[str, Mapping[str, Any]],
) -> None:
    _object(label, result)
    _allowed(
        label,
        result,
        {"rank", "score", "score_kind", "document", "evidence", "provenance"},
    )
    rank = result.get("rank")
    if not isinstance(rank, int) or isinstance(rank, bool) or not 1 <= rank <= 50:
        raise BenchmarkManifestValidationError(
            f"{label}.rank must be an integer from 1 to 50"
        )
    if (
        not isinstance(result.get("score"), (int, float))
        or isinstance(result["score"], bool)
        or not math.isfinite(result["score"])
    ):
        raise BenchmarkManifestValidationError(f"{label}.score must be finite")
    _text(result, "score_kind", label)
    document = result.get("document")
    _object(f"{label}.document", document)
    _allowed(
        f"{label}.document",
        document,
        {
            "id",
            "record_kind",
            "system_id",
            "feature_id",
            "name",
            "description",
            "claim_type",
            "claim_status",
            "evidence_ids",
            "validity_scope",
            "scope_context",
        },
    )
    _text(document, "id", f"{label}.document")
    if document["id"] not in document_ids:
        raise BenchmarkManifestValidationError(f"{label}.document.id is not in corpus")
    if (
        document.get("record_kind") not in RETRIEVAL_RECORD_KINDS
        or document.get("claim_type") not in CLAIM_TYPES
        or document.get("claim_status") not in CLAIM_STATUSES
    ):
        raise BenchmarkManifestValidationError(
            f"{label} has invalid record or claim type"
        )
    _non_empty_string_list(document, "evidence_ids", f"{label}.document")
    if set(document["evidence_ids"]) != document_evidence[document["id"]]:
        raise BenchmarkManifestValidationError(
            f"{label}.evidence_ids must preserve local corpus evidence closure"
        )
    _validate_scope(document.get("validity_scope"), f"{label}.document.validity_scope")
    if "scope_context" in document:
        _validate_scope_context(
            document["scope_context"],
            f"{label}.document.scope_context",
            document_evidence[document["id"]],
        )
    corpus_document = document_metadata[document["id"]]
    for field in (
        "record_kind",
        "claim_type",
        "claim_status",
        "validity_scope",
        "scope_context",
    ):
        if document.get(field) != corpus_document.get(field):
            raise BenchmarkManifestValidationError(
                f"{label}.document.{field} does not match corpus"
            )
    evidence = _list(result, "evidence", label)
    evidence_ids: set[str] = set()
    for index, evidence_record in enumerate(evidence):
        evidence_label = f"{label}.evidence[{index}]"
        _object(evidence_label, evidence_record)
        _allowed(evidence_label, evidence_record, {"id", "kind", "title", "uri"})
        _text(evidence_record, "id", evidence_label)
        if evidence_record["id"] in evidence_ids:
            raise BenchmarkManifestValidationError(
                f"duplicate result evidence id: {evidence_record['id']}"
            )
        evidence_ids.add(evidence_record["id"])
    if not evidence_ids.issuperset(document["evidence_ids"]):
        raise BenchmarkManifestValidationError(
            f"{label}.evidence must close document evidence IDs"
        )
    provenance = result.get("provenance")
    _object(f"{label}.provenance", provenance)
    _allowed(
        f"{label}.provenance",
        provenance,
        {"source_ref", "source_digest", "retrieval_method"},
    )
    _text(provenance, "source_ref", f"{label}.provenance")
    _digest(provenance, "source_digest", f"{label}.provenance")
    _text(provenance, "retrieval_method", f"{label}.provenance")
    if provenance["source_ref"] != corpus_document["source_ref"]:
        raise BenchmarkManifestValidationError(
            f"{label}.provenance.source_ref does not match corpus"
        )
    if provenance["source_digest"] != corpus_document["source_digest"]:
        raise BenchmarkManifestValidationError(
            f"{label}.provenance.source_digest does not match corpus"
        )


def _validate_retrieval_metrics(metrics: Any) -> None:
    _object("metrics", metrics)
    names = {
        "recall_at_k",
        "ndcg_at_k",
        "evidence_locality",
        "claim_type_accuracy",
        "scope_completeness",
        "false_link_rate",
        "abstention_rate",
    }
    _allowed("metrics", metrics, names)
    for field in ("recall_at_k", "ndcg_at_k"):
        records = _list(metrics, field, "metrics")
        for index, record in enumerate(records):
            _validate_metric(record, f"metrics.{field}[{index}]")
            if (
                "k" not in record
                or not isinstance(record["k"], int)
                or not 1 <= record["k"] <= 50
            ):
                raise BenchmarkManifestValidationError(
                    f"metrics.{field}[{index}].k is invalid"
                )
    for field in (
        "evidence_locality",
        "claim_type_accuracy",
        "scope_completeness",
        "false_link_rate",
        "abstention_rate",
    ):
        _validate_metric(metrics.get(field), f"metrics.{field}")


def _validate_metric(metric: Any, label: str) -> None:
    _object(label, metric)
    _allowed(label, metric, {"k", "numerator", "denominator", "value"})
    if (
        not isinstance(metric.get("numerator"), (int, float))
        or isinstance(metric["numerator"], bool)
        or not math.isfinite(metric["numerator"])
        or metric["numerator"] < 0
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.numerator must be non-negative"
        )
    if (
        not isinstance(metric.get("denominator"), int)
        or isinstance(metric["denominator"], bool)
        or metric["denominator"] < 0
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.denominator must be non-negative integer"
        )
    if metric["numerator"] > metric["denominator"]:
        raise BenchmarkManifestValidationError(
            f"{label}.numerator cannot exceed denominator"
        )
    metric_value = metric.get("value")
    if metric_value is not None and (
        not isinstance(metric_value, (int, float))
        or isinstance(metric_value, bool)
        or not 0 <= metric_value <= 1
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.value must be null or between 0 and 1"
        )
    if metric["denominator"] == 0 and metric_value is not None:
        raise BenchmarkManifestValidationError(
            f"{label}.value must be null for an empty denominator"
        )
    if metric["denominator"] > 0 and metric_value is None:
        raise BenchmarkManifestValidationError(
            f"{label}.value is required for a non-empty denominator"
        )
    if metric_value is not None and (
        not math.isfinite(metric_value)
        or not math.isclose(metric_value, metric["numerator"] / metric["denominator"])
    ):
        raise BenchmarkManifestValidationError(
            f"{label}.value must equal numerator divided by denominator"
        )


def _validate_retrieval_result_boundary(boundary: Any) -> None:
    _object("result_boundary", boundary)
    _allowed(
        "result_boundary",
        boundary,
        {
            "canonical",
            "storage_scope",
            "promotion_requires_human_review",
            "discovery_only",
            "score_is_truth",
            "score_is_compatibility",
        },
    )
    if (
        boundary.get("canonical") is not False
        or boundary.get("promotion_requires_human_review") is not True
    ):
        raise BenchmarkManifestValidationError("retrieval results cannot be canonical")
    if boundary.get("storage_scope") not in {"research", "draft"}:
        raise BenchmarkManifestValidationError(
            "result_boundary.storage_scope is invalid"
        )
    if (
        boundary.get("discovery_only") is not True
        or boundary.get("score_is_truth") is not False
        or boundary.get("score_is_compatibility") is not False
    ):
        raise BenchmarkManifestValidationError("retrieval metrics are discovery-only")


def _object(label: str, value: Any) -> None:
    if not isinstance(value, Mapping):
        raise BenchmarkManifestValidationError(f"{label} must be an object")


def _allowed(label: str, value: Mapping[str, Any], fields: set[str]) -> None:
    unknown = sorted(set(value) - fields)
    if unknown:
        raise BenchmarkManifestValidationError(f"{label} has unknown fields: {unknown}")


def _text(value: Mapping[str, Any], field: str, label: str = "manifest") -> None:
    if not isinstance(value.get(field), str) or not value[field]:
        raise BenchmarkManifestValidationError(
            f"{label}.{field} needs a non-empty string"
        )


def _list(value: Mapping[str, Any], field: str, label: str = "manifest") -> list[Any]:
    result = value.get(field)
    if not isinstance(result, list):
        raise BenchmarkManifestValidationError(f"{label}.{field} must be a list")
    return result


def _string_list(
    value: Mapping[str, Any], field: str, label: str = "manifest"
) -> list[str]:
    result = _list(value, field, label)
    if any(not isinstance(item, str) or not item for item in result):
        raise BenchmarkManifestValidationError(
            f"{label}.{field} must be a list of strings"
        )
    return result


def _non_empty_string_list(
    value: Mapping[str, Any], field: str, label: str = "manifest"
) -> list[str]:
    result = _string_list(value, field, label)
    if not result:
        raise BenchmarkManifestValidationError(f"{label}.{field} must not be empty")
    return result


def _evidence_ids(
    value: Mapping[str, Any],
    field: str,
    evidence_set: set[str],
    label: str,
) -> None:
    ids = _string_list(value, field, label)
    if not ids:
        raise BenchmarkManifestValidationError(f"{label}.{field} must not be empty")
    if len(set(ids)) != len(ids):
        raise BenchmarkManifestValidationError(f"{label}.{field} must be unique")
    unknown = sorted(set(ids) - evidence_set)
    if unknown:
        raise BenchmarkManifestValidationError(
            f"{label}.{field} has unknown evidence ids: {unknown}"
        )


def _validate_claim(
    claim: Any, label: str, evidence_set: set[str], claim_ids: set[str]
) -> None:
    _object(label, claim)
    _allowed(
        label,
        claim,
        {"id", "description", "claim_type", "claim_status", "evidence_ids"},
    )
    _text(claim, "id", label)
    _text(claim, "description", label)
    if claim["id"] in claim_ids:
        raise BenchmarkManifestValidationError(f"duplicate claim id: {claim['id']}")
    claim_ids.add(claim["id"])
    if claim.get("claim_type") not in CLAIM_TYPES:
        raise BenchmarkManifestValidationError(f"{label}.claim_type is invalid")
    if claim.get("claim_status") not in CLAIM_STATUSES:
        raise BenchmarkManifestValidationError(f"{label}.claim_status is invalid")
    _evidence_ids(claim, "evidence_ids", evidence_set, label)

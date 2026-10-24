"""Research-only manifests and deterministic metrics for MTH-0118.

This module intentionally does not run models, contact deployment origins, or
promote any candidate.  It validates an audit manifest and computes metrics
from already-normalized, reviewed inputs.  The metric functions use explicit
judgments (for example, ``supported`` or ``expected_claim_type``); they do not
infer evidence support from names, URLs, or prose similarity.
"""

from __future__ import annotations

import copy
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

BENCHMARK_MANIFEST_SCHEMA_VERSION = "1.1"
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


class BenchmarkManifestValidationError(ValueError):
    """Raised when a benchmark run manifest violates the research contract."""


@dataclass(frozen=True, slots=True)
class Metric:
    """A numerator/denominator metric with an explicit empty denominator."""

    name: str
    numerator: int
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


def discover_benchmark_manifests(path: Path) -> list[Path]:
    """Return benchmark manifest files in deterministic order."""

    if path.is_file():
        return [path]
    if not path.is_dir():
        return []
    return sorted(
        candidate for candidate in path.rglob("*.json") if candidate.is_file()
    )


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
    _allowed("manifest", value, required)
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
        {"origin", "version", "conditions", "exclusions", "workload"},
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

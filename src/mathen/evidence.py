"""Validation for additive experimental and operational evidence records.

Observation records are deliberately stricter than legacy ``experiment``
records.  The legacy shape remains readable, while records carrying
``observation_version`` are required to preserve the boundary, provenance,
scope, and null/abstention semantics needed for review.
"""

from __future__ import annotations

import copy
import math
import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from .scope import ScopeContextValidationError, validate_scope_context

OBSERVATION_KINDS = frozenset(
    {
        "experiment",
        "benchmark",
        "fault-injection",
        "operational-observation",
        "counterexample",
        "negative-result",
    }
)
OBSERVATION_VERSION = "1"
OBSERVATION_REQUIRED_FIELDS = (
    "observation_version",
    "protocol",
    "system_commit",
    "command",
    "dataset",
    "repetitions",
    "metrics",
    "artifacts",
    "workload",
    "environment",
    "conditions",
    "provenance",
    "result_boundary",
    "result",
    "review",
)
RESULT_STATUSES = frozenset(
    {"observed", "not-observed", "inconclusive", "abstained", "failed"}
)
MEASUREMENT_STATUSES = frozenset(
    {"observed", "not-observed", "not-measured", "abstained"}
)
ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._:-]*$")


def is_observation_record(evidence: Mapping[str, Any]) -> bool:
    """Return whether an evidence item uses the v1 observation contract."""

    return evidence.get("kind") in OBSERVATION_KINDS and (
        evidence.get("observation_version") == OBSERVATION_VERSION
    )


@dataclass(frozen=True, slots=True)
class ObservationEvidence:
    """Detached model for a validated v1 observation record."""

    value: dict[str, Any]

    @classmethod
    def from_dict(
        cls, evidence: Mapping[str, Any], evidence_ids: set[str]
    ) -> "ObservationEvidence":
        validate_observation_evidence(evidence, evidence_ids, "observation")
        return cls(copy.deepcopy(dict(evidence)))

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible record."""

        return copy.deepcopy(self.value)


def validate_observation_evidence(
    evidence: Mapping[str, Any], evidence_ids: set[str], label: str
) -> None:
    """Validate one v1 experiment, benchmark, or operational observation."""

    missing = [field for field in OBSERVATION_REQUIRED_FIELDS if field not in evidence]
    if missing:
        raise ValueError(f"{label} missing observation fields: {missing}")
    if evidence["observation_version"] != OBSERVATION_VERSION:
        raise ValueError(f"{label}.observation_version is unsupported")
    _stable_id(evidence.get("id"), f"{label}.id")

    for field in ("protocol", "system_commit", "command"):
        _non_empty_text(evidence.get(field), f"{label}.{field}")
    _text_or_object(evidence["dataset"], f"{label}.dataset")
    repetitions = evidence["repetitions"]
    if (
        isinstance(repetitions, bool)
        or not isinstance(repetitions, int)
        or repetitions < 1
    ):
        raise ValueError(f"{label}.repetitions must be a positive integer")
    metrics = evidence["metrics"]
    if not isinstance(metrics, Mapping):
        raise ValueError(f"{label}.metrics must be an object")
    for name, value in metrics.items():
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(f"{label}.metrics.{name} must be a finite number or null")

    for field in ("workload", "environment", "conditions"):
        _text_or_object(evidence[field], f"{label}.{field}")

    scope = evidence.get("scope_context")
    if not isinstance(scope, Mapping):
        raise ValueError(f"{label}.scope_context is required for observation records")
    try:
        validate_scope_context(
            scope, evidence_ids=evidence_ids, label=f"{label}.scope_context"
        )
    except ScopeContextValidationError as error:
        raise ValueError(str(error)) from error

    provenance = _object(evidence["provenance"], f"{label}.provenance")
    _exact_fields(
        provenance,
        {
            "run_id",
            "source_revision",
            "protocol_digest",
            "recorded_at",
            "runner",
            "toolchain",
        },
        f"{label}.provenance",
    )
    for field in (
        "run_id",
        "source_revision",
        "protocol_digest",
        "recorded_at",
        "runner",
    ):
        _non_empty_text(provenance.get(field), f"{label}.provenance.{field}")
    _text_or_object(provenance["toolchain"], f"{label}.provenance.toolchain")
    if provenance["source_revision"] != evidence.get("system_commit"):
        raise ValueError(f"{label}.provenance.source_revision must equal system_commit")

    boundary = _object(evidence["result_boundary"], f"{label}.result_boundary")
    _exact_fields(
        boundary,
        {"canonical", "promotion_requires_human_review", "storage_scope", "limits"},
        f"{label}.result_boundary",
    )
    if boundary.get("canonical") is not False:
        raise ValueError(f"{label}.result_boundary.canonical must remain false")
    if boundary.get("promotion_requires_human_review") is not True:
        raise ValueError(
            f"{label}.result_boundary.promotion_requires_human_review must remain true"
        )
    if boundary.get("storage_scope") not in {"research", "draft"}:
        raise ValueError(f"{label}.result_boundary.storage_scope is invalid")
    _non_empty_string_list(boundary.get("limits"), f"{label}.result_boundary.limits")

    result = _object(evidence["result"], f"{label}.result")
    _exact_fields(
        result,
        {"status", "summary", "measurements", "abstention_reason"},
        f"{label}.result",
    )
    if result.get("status") not in RESULT_STATUSES:
        raise ValueError(f"{label}.result.status is invalid")
    _non_empty_text(result.get("summary"), f"{label}.result.summary")
    measurements = result.get("measurements")
    if not isinstance(measurements, list):
        raise ValueError(f"{label}.result.measurements must be a list")
    measurement_ids: set[str] = set()
    for index, measurement in enumerate(measurements):
        measurement_label = f"{label}.result.measurements[{index}]"
        measurement = _object(measurement, measurement_label)
        _exact_fields(
            measurement,
            {"id", "value", "unit", "status", "notes"},
            measurement_label,
        )
        measurement_id = measurement.get("id")
        _stable_id(measurement_id, f"{measurement_label}.id")
        if measurement_id in measurement_ids:
            raise ValueError(f"{measurement_label}.id is duplicated")
        measurement_ids.add(measurement_id)
        _non_empty_text(measurement.get("unit"), f"{measurement_label}.unit")
        status = measurement.get("status")
        if status not in MEASUREMENT_STATUSES:
            raise ValueError(f"{measurement_label}.status is invalid")
        value = measurement.get("value")
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError(
                f"{measurement_label}.value must be a finite number or null"
            )
        if (status == "observed") != (value is not None):
            raise ValueError(f"{measurement_label}.value nullability must match status")
        if "notes" in measurement:
            _non_empty_text(measurement["notes"], f"{measurement_label}.notes")
    if result["status"] == "abstained":
        _non_empty_text(
            result.get("abstention_reason"), f"{label}.result.abstention_reason"
        )
    elif result.get("abstention_reason") is not None:
        raise ValueError(
            f"{label}.result.abstention_reason is only valid for abstained results"
        )

    _validate_artifacts(evidence.get("artifacts"), label)
    review = _object(evidence["review"], f"{label}.review")
    _exact_fields(
        review,
        {"status", "reviewer", "reviewed_at", "card_claim_refs"},
        f"{label}.review",
    )
    if review.get("status") not in {"unreviewed", "reviewed"}:
        raise ValueError(f"{label}.review.status is invalid")
    refs = _non_empty_string_list(
        review.get("card_claim_refs", []),
        f"{label}.review.card_claim_refs",
        allow_empty=True,
    )
    if len(refs) != len(set(refs)):
        raise ValueError(f"{label}.review.card_claim_refs must be unique")
    if review["status"] == "reviewed":
        _non_empty_text(review.get("reviewer"), f"{label}.review.reviewer")
        _non_empty_text(review.get("reviewed_at"), f"{label}.review.reviewed_at")
        if not refs:
            raise ValueError(
                f"{label}.reviewed records require card_claim_refs for closure"
            )
    elif refs:
        raise ValueError(f"{label}.review.card_claim_refs require reviewed status")

    kind = evidence["kind"]
    if kind == "fault-injection":
        _validate_failure(evidence.get("failure"), label, evidence_ids)
    elif kind == "counterexample":
        _validate_counterexample(evidence.get("counterexample"), label, evidence_ids)
    elif kind == "negative-result":
        _validate_negative_result(evidence.get("negative_result"), label, evidence_ids)


def _validate_failure(value: Any, label: str, evidence_ids: set[str]) -> None:
    record = _object(value, f"{label}.failure")
    _exact_fields(
        record,
        {"trigger", "observed_behavior", "boundary", "evidence_ids"},
        f"{label}.failure",
    )
    for field in ("trigger", "observed_behavior", "boundary"):
        _non_empty_text(record.get(field), f"{label}.failure.{field}")
    _local_evidence_ids(record.get("evidence_ids"), evidence_ids, f"{label}.failure")


def _validate_counterexample(value: Any, label: str, evidence_ids: set[str]) -> None:
    record = _object(value, f"{label}.counterexample")
    _exact_fields(
        record,
        {"target_claim", "condition", "observed_result", "implication", "evidence_ids"},
        f"{label}.counterexample",
    )
    for field in ("target_claim", "condition", "observed_result", "implication"):
        _non_empty_text(record.get(field), f"{label}.counterexample.{field}")
    _local_evidence_ids(
        record.get("evidence_ids"), evidence_ids, f"{label}.counterexample"
    )


def _validate_negative_result(value: Any, label: str, evidence_ids: set[str]) -> None:
    record = _object(value, f"{label}.negative_result")
    _exact_fields(
        record,
        {"question", "result", "reason", "evidence_ids"},
        f"{label}.negative_result",
    )
    for field in ("question", "result", "reason"):
        _non_empty_text(record.get(field), f"{label}.negative_result.{field}")
    _local_evidence_ids(
        record.get("evidence_ids"), evidence_ids, f"{label}.negative_result"
    )


def _validate_artifacts(value: Any, label: str) -> None:
    if not isinstance(value, list):
        raise ValueError(f"{label}.artifacts must be a list")
    ids: set[str] = set()
    for index, artifact in enumerate(value):
        item_label = f"{label}.artifacts[{index}]"
        artifact = _object(artifact, item_label)
        _exact_fields(artifact, {"id", "kind", "uri", "path", "digest"}, item_label)
        _stable_id(artifact.get("id"), f"{item_label}.id")
        if artifact["id"] in ids:
            raise ValueError(f"{item_label}.id is duplicated")
        ids.add(artifact["id"])
        _non_empty_text(artifact.get("kind"), f"{item_label}.kind")
        if not artifact.get("uri") and not artifact.get("path"):
            raise ValueError(f"{item_label} needs uri or path")
        for field in ("uri", "path", "digest"):
            if field in artifact:
                _non_empty_text(artifact[field], f"{item_label}.{field}")


def _local_evidence_ids(value: Any, evidence_ids: set[str], label: str) -> None:
    refs = _non_empty_string_list(value, f"{label}.evidence_ids")
    if len(refs) != len(set(refs)):
        raise ValueError(f"{label}.evidence_ids must be unique")
    unknown = set(refs) - evidence_ids
    if unknown:
        raise ValueError(f"{label} has unknown evidence ids: {sorted(unknown)}")


def _object(value: Any, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be an object")
    return dict(value)


def _exact_fields(value: Mapping[str, Any], allowed: set[str], label: str) -> None:
    unexpected = set(value) - allowed
    if unexpected:
        raise ValueError(f"{label} has unexpected fields: {sorted(unexpected)}")


def _non_empty_text(value: Any, label: str) -> None:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-empty string")


def _text_or_object(value: Any, label: str) -> None:
    if isinstance(value, str):
        _non_empty_text(value, label)
    elif isinstance(value, Mapping) and value:
        return
    else:
        raise ValueError(f"{label} must be a non-empty string or object")


def _non_empty_string_list(
    value: Any, label: str, *, allow_empty: bool = False
) -> list[str]:
    if not isinstance(value, list) or (not allow_empty and not value):
        raise ValueError(f"{label} must be a non-empty list of strings")
    if not all(isinstance(item, str) and item.strip() for item in value):
        raise ValueError(f"{label} must contain non-empty strings")
    return value


def _stable_id(value: Any, label: str) -> None:
    if not isinstance(value, str) or not ID_PATTERN.fullmatch(value):
        raise ValueError(f"{label} must be a stable lowercase identifier")

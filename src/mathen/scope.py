"""Evidence-bounded deployment and operating-scope metadata.

``scope_context`` is additive metadata.  It does not change the claim type of
the record that owns it, and an ``unspecified`` dimension is an absence of a
scope claim, not evidence that the dimension does not apply.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

SCOPE_CONTEXT_FIELDS = frozenset(
    {
        "validity_scope",
        "workload",
        "runtime_conditions",
        "scale",
        "failure_conditions",
    }
)
SCOPE_STATES = frozenset({"specified", "unknown", "unspecified", "not-applicable"})
VALIDITY_STATES = frozenset({"specified", "unknown", "unspecified", "not-applicable"})
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)


class ScopeContextValidationError(ValueError):
    """Raised when evidence-bounded scope metadata is malformed."""


def validate_scope_context(
    value: Any,
    *,
    evidence_ids: set[str] | None = None,
    label: str = "scope_context",
) -> None:
    """Validate a complete scope context and its local evidence closure.

    All dimensions are required once the envelope is present.  A producer that
    has not established a dimension must include it with ``status`` equal to
    ``unspecified`` rather than omitting it.
    """

    _object(label, value)
    if set(value) != SCOPE_CONTEXT_FIELDS:
        raise ScopeContextValidationError(
            f"{label} must contain exactly {sorted(SCOPE_CONTEXT_FIELDS)}"
        )
    _validate_validity_scope(
        f"{label}.validity_scope", value["validity_scope"], evidence_ids
    )
    for field in sorted(SCOPE_CONTEXT_FIELDS - {"validity_scope"}):
        _validate_dimension(f"{label}.{field}", value[field], evidence_ids)


def _validate_validity_scope(
    label: str, value: Any, evidence_ids: set[str] | None
) -> None:
    _object(label, value)
    required = {
        "status",
        "systems",
        "versions",
        "deployment_origins",
        "conditions",
        "exclusions",
        "evidence_ids",
    }
    allowed = required | {"claim_type", "claim_status", "notes"}
    _fields(label, value, required, allowed)
    status = value["status"]
    if status not in VALIDITY_STATES:
        raise ScopeContextValidationError(f"{label}.status is invalid")
    for field in (
        "systems",
        "versions",
        "deployment_origins",
        "conditions",
        "exclusions",
    ):
        _strings(label, field, value[field])
    _validate_basis(label, value, status, evidence_ids, validity=True)
    if status != "specified" and any(
        value[field]
        for field in (
            "systems",
            "versions",
            "deployment_origins",
            "conditions",
            "exclusions",
        )
    ):
        raise ScopeContextValidationError(
            f"{label} non-specified status must not contain boundary values"
        )
    if status == "not-applicable" and (
        not isinstance(value.get("notes"), str) or not value["notes"].strip()
    ):
        raise ScopeContextValidationError(f"{label} not-applicable status needs notes")
    if status == "specified" and not any(
        value[field]
        for field in (
            "systems",
            "versions",
            "deployment_origins",
            "conditions",
            "exclusions",
        )
    ):
        raise ScopeContextValidationError(
            f"{label} specified status needs at least one declared boundary"
        )


def _validate_dimension(label: str, value: Any, evidence_ids: set[str] | None) -> None:
    _object(label, value)
    required = {"status", "values", "evidence_ids"}
    allowed = required | {"claim_type", "claim_status", "notes"}
    _fields(label, value, required, allowed)
    status = value["status"]
    if status not in SCOPE_STATES:
        raise ScopeContextValidationError(f"{label}.status is invalid")
    _strings(label, "values", value["values"])
    _validate_basis(label, value, status, evidence_ids)
    if status == "specified" and not value["values"]:
        raise ScopeContextValidationError(f"{label} specified status needs values")
    if status != "specified" and value["values"]:
        raise ScopeContextValidationError(
            f"{label} non-specified status must not contain values"
        )
    if status == "not-applicable" and (
        not isinstance(value.get("notes"), str) or not value["notes"].strip()
    ):
        raise ScopeContextValidationError(f"{label} not-applicable status needs notes")


def _validate_basis(
    label: str,
    value: Mapping[str, Any],
    status: str,
    evidence_ids: set[str] | None,
    *,
    validity: bool = False,
) -> None:
    cited = value["evidence_ids"]
    _strings(label, "evidence_ids", cited)
    if len(cited) != len(set(cited)):
        raise ScopeContextValidationError(f"{label}.evidence_ids contains duplicates")
    if evidence_ids is not None:
        unknown = set(cited) - evidence_ids
        if unknown:
            raise ScopeContextValidationError(
                f"{label}.evidence_ids references unknown evidence: {sorted(unknown)}"
            )
    if status == "unspecified":
        if cited or any(field in value for field in ("claim_type", "claim_status")):
            raise ScopeContextValidationError(
                f"{label} unspecified status cannot carry a claim or evidence"
            )
        return
    if not cited:
        raise ScopeContextValidationError(
            f"{label} status {status!r} needs evidence_ids"
        )
    for field, allowed in (
        ("claim_type", CLAIM_TYPES),
        ("claim_status", CLAIM_STATUSES),
    ):
        if value.get(field) not in allowed:
            raise ScopeContextValidationError(f"{label}.{field} is invalid")
    if validity and status == "unknown" and value.get("claim_type") == "analogy":
        raise ScopeContextValidationError(
            f"{label}.claim_type analogy cannot establish unknown validity scope"
        )


def _object(label: str, value: Any) -> None:
    if not isinstance(value, Mapping):
        raise ScopeContextValidationError(f"{label} must be an object")


def _fields(
    label: str,
    value: Mapping[str, Any],
    required: set[str],
    allowed: set[str],
) -> None:
    missing = required - value.keys()
    if missing:
        raise ScopeContextValidationError(f"{label} missing fields: {sorted(missing)}")
    unexpected = set(value) - allowed
    if unexpected:
        raise ScopeContextValidationError(
            f"{label} has unexpected fields: {sorted(unexpected)}"
        )
    if "notes" in value and (
        not isinstance(value["notes"], str) or not value["notes"].strip()
    ):
        raise ScopeContextValidationError(f"{label}.notes must be a non-empty string")


def _strings(label: str, field: str, value: Any) -> None:
    if not isinstance(value, list) or any(
        not isinstance(item, str) or not item.strip() for item in value
    ):
        raise ScopeContextValidationError(
            f"{label}.{field} must be a list of non-empty strings"
        )
    if len(value) != len(set(value)):
        raise ScopeContextValidationError(f"{label}.{field} contains duplicates")

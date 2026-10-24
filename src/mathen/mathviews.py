"""Evidence-bounded, checkable mathematical architecture-view contracts.

The contracts in this module are candidate models, not formal proofs.  The
deterministic classifier only evaluates finite data supplied by the contract
and reports ``undetermined`` when the supplied representation is insufficient.
"""

from __future__ import annotations

import copy
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

MATHEMATICAL_VIEW_CONTRACT_VERSION = "1.0"
CONTRACT_FAMILIES = frozenset(
    {
        "graph",
        "dag",
        "partial_order",
        "state_machine",
        "algebraic",
        "semilattice",
        "monotone_system",
        "refinement",
        "simulation",
        "bisimulation",
        "cost",
        "complexity",
        "queueing",
        "reliability",
    }
)
CLASSIFICATION_RESULTS = frozenset({"valid", "invalid", "undetermined"})
CHECK_RESULTS = frozenset({"pass", "fail", "not-run"})
CLAIM_TYPES = frozenset({"fact", "inference", "hypothesis", "analogy"})
CLAIM_STATUSES = frozenset(
    {"proposed", "under-review", "accepted", "rejected", "deprecated"}
)
_ID_PATTERN = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TOP_LEVEL_FIELDS = {
    "schema_version",
    "id",
    "family",
    "question",
    "carrier",
    "state_space",
    "operations",
    "relations",
    "transitions",
    "laws_or_checks",
    "assumptions",
    "validity_scope",
    "parameters",
    "claim_type",
    "claim_status",
    "evidence_ids",
    "classification",
}
_REQUIRED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "id",
    "family",
    "question",
    "carrier",
    "operations",
    "relations",
    "transitions",
    "laws_or_checks",
    "assumptions",
    "validity_scope",
    "claim_type",
    "claim_status",
    "evidence_ids",
    "classification",
}


class MathematicalViewValidationError(ValueError):
    """Raised when a mathematical view contract is malformed or inconsistent."""


@dataclass(frozen=True, slots=True)
class MathematicalViewContract:
    """Immutable model for one validated mathematical view contract."""

    schema_version: str
    id: str
    family: str
    question: str
    carrier: dict[str, Any]
    state_space: dict[str, Any] | None
    operations: tuple[dict[str, Any], ...]
    relations: tuple[dict[str, Any], ...]
    transitions: tuple[dict[str, Any], ...]
    laws_or_checks: tuple[dict[str, Any], ...]
    assumptions: tuple[str, ...]
    validity_scope: dict[str, Any]
    parameters: dict[str, Any] | None
    claim_type: str
    claim_status: str
    evidence_ids: tuple[str, ...]
    classification: dict[str, Any]

    @classmethod
    def from_dict(
        cls, value: dict[str, Any], evidence_ids: set[str] | None = None
    ) -> "MathematicalViewContract":
        validate_math_view_contract(value, evidence_ids=evidence_ids)
        return cls(
            schema_version=value["schema_version"],
            id=value["id"],
            family=value["family"],
            question=value["question"],
            carrier=copy.deepcopy(value["carrier"]),
            state_space=copy.deepcopy(value.get("state_space")),
            operations=tuple(copy.deepcopy(value["operations"])),
            relations=tuple(copy.deepcopy(value["relations"])),
            transitions=tuple(copy.deepcopy(value["transitions"])),
            laws_or_checks=tuple(copy.deepcopy(value["laws_or_checks"])),
            assumptions=tuple(value["assumptions"]),
            validity_scope=copy.deepcopy(value["validity_scope"]),
            parameters=copy.deepcopy(value.get("parameters")),
            claim_type=value["claim_type"],
            claim_status=value["claim_status"],
            evidence_ids=tuple(value["evidence_ids"]),
            classification=copy.deepcopy(value["classification"]),
        )

    def to_dict(self) -> dict[str, Any]:
        """Return a detached JSON-compatible representation."""

        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "family": self.family,
            "question": self.question,
            "carrier": copy.deepcopy(self.carrier),
            **(
                {"state_space": copy.deepcopy(self.state_space)}
                if self.state_space is not None
                else {}
            ),
            "operations": [copy.deepcopy(item) for item in self.operations],
            "relations": [copy.deepcopy(item) for item in self.relations],
            "transitions": [copy.deepcopy(item) for item in self.transitions],
            "laws_or_checks": [copy.deepcopy(item) for item in self.laws_or_checks],
            "assumptions": list(self.assumptions),
            "validity_scope": copy.deepcopy(self.validity_scope),
            **(
                {"parameters": copy.deepcopy(self.parameters)}
                if self.parameters is not None
                else {}
            ),
            "claim_type": self.claim_type,
            "claim_status": self.claim_status,
            "evidence_ids": list(self.evidence_ids),
            "classification": copy.deepcopy(self.classification),
        }


def load_math_view_contract(
    path: Path, evidence_ids: set[str] | None = None
) -> MathematicalViewContract:
    """Load and validate one JSON mathematical-view contract."""

    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise MathematicalViewValidationError(
            f"{path}: invalid JSON: {error}"
        ) from error
    if not isinstance(value, dict):
        raise MathematicalViewValidationError(f"{path}: contract must be an object")
    try:
        return MathematicalViewContract.from_dict(value, evidence_ids=evidence_ids)
    except MathematicalViewValidationError as error:
        raise MathematicalViewValidationError(f"{path}: {error}") from error


def classify_math_view_contract(contract: dict[str, Any]) -> dict[str, Any]:
    """Return a deterministic classification for a structurally valid contract.

    This is a bounded consistency check over declared finite carriers, tables,
    relations, and numeric parameters.  ``valid`` means the supplied checks
    passed; it does not mean the architecture has been formally proved.
    """

    family = contract.get("family")
    if family in {"graph", "dag", "partial_order"}:
        return _classify_order_family(contract)
    if family == "state_machine":
        return _classify_state_machine(contract)
    if family in {"algebraic", "semilattice", "monotone_system"}:
        return _classify_algebraic_family(contract)
    if family in {"refinement", "simulation", "bisimulation"}:
        return _classify_simulation_family(contract)
    if family in {"cost", "complexity", "queueing", "reliability"}:
        return _classify_numeric_family(contract)
    return _result(
        "undetermined", "No deterministic classifier is defined for this family."
    )


def validate_math_view_contract(
    contract: dict[str, Any],
    *,
    evidence_ids: set[str] | None = None,
    path: Path | None = None,
) -> None:
    """Validate contract shape, evidence locality, references, and classification."""

    label = str(path) if path else str(contract.get("id", "mathematical-view"))
    if not isinstance(contract, dict):
        raise MathematicalViewValidationError(f"{label}: must be an object")
    missing = _REQUIRED_TOP_LEVEL_FIELDS - contract.keys()
    if missing:
        raise MathematicalViewValidationError(
            f"{label}: missing fields: {sorted(missing)}"
        )
    unexpected = contract.keys() - _TOP_LEVEL_FIELDS
    if unexpected:
        raise MathematicalViewValidationError(
            f"{label}: unexpected fields: {sorted(unexpected)}"
        )
    if contract["schema_version"] != MATHEMATICAL_VIEW_CONTRACT_VERSION:
        raise MathematicalViewValidationError(
            f"{label}: unsupported schema_version: {contract['schema_version']}"
        )
    for field in ("schema_version", "id", "family", "question"):
        _require_string(label, field, contract[field])
    _require_id(label, "id", contract["id"])
    if contract["family"] not in CONTRACT_FAMILIES:
        raise MathematicalViewValidationError(f"{label}: invalid family")
    _validate_carrier(label, contract["carrier"])
    _validate_state_space(label, contract.get("state_space"), contract["family"])
    _validate_string_list(
        label, "assumptions", contract["assumptions"], allow_empty=True
    )
    _validate_scope(label, contract["validity_scope"])
    _validate_claim_fields(label, contract, "contract", evidence_ids)
    if "parameters" in contract:
        if not isinstance(contract["parameters"], dict):
            raise MathematicalViewValidationError(
                f"{label}: parameters must be an object"
            )
        for name, value in contract["parameters"].items():
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise MathematicalViewValidationError(
                    f"{label}: parameters.{name} must be a number"
                )
            if not math.isfinite(value):
                raise MathematicalViewValidationError(
                    f"{label}: parameters.{name} must be finite"
                )
    ids = _validate_elements(label, contract)
    _validate_laws(label, contract["laws_or_checks"])
    _validate_classification(
        label, contract["classification"], contract["laws_or_checks"]
    )
    expected = classify_math_view_contract(contract)
    if contract["classification"]["result"] != expected["result"]:
        raise MathematicalViewValidationError(
            f"{label}: classification result is "
            f"{contract['classification']['result']!r}; deterministic checks "
            f"require {expected['result']!r}"
        )
    _validate_family_references(label, contract, ids)


def _validate_carrier(label: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise MathematicalViewValidationError(f"{label}: carrier must be an object")
    required = {"kind", "description", "elements"}
    if required - value.keys():
        raise MathematicalViewValidationError(
            f"{label}: carrier missing fields: {sorted(required - value.keys())}"
        )
    _require_string(label, "carrier.kind", value["kind"])
    _require_string(label, "carrier.description", value["description"])
    if not isinstance(value["elements"], list) or not all(
        isinstance(item, str) and item for item in value["elements"]
    ):
        raise MathematicalViewValidationError(
            f"{label}: carrier.elements must be a list of non-empty strings"
        )
    if len(set(value["elements"])) != len(value["elements"]):
        raise MathematicalViewValidationError(
            f"{label}: carrier.elements contains duplicates"
        )


def _validate_state_space(label: str, value: Any, family: str) -> None:
    if value is None:
        if family == "state_machine" or family in {
            "refinement",
            "simulation",
            "bisimulation",
        }:
            raise MathematicalViewValidationError(
                f"{label}: state_space is required for {family}"
            )
        return
    if not isinstance(value, dict):
        raise MathematicalViewValidationError(f"{label}: state_space must be an object")
    required = {"states", "initial", "terminal", "description"}
    if required - value.keys():
        raise MathematicalViewValidationError(
            f"{label}: state_space missing fields: {sorted(required - value.keys())}"
        )
    _require_string(label, "state_space.description", value["description"])
    for field in ("states", "initial", "terminal"):
        _validate_string_list(
            label, f"state_space.{field}", value[field], allow_empty=field == "terminal"
        )
    if not set(value["initial"]) <= set(value["states"]):
        raise MathematicalViewValidationError(
            f"{label}: state_space.initial references unknown state"
        )
    if not set(value["terminal"]) <= set(value["states"]):
        raise MathematicalViewValidationError(
            f"{label}: state_space.terminal references unknown state"
        )


def _validate_elements(label: str, contract: dict[str, Any]) -> dict[str, set[str]]:
    carrier = set(contract["carrier"]["elements"])
    ids: dict[str, set[str]] = {
        "operations": set(),
        "relations": set(),
        "transitions": set(),
        "laws_or_checks": set(),
    }
    for field in ids:
        values = contract[field]
        if not isinstance(values, list):
            raise MathematicalViewValidationError(f"{label}: {field} must be a list")
        for index, item in enumerate(values):
            item_label = f"{field}[{index}]"
            if not isinstance(item, dict):
                raise MathematicalViewValidationError(
                    f"{label}: {item_label} must be an object"
                )
            item_id = item.get("id")
            _require_id(label, f"{item_label}.id", item_id)
            if item_id in ids[field]:
                raise MathematicalViewValidationError(
                    f"{label}: duplicate {field} id: {item_id}"
                )
            if any(item_id in existing for existing in ids.values()):
                raise MathematicalViewValidationError(
                    f"{label}: duplicate contract element id: {item_id}"
                )
            ids[field].add(item_id)
            if field != "laws_or_checks":
                _require_string(label, f"{item_label}.name", item.get("name"))
    for index, relation in enumerate(contract["relations"]):
        pairs = relation.get("pairs")
        if not isinstance(pairs, list):
            raise MathematicalViewValidationError(
                f"{label}: relations[{index}].pairs must be a list"
            )
        for pair in pairs:
            if (
                not isinstance(pair, list)
                or len(pair) != 2
                or not all(item in carrier for item in pair)
            ):
                raise MathematicalViewValidationError(
                    f"{label}: relations[{index}] contains a pair outside the carrier"
                )
    return {**ids, "carrier": carrier}


def _validate_laws(label: str, values: Any) -> None:
    if not isinstance(values, list):
        raise MathematicalViewValidationError(f"{label}: laws_or_checks must be a list")
    for index, item in enumerate(values):
        if not isinstance(item, dict):
            raise MathematicalViewValidationError(
                f"{label}: laws_or_checks[{index}] must be an object"
            )
        _require_string(label, f"laws_or_checks[{index}].name", item.get("name"))
        _require_string(
            label, f"laws_or_checks[{index}].description", item.get("description")
        )
        _require_string(label, f"laws_or_checks[{index}].check", item.get("check"))


def _validate_classification(
    label: str, value: Any, laws: list[dict[str, Any]]
) -> None:
    if not isinstance(value, dict):
        raise MathematicalViewValidationError(
            f"{label}: classification must be an object"
        )
    if value.get("result") not in CLASSIFICATION_RESULTS:
        raise MathematicalViewValidationError(f"{label}: invalid classification.result")
    _require_string(label, "classification.reason", value.get("reason"))
    checks = value.get("checks")
    law_ids = {item["id"] for item in laws}
    if not isinstance(checks, list):
        raise MathematicalViewValidationError(
            f"{label}: classification.checks must be a list"
        )
    for index, item in enumerate(checks):
        if not isinstance(item, dict) or item.get("id") not in law_ids:
            raise MathematicalViewValidationError(
                f"{label}: classification.checks[{index}] has unknown id"
            )
        if item.get("result") not in CHECK_RESULTS:
            raise MathematicalViewValidationError(
                f"{label}: invalid classification check result"
            )


def _validate_family_references(
    label: str, contract: dict[str, Any], ids: dict[str, set[str]]
) -> None:
    states = set(contract.get("state_space", {}).get("states", []))
    for index, transition in enumerate(contract["transitions"]):
        _require_string(label, f"transitions[{index}].label", transition.get("label"))
        for field in ("source", "target"):
            if transition.get(field) not in states:
                raise MathematicalViewValidationError(
                    f"{label}: transitions[{index}].{field} references unknown state"
                )
        if "system" in transition and not isinstance(transition["system"], str):
            raise MathematicalViewValidationError(
                f"{label}: transition system must be a string"
            )
        if contract["family"] in {"refinement", "simulation", "bisimulation"}:
            if transition.get("system") not in {"left", "right"}:
                raise MathematicalViewValidationError(
                    f"{label}: simulation transitions need system left or right"
                )
    if contract["family"] in {"refinement", "simulation", "bisimulation"}:
        state_space = set(contract["state_space"]["states"])
        for index, relation in enumerate(contract["relations"]):
            for pair in relation.get("pairs", []):
                if not set(pair) <= state_space:
                    raise MathematicalViewValidationError(
                        f"{label}: relations[{index}] references unknown state"
                    )
    for index, operation in enumerate(contract["operations"]):
        arity = operation.get("arity")
        if isinstance(arity, bool) or not isinstance(arity, int) or arity < 0:
            raise MathematicalViewValidationError(
                f"{label}: operations[{index}].arity must be a non-negative integer"
            )
        table = operation.get("table")
        if table is not None and not isinstance(table, dict):
            raise MathematicalViewValidationError(
                f"{label}: operations[{index}].table must be an object"
            )
        if table is not None:
            carrier = ids["carrier"]
            for key, result in table.items():
                parts = key.split("|")
                if (
                    len(parts) != arity
                    or any(part not in carrier for part in parts)
                    or result not in carrier
                ):
                    raise MathematicalViewValidationError(
                        f"{label}: operations[{index}].table is not closed over carrier"
                    )


def _validate_claim_fields(
    label: str, value: dict[str, Any], item: str, evidence_ids: set[str] | None
) -> None:
    if value.get("claim_type") not in CLAIM_TYPES:
        raise MathematicalViewValidationError(f"{label}: invalid {item} claim_type")
    if value.get("claim_status") not in CLAIM_STATUSES:
        raise MathematicalViewValidationError(f"{label}: invalid {item} claim_status")
    references = value.get("evidence_ids")
    if (
        not isinstance(references, list)
        or not references
        or not all(isinstance(ref, str) and ref for ref in references)
    ):
        raise MathematicalViewValidationError(
            f"{label}: {item}.evidence_ids must be a non-empty list"
        )
    if len(set(references)) != len(references):
        raise MathematicalViewValidationError(
            f"{label}: {item}.evidence_ids contains duplicates"
        )
    if evidence_ids is not None:
        unknown = set(references) - evidence_ids
        if unknown:
            raise MathematicalViewValidationError(
                f"{label}: {item} references unknown evidence ids: {sorted(unknown)}"
            )


def _validate_scope(label: str, value: Any) -> None:
    if not isinstance(value, dict):
        raise MathematicalViewValidationError(
            f"{label}: validity_scope must be an object"
        )
    required = {"systems", "versions", "deployment_origins", "conditions", "exclusions"}
    if required - value.keys():
        raise MathematicalViewValidationError(
            f"{label}: validity_scope missing fields: {sorted(required - value.keys())}"
        )
    for field in required:
        _validate_string_list(
            label,
            f"validity_scope.{field}",
            value[field],
            allow_empty=field == "exclusions",
        )


def _validate_string_list(
    label: str, field: str, value: Any, *, allow_empty: bool
) -> None:
    if (
        not isinstance(value, list)
        or (not allow_empty and not value)
        or not all(isinstance(item, str) and item for item in value)
    ):
        raise MathematicalViewValidationError(
            f"{label}: {field} must be a list of non-empty strings"
        )


def _require_string(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not value:
        raise MathematicalViewValidationError(
            f"{label}: {field} must be a non-empty string"
        )


def _require_id(label: str, field: str, value: Any) -> None:
    if not isinstance(value, str) or not _ID_PATTERN.fullmatch(value):
        raise MathematicalViewValidationError(
            f"{label}: {field} must be a lowercase id"
        )


def _result(
    result: str, reason: str, checks: list[dict[str, str]] | None = None
) -> dict[str, Any]:
    return {"result": result, "reason": reason, "checks": checks or []}


def _relation(contract: dict[str, Any], kind: str) -> dict[str, Any] | None:
    return next(
        (item for item in contract["relations"] if item.get("kind") == kind), None
    )


def _classify_order_family(contract: dict[str, Any]) -> dict[str, Any]:
    relation = contract["relations"][0] if contract["relations"] else None
    if relation is None:
        return _result(
            "invalid", "A graph-family contract needs at least one relation."
        )
    pairs = {tuple(pair) for pair in relation["pairs"]}
    carrier = set(contract["carrier"]["elements"])
    if contract["family"] == "graph":
        return _result(
            "valid", "The declared relation is a closed graph over the carrier."
        )
    if contract["family"] == "dag":
        if _has_cycle(carrier, pairs):
            return _result(
                "invalid", "The declared directed relation contains a cycle."
            )
        return _result("valid", "The declared directed relation is acyclic.")
    if not all((item, item) in pairs for item in carrier):
        return _result("invalid", "A partial order must be reflexive over the carrier.")
    if any(a != b and (b, a) in pairs for a, b in pairs):
        return _result("invalid", "A partial order must be antisymmetric.")
    if any((a, c) not in pairs for a, b in pairs for b2, c in pairs if b == b2):
        return _result("invalid", "A partial order must be transitive.")
    return _result(
        "valid", "The declared relation is reflexive, antisymmetric, and transitive."
    )


def _has_cycle(nodes: set[str], edges: set[tuple[str, str]]) -> bool:
    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(node: str) -> bool:
        if node in visiting:
            return True
        if node in visited:
            return False
        visiting.add(node)
        if any(source == node and visit(target) for source, target in edges):
            return True
        visiting.remove(node)
        visited.add(node)
        return False

    return any(visit(node) for node in nodes)


def _classify_state_machine(contract: dict[str, Any]) -> dict[str, Any]:
    state_space = contract["state_space"]
    if not state_space["initial"]:
        return _result("invalid", "A state machine needs at least one initial state.")
    return _result("valid", "All transitions are closed over the declared state space.")


def _table(operation: dict[str, Any]) -> dict[tuple[str, ...], str] | None:
    raw = operation.get("table")
    if not isinstance(raw, dict):
        return None
    return {tuple(key.split("|")): value for key, value in raw.items()}


def _classify_algebraic_family(contract: dict[str, Any]) -> dict[str, Any]:
    if contract["family"] == "monotone_system":
        order = next(
            (
                item
                for item in contract["relations"]
                if item.get("kind") in {"order", "partial-order", "ordering"}
            ),
            None,
        )
        operation = next(
            (item for item in contract["operations"] if item.get("arity") == 1), None
        )
        if order is None or operation is None or _table(operation) is None:
            return _result(
                "undetermined",
                "A monotone system needs an order relation and a finite unary table.",
            )
        table = _table(operation)
        ordered_pairs = [tuple(pair) for pair in order["pairs"]]
        if any(
            (x,) not in table
            or (y,) not in table
            or (table[(x,)], table[(y,)]) not in ordered_pairs
            for x, y in ordered_pairs
        ):
            return _result(
                "invalid",
                "The declared operation is not monotone over the supplied order.",
            )
        return _result(
            "valid",
            "The supplied unary operation preserves the declared order.",
        )
    operations = contract["operations"]
    binary = next((item for item in operations if item.get("arity") == 2), None)
    if binary is None or _table(binary) is None:
        return _result(
            "undetermined", "A finite operation table is required for these laws."
        )
    table = _table(binary)
    carrier = set(contract["carrier"]["elements"])
    if any((a, b) not in table for a in carrier for b in carrier):
        return _result("invalid", "The binary operation table is incomplete.")
    checks: list[dict[str, str]] = []
    requested = {item.get("check") for item in contract["laws_or_checks"]}
    if contract["family"] == "semilattice":
        requested |= {"associative", "commutative", "idempotent"}
    for check in sorted(requested):
        if check == "associative":
            passed = all(
                table[(table[(a, b)], c)] == table[(a, table[(b, c)])]
                for a in carrier
                for b in carrier
                for c in carrier
            )
        elif check == "commutative":
            passed = all(
                table[(a, b)] == table[(b, a)] for a in carrier for b in carrier
            )
        elif check == "idempotent":
            passed = all(table[(a, a)] == a for a in carrier)
        elif check == "closure":
            passed = all(table[(a, b)] in carrier for a in carrier for b in carrier)
        else:
            continue
        checks.append({"id": check, "result": "pass" if passed else "fail"})
        if not passed:
            return _result(
                "invalid", f"The declared operation fails the {check} law.", checks
            )
    if (
        contract["family"] == "semilattice"
        and {"associative", "commutative", "idempotent"} - requested
    ):
        return _result(
            "invalid",
            "A semilattice contract must declare its three defining laws.",
            checks,
        )
    return _result(
        "valid", "The supplied finite operation table passes the declared laws.", checks
    )


def _classify_simulation_family(contract: dict[str, Any]) -> dict[str, Any]:
    relation = contract["relations"][0] if contract["relations"] else None
    transitions = contract["transitions"]
    if relation is None or not transitions:
        return _result(
            "undetermined",
            "A relation and transitions are required to check simulation.",
        )
    pairs = {tuple(pair) for pair in relation["pairs"]}
    left = [item for item in transitions if item.get("system") == "left"]
    right = [item for item in transitions if item.get("system") == "right"]
    if not left or not right:
        return _result(
            "undetermined",
            "Both left and right transition systems are required to check simulation.",
        )

    def sim(
        source: list[dict[str, Any]], target: list[dict[str, Any]], direction: int
    ) -> bool:
        for transition in source:
            related = [
                pair
                for pair in pairs
                if pair[0 if direction == 0 else 1] == transition["source"]
            ]
            for pair in related:
                target_state = pair[1 if direction == 0 else 0]
                matches = [
                    item
                    for item in target
                    if item["source"] == target_state
                    and item.get("label") == transition.get("label")
                ]
                if direction == 0:
                    matched = any(
                        (transition["target"], item["target"]) in pairs
                        for item in matches
                    )
                else:
                    matched = any(
                        (item["target"], transition["target"]) in pairs
                        for item in matches
                    )
                if not matched:
                    return False
        return True

    forward = sim(left, right, 0)
    backward = sim(right, left, 1)
    passed = backward and forward if contract["family"] == "bisimulation" else forward
    if not passed:
        return _result(
            "invalid",
            "The declared state relation fails the requested simulation obligations.",
        )
    return _result(
        "valid",
        "The declared state relation satisfies the supplied transition obligations.",
    )


def _classify_numeric_family(contract: dict[str, Any]) -> dict[str, Any]:
    parameters = contract.get("parameters")
    if not parameters:
        return _result(
            "undetermined", "Numeric parameters are required for this model family."
        )
    if contract["family"] in {"cost", "complexity"}:
        if any(value < 0 for value in parameters.values()):
            return _result(
                "invalid", "Cost and complexity parameters must be non-negative."
            )
        return _result(
            "valid",
            "All supplied cost or complexity parameters are finite and non-negative.",
        )
    if contract["family"] == "queueing":
        arrival = parameters.get("arrival_rate")
        service = parameters.get("service_rate")
        if arrival is None or service is None:
            return _result(
                "undetermined",
                "A queueing model needs arrival_rate and service_rate parameters.",
            )
        if arrival < 0 or service <= 0:
            return _result(
                "invalid",
                "Queueing arrival rate must be non-negative and service rate positive.",
            )
        if arrival / service >= 1:
            return _result(
                "invalid",
                "The declared single-server queue is not stable at utilization >= 1.",
            )
        return _result(
            "valid",
            "The declared queue has finite positive service and utilization < 1.",
        )
    if any(not 0 <= value <= 1 for value in parameters.values()):
        return _result("invalid", "Reliability probabilities must be within [0, 1].")
    return _result("valid", "All supplied reliability probabilities are within [0, 1].")


__all__ = [
    "CLAIM_STATUSES",
    "CLAIM_TYPES",
    "CLASSIFICATION_RESULTS",
    "CONTRACT_FAMILIES",
    "MATHEMATICAL_VIEW_CONTRACT_VERSION",
    "MathematicalViewContract",
    "MathematicalViewValidationError",
    "classify_math_view_contract",
    "load_math_view_contract",
    "validate_math_view_contract",
]

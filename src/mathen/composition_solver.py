"""Deterministic, bounded exploration of feature compositions.

The solver treats feature records as opaque capability declarations.  It does
not infer relationships from names or descriptions, and its results are
candidate compositions requiring review rather than proofs of compatibility.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations
from typing import Any, Iterable, Mapping


@dataclass(frozen=True, slots=True)
class FeatureRecord:
    """A feature that can provide, require, or conflict with capabilities."""

    id: str
    provides: frozenset[str] = frozenset()
    requires: frozenset[str] = frozenset()
    conflicts: frozenset[str] = frozenset()
    evidence_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class CompositionCandidate:
    """An explainable candidate returned by :func:`solve_compositions`."""

    feature_ids: tuple[str, ...]
    dependency_ids: tuple[str, ...]
    provided_capabilities: tuple[str, ...]
    required_capabilities: tuple[str, ...]
    unresolved_requirements: tuple[str, ...]
    conflicts: tuple[str, ...]
    coverage_score: float
    evidence_score: float
    score: float
    explanation: tuple[str, ...]
    evidence_ids: tuple[str, ...] = ()
    proven: bool = False

    @property
    def selected_ids(self) -> tuple[str, ...]:
        """Stable alias for the selected feature IDs in the result contract."""

        return self.feature_ids


@dataclass(frozen=True, slots=True)
class ReviewedFeatureSpec:
    """Explicit capability semantics for one reviewed-card feature.

    Architecture Cards intentionally describe features but do not assign them
    capability semantics.  A caller must supply this boundary separately; the
    solver never derives capabilities from names, descriptions, categories, or
    other free text.
    """

    system_id: str
    feature_id: str
    provides: frozenset[str] = frozenset()
    requires: frozenset[str] = frozenset()
    conflicts: frozenset[str] = frozenset()


def adapt_reviewed_cards(
    cards: Iterable[Mapping[str, Any]],
    capability_specs: Iterable[ReviewedFeatureSpec | Mapping[str, Any]],
) -> tuple[FeatureRecord, ...]:
    """Adapt reviewed Architecture Cards into solver records.

    ``cards`` must contain validated reviewed-card objects.  Each feature made
    available to the solver must have one explicit capability spec, keyed by
    its ``system_id`` and ``feature_id``.  Feature evidence is copied from the card and
    qualified as ``system_id:evidence_id`` so results remain attributable when
    multiple cards reuse an evidence identifier.  Card feature relations are
    not treated as capability semantics; callers should express any required
    or conflicting capability in ``capability_specs``.

    This function is an adapter boundary, not a card validator.  Use
    :func:`mathen.cards.load_card` or :func:`mathen.cards.validate_card` before
    calling it.  The returned records can be passed to
    :func:`solve_compositions`.
    """

    card_features = _card_features(cards)
    specs = _normalise_specs(capability_specs)
    unknown = sorted(set(specs) - set(card_features))
    if unknown:
        raise ValueError(
            "capability specs reference unknown reviewed features: "
            + ", ".join(f"{system}:{feature}" for system, feature in unknown)
        )

    records = []
    for key in sorted(specs):
        system_id, feature_id = key
        spec = specs[key]
        records.append(
            FeatureRecord(
                id=_qualified_feature_id(system_id, feature_id),
                provides=spec.provides,
                requires=spec.requires,
                conflicts=spec.conflicts,
                evidence_ids=card_features[key],
            )
        )
    return tuple(records)


def solve_reviewed_compositions(
    cards: Iterable[Mapping[str, Any]],
    capability_specs: Iterable[ReviewedFeatureSpec | Mapping[str, Any]],
    required_capabilities: Iterable[str],
    *,
    max_components: int = 4,
    max_depth: int = 3,
    max_results: int = 20,
) -> list[CompositionCandidate]:
    """Solve explicit capability requirements over reviewed-card features.

    This is the minimal library boundary for real reviewed cards.  It adapts
    cards and then invokes the deterministic bounded solver.  Results are
    candidates with ``proven=False``; no execution, compatibility proof, or
    claim promotion is performed.
    """

    return solve_compositions(
        adapt_reviewed_cards(cards, capability_specs),
        required_capabilities,
        max_components=max_components,
        max_depth=max_depth,
        max_results=max_results,
    )


def solve_compositions(
    features: Iterable[FeatureRecord | Mapping[str, Any]],
    required_capabilities: Iterable[str],
    *,
    max_components: int = 4,
    max_depth: int = 3,
    max_results: int = 20,
) -> list[CompositionCandidate]:
    """Return deterministic bounded composition candidates.

    A candidate consists of a non-empty subset of input features.  Requirements
    are satisfied by capabilities provided by that subset, while each selected
    feature's direct requirements are recursively expanded with providers when
    possible.  The depth bound limits recursive dependency expansion and the
    component bound limits the resulting closure.  Candidates with conflicts
    remain explainable results but are ranked after conflict-free candidates;
    unresolved requirements are likewise reported rather than hidden.

    Feature records are read structurally only.  In particular, free-text
    fields are ignored.  All bounds must be positive integers; ``ValueError``
    is raised otherwise.

    If ``n`` records are available and ``S`` is the number of non-empty
    subsets up to ``max_components``, enumeration takes
    ``O(S * max_components * max_depth)`` capability-closure steps and stores
    ``O(S)`` candidates before truncating the returned list.  The bounds are
    therefore part of the safety and reproducibility contract.
    """

    _validate_bounds(max_components, max_depth, max_results)
    records = _normalise_features(features)
    requirements = frozenset(_normalise_capabilities(required_capabilities))
    providers = _providers_by_capability(records)
    candidates: dict[tuple[str, ...], CompositionCandidate] = {}

    for size in range(1, min(max_components, len(records)) + 1):
        for selected in combinations(records, size):
            candidate = _build_candidate(
                selected,
                requirements,
                providers,
                max_components=max_components,
                max_depth=max_depth,
            )
            candidates[candidate.feature_ids] = candidate

    ordered = sorted(
        candidates.values(),
        key=lambda candidate: (
            candidate.unresolved_requirements != (),
            candidate.conflicts != (),
            -candidate.score,
            -candidate.coverage_score,
            -candidate.evidence_score,
            len(candidate.feature_ids),
            candidate.feature_ids,
        ),
    )
    return ordered[:max_results]


def _validate_bounds(max_components: int, max_depth: int, max_results: int) -> None:
    for name, value in (
        ("max_components", max_components),
        ("max_depth", max_depth),
        ("max_results", max_results),
    ):
        if isinstance(value, bool) or not isinstance(value, int) or value < 1:
            raise ValueError(f"{name} must be a positive integer")


def _normalise_features(
    features: Iterable[FeatureRecord | Mapping[str, Any]],
) -> tuple[FeatureRecord, ...]:
    records: list[FeatureRecord] = []
    seen: set[str] = set()
    for item in features:
        if isinstance(item, FeatureRecord):
            record = item
        elif isinstance(item, Mapping):
            record = FeatureRecord(
                id=_required_text(item, "id"),
                provides=_text_set(item.get("provides", ()), "provides"),
                requires=_text_set(item.get("requires", ()), "requires"),
                conflicts=_text_set(item.get("conflicts", ()), "conflicts"),
                evidence_ids=_text_tuple(item.get("evidence_ids", ()), "evidence_ids"),
            )
        else:
            raise TypeError("features must contain FeatureRecord or mapping values")
        if not record.id:
            raise ValueError("feature id must not be empty")
        if record.id in seen:
            raise ValueError(f"duplicate feature id: {record.id}")
        seen.add(record.id)
        records.append(record)
    return tuple(sorted(records, key=lambda record: record.id))


def _required_text(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{field} must be a non-empty string")
    return value


def _normalise_capabilities(value: Iterable[str]) -> tuple[str, ...]:
    return _text_tuple(value, "required_capabilities")


def _text_set(value: Any, field: str) -> frozenset[str]:
    return frozenset(_text_tuple(value, field))


def _text_tuple(value: Any, field: str) -> tuple[str, ...]:
    if isinstance(value, (str, bytes)):
        raise ValueError(f"{field} must be an iterable of strings")
    try:
        values = tuple(value)
    except TypeError as error:
        raise ValueError(f"{field} must be an iterable of strings") from error
    if any(not isinstance(item, str) or not item for item in values):
        raise ValueError(f"{field} must contain non-empty strings")
    return tuple(sorted(set(values)))


def _providers_by_capability(
    records: tuple[FeatureRecord, ...],
) -> dict[str, tuple[FeatureRecord, ...]]:
    providers: dict[str, list[FeatureRecord]] = {}
    for record in records:
        for capability in record.provides:
            providers.setdefault(capability, []).append(record)
    return {capability: tuple(values) for capability, values in providers.items()}


def _build_candidate(
    selected: tuple[FeatureRecord, ...],
    required: frozenset[str],
    providers: dict[str, tuple[FeatureRecord, ...]],
    *,
    max_components: int,
    max_depth: int,
) -> CompositionCandidate:
    chosen: dict[str, FeatureRecord] = {record.id: record for record in selected}
    unresolved: set[str] = set()
    pending = sorted(
        (capability, 0)
        for capability in {
            requirement for record in selected for requirement in record.requires
        }
    )
    visited_requirements: set[str] = set()
    while pending:
        pending.sort(key=lambda item: (item[1], item[0]))
        capability, depth = pending.pop(0)
        if capability in visited_requirements:
            continue
        visited_requirements.add(capability)
        if any(capability in record.provides for record in chosen.values()):
            continue
        if depth > max_depth or len(chosen) >= max_components:
            unresolved.add(capability)
            continue
        options = providers.get(capability, ())
        provider = next((record for record in options if record.id not in chosen), None)
        if provider is None:
            unresolved.add(capability)
            continue
        chosen[provider.id] = provider
        pending.extend((requirement, depth + 1) for requirement in provider.requires)

    all_records = tuple(sorted(chosen.values(), key=lambda record: record.id))
    provided = frozenset(
        capability for record in all_records for capability in record.provides
    )
    required_with_dependencies = (
        frozenset(
            capability for record in all_records for capability in record.requires
        )
        | required
    )
    unresolved.update(required - provided)
    conflict_ids = _find_conflicts(all_records)
    dependencies = tuple(
        record.id
        for record in all_records
        if record.id not in {item.id for item in selected}
    )
    coverage = len(required & provided) / len(required) if required else 1.0
    evidence_count = sum(len(record.evidence_ids) for record in all_records)
    evidence_score = evidence_count / len(all_records) if all_records else 0.0
    score = (
        coverage * 100.0
        + evidence_score
        - len(unresolved) * 10.0
        - len(conflict_ids) * 20.0
    )
    explanation = _explanation(
        selected=tuple(record.id for record in selected),
        dependencies=dependencies,
        provided=provided,
        required=required_with_dependencies,
        unresolved=unresolved,
        conflicts=conflict_ids,
    )
    return CompositionCandidate(
        feature_ids=tuple(record.id for record in selected),
        dependency_ids=dependencies,
        provided_capabilities=tuple(sorted(provided)),
        required_capabilities=tuple(sorted(required_with_dependencies)),
        unresolved_requirements=tuple(sorted(unresolved)),
        conflicts=conflict_ids,
        coverage_score=coverage,
        evidence_score=evidence_score,
        score=score,
        explanation=explanation,
        evidence_ids=tuple(
            sorted(
                {
                    evidence_id
                    for record in all_records
                    for evidence_id in record.evidence_ids
                }
            )
        ),
    )


def _find_conflicts(records: tuple[FeatureRecord, ...]) -> tuple[str, ...]:
    conflicts: set[str] = set()
    ids = {record.id for record in records}
    provided = {capability for record in records for capability in record.provides}
    for record in records:
        for conflict in record.conflicts:
            if conflict in ids or conflict in provided:
                conflicts.add(f"{record.id}:{conflict}")
    return tuple(sorted(conflicts))


def _explanation(
    *,
    selected: tuple[str, ...],
    dependencies: tuple[str, ...],
    provided: frozenset[str],
    required: frozenset[str],
    unresolved: set[str],
    conflicts: tuple[str, ...],
) -> tuple[str, ...]:
    statements = [f"selected features: {', '.join(selected)}"]
    if dependencies:
        statements.append(f"dependency closure added: {', '.join(dependencies)}")
    statements.append(
        "capability coverage: "
        f"{len(required - unresolved)} of {len(required)} requirements"
    )
    if unresolved:
        statements.append(f"unresolved requirements: {', '.join(sorted(unresolved))}")
    if conflicts:
        statements.append(f"detected conflicts: {', '.join(conflicts)}")
    statements.append("candidate requires review; it is not a proof of compatibility")
    return tuple(statements)


def _card_features(
    cards: Iterable[Mapping[str, Any]],
) -> dict[tuple[str, str], tuple[str, ...]]:
    features: dict[tuple[str, str], tuple[str, ...]] = {}
    for card in cards:
        if not isinstance(card, Mapping):
            raise TypeError("cards must contain mapping values")
        system_id = card.get("id")
        if not isinstance(system_id, str) or not system_id:
            raise ValueError("reviewed card id must be a non-empty string")
        raw_features = card.get("features")
        if not isinstance(raw_features, list):
            raise ValueError(f"reviewed card {system_id} features must be a list")
        for feature in raw_features:
            if not isinstance(feature, Mapping):
                raise ValueError(f"reviewed card {system_id} features must be objects")
            feature_id = feature.get("id")
            if not isinstance(feature_id, str) or not feature_id:
                raise ValueError(
                    f"reviewed card {system_id} feature id must be non-empty"
                )
            evidence_ids = feature.get("evidence_ids")
            if evidence_ids is None:
                raise ValueError(
                    f"reviewed feature {system_id}:{feature_id} needs evidence_ids"
                )
            evidence = _text_tuple(evidence_ids, "evidence_ids")
            key = (system_id, feature_id)
            if key in features:
                raise ValueError(
                    f"duplicate reviewed feature: {system_id}:{feature_id}"
                )
            features[key] = tuple(
                f"{system_id}:{evidence_id}" for evidence_id in evidence
            )
    return features


def _normalise_specs(
    specs: Iterable[ReviewedFeatureSpec | Mapping[str, Any]],
) -> dict[tuple[str, str], ReviewedFeatureSpec]:
    normalised: dict[tuple[str, str], ReviewedFeatureSpec] = {}
    for item in specs:
        if isinstance(item, ReviewedFeatureSpec):
            spec = item
        elif isinstance(item, Mapping):
            spec = ReviewedFeatureSpec(
                system_id=_required_text(item.get("system_id"), "system_id"),
                feature_id=_required_text(item.get("feature_id"), "feature_id"),
                provides=_text_set(item.get("provides", ()), "provides"),
                requires=_text_set(item.get("requires", ()), "requires"),
                conflicts=_text_set(item.get("conflicts", ()), "conflicts"),
            )
        else:
            raise TypeError(
                "capability specs must contain ReviewedFeatureSpec or mapping values"
            )
        if not spec.system_id or not spec.feature_id:
            raise ValueError("capability spec identifiers must not be empty")
        key = (spec.system_id, spec.feature_id)
        if key in normalised:
            raise ValueError(
                f"duplicate capability spec: {spec.system_id}:{spec.feature_id}"
            )
        normalised[key] = spec
    return normalised


def _qualified_feature_id(system_id: str, feature_id: str) -> str:
    return f"{system_id}:{feature_id}"

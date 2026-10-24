"""Controlled vocabulary for reusable Architecture Card features.

The card format historically stores a free-form ``category`` on each feature.
This module provides a small, forward-compatible vocabulary for new producers
without requiring a migration of existing cards.  Legacy categories are
aliases: they are normalized to a deterministic four-field taxonomy entry and
remain valid input to :func:`normalize_feature_taxonomy`.
"""

from __future__ import annotations

import re
from types import MappingProxyType
from typing import Any, Mapping


class TaxonomyValidationError(ValueError):
    """Raised when a feature taxonomy value is invalid."""


# These are intentionally small semantic dimensions.  ``pattern_id`` is not
# enumerated: review may propose a new pattern before it is added to a future
# registry.  The dimensions, however, are controlled and typo-resistant.
FEATURE_KINDS = frozenset(
    {
        "boundary",
        "control",
        "interface",
        "mechanism",
        "model",
        "property",
        "state",
        "workflow",
    }
)
FEATURE_DOMAINS = frozenset(
    {
        "build",
        "communication",
        "coordination",
        "data",
        "deployment",
        "execution",
        "integration",
        "language",
        "media",
        "observability",
        "reliability",
        "resource",
        "security",
        "storage",
        "ui",
    }
)
FEATURE_LAYERS = frozenset(
    {
        "application",
        "control",
        "data",
        "interface",
        "platform",
        "runtime",
        "storage",
        "system",
    }
)

_FIELD_ALIASES = {
    "kind": {
        "architecture": "model",
        "component": "mechanism",
        "constraint": "property",
        "lifecycle": "state",
        "process": "mechanism",
        "pattern": "mechanism",
    },
    "domain": {
        "compute": "execution",
        "network": "communication",
        "networking": "communication",
        "ops": "deployment",
        "persistence": "storage",
        "presentation": "ui",
        "resource-control": "resource",
        "tooling": "build",
    },
    "layer": {
        "api": "interface",
        "application-layer": "application",
        "backend": "runtime",
        "control-plane": "control",
        "kernel": "system",
        "library": "platform",
        "service": "runtime",
    },
}

_VOCABULARIES = {
    "kind": FEATURE_KINDS,
    "domain": FEATURE_DOMAINS,
    "layer": FEATURE_LAYERS,
}

_IDENTIFIER = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
_TOKEN_SEPARATOR = re.compile(r"[\s_]+")
_LEGACY_SEPARATOR = re.compile(r"[^a-z0-9]+")

# The values present in reviewed and generated cards at the time this
# vocabulary was introduced.  Keeping the set here makes the compatibility
# boundary explicit and independent of the data directory.
LEGACY_CATEGORY_VALUES = (
    "I/O-model",
    "activation-model",
    "adapter-boundary",
    "api-model",
    "application-model",
    "application-state-model",
    "asynchronous-io-model",
    "architecture-evidence",
    "architecture-model",
    "artifact-model",
    "audio-model",
    "authentication-model",
    "authorization-model",
    "automation-model",
    "availability-and-loading",
    "availability-model",
    "backpressure-model",
    "backup-storage",
    "boot-recovery-model",
    "boundary-validation",
    "build-and-analysis-model",
    "build-and-integration-model",
    "build-configuration",
    "build-graph",
    "build-lifecycle",
    "build-model",
    "change-management",
    "code-generation-model",
    "code-reuse",
    "codec-execution-model",
    "collection-model",
    "command-interface",
    "commit-model",
    "communication-model",
    "compatibility-boundary",
    "compatibility-model",
    "context-model",
    "compilation-model",
    "compile-time-model",
    "compiler-pipeline",
    "compiler-platform",
    "compiler-toolchain",
    "component-model",
    "composition-model",
    "compute-model",
    "concurrency-control",
    "concurrency-model",
    "configuration-model",
    "connection-model",
    "consistency-model",
    "consumption-model",
    "content-model",
    "control-and-data-model",
    "control-loop",
    "control-model",
    "control-plane",
    "control-plane-model",
    "coordination-model",
    "correlation-model",
    "credential-lifecycle",
    "data-contract",
    "data-model",
    "data-path",
    "data-plane-model",
    "dataflow-model",
    "declarative-control",
    "delivery-model",
    "dependency-model",
    "deployment-interface",
    "deployment-boundary",
    "deployment-model",
    "development-model",
    "differentiation-model",
    "discovery-model",
    "distributed-execution",
    "distributed-interface",
    "distribution-model",
    "durability-model",
    "embedding-and-interoperability",
    "embedding-interface",
    "embedding-model",
    "evaluation-model",
    "event-model",
    "evolution-model",
    "execution-boundary",
    "execution-model",
    "extension-model",
    "failure-model",
    "failure-recovery-model",
    "fault-isolation",
    "fault-tolerance",
    "fault-tolerance-model",
    "graph-model",
    "host-integration",
    "http-execution",
    "incremental-build-model",
    "incremental-computation",
    "incrementality-model",
    "inference-model",
    "ingress-model",
    "input-and-control",
    "input-model",
    "input-output-model",
    "input-render-model",
    "integration-model",
    "interaction-model",
    "interface-model",
    "intermediate-representation",
    "interoperability-model",
    "ipc-model",
    "isolation-boundary",
    "isolation-model",
    "kernel-model",
    "kernel-resource-model",
    "language-model",
    "language-semantics",
    "layout-model",
    "library-architecture",
    "library-model",
    "lifecycle-model",
    "lifecycle-state",
    "linkage-model",
    "linking-model",
    "liveness-model",
    "liveness-observation",
    "log-structured-persistence",
    "maintenance-model",
    "media-container-model",
    "media-graph",
    "media-transformation-model",
    "memory-and-extension-model",
    "memory-management",
    "memory-model",
    "memory-safety-model",
    "message-model",
    "messaging-model",
    "microkernel-model",
    "model-api",
    "model-definition",
    "modular-architecture",
    "module-loading",
    "module-model",
    "native-integration",
    "network-model",
    "networking-model",
    "object-model",
    "observability-model",
    "observation-model",
    "operational-state",
    "optimization-model",
    "ordering-model",
    "output-model",
    "parse-model",
    "parser-model",
    "persistence-execution",
    "persistence-model",
    "platform-abstraction",
    "platform-architecture",
    "platform-capability",
    "platform-integration",
    "platform-model",
    "portability-model",
    "presentation-model",
    "process-boundary",
    "process-interface",
    "process-model",
    "program-model",
    "programming-model",
    "protocol-abstraction",
    "protocol-and-backend",
    "protocol-and-compositor",
    "protocol-boundary",
    "protocol-composition",
    "protocol-contract",
    "protocol-model",
    "provenance-model",
    "provider-model",
    "query-execution",
    "query-model",
    "queue-model",
    "reactivity-model",
    "recovery-model",
    "reliability-model",
    "renderable-model",
    "rendering-lifecycle",
    "rendering-model",
    "replication-model",
    "repository-model",
    "release-model",
    "request-execution",
    "request-lifecycle",
    "request-path",
    "resource-abstraction",
    "resource-and-state-model",
    "resource-control",
    "resource-interface",
    "resource-lifecycle",
    "resource-mediation",
    "resource-model",
    "resource-placement",
    "restore-model",
    "routing-model",
    "runtime-boundary",
    "runtime-composition",
    "runtime-interface",
    "runtime-model",
    "runtime-state",
    "runtime-state-model",
    "scene-model",
    "scheduler-model",
    "scheduling-model",
    "schema-model",
    "security-and-operations",
    "security-boundary",
    "security-model",
    "security-observability",
    "security-protocol",
    "selection-model",
    "serialization-model",
    "serving-model",
    "session-model",
    "state-and-failure-model",
    "state-and-memory-model",
    "state-management",
    "state-model",
    "state-storage",
    "state-exchange-model",
    "static-analysis-model",
    "static-safety-model",
    "storage-architecture",
    "storage-maintenance",
    "storage-model",
    "synchronization-model",
    "system-interface",
    "tenant-model",
    "terminal-model",
    "test-execution-model",
    "time-model",
    "toolchain-model",
    "tooling-model",
    "topology-model",
    "transaction-model",
    "transformation-model",
    "transport-model",
    "transport-security",
    "traversal-model",
    "type-negotiation",
    "ui-model",
    "ui-representation",
    "upstream-model",
    "validation-model",
    "verification-model",
    "version-control-boundary",
    "virtual-machine-model",
    "virtualization-boundary",
    "workflow-model",
    "workflow-state-model",
)


def normalize_identifier(value: Any, field: str = "identifier") -> str:
    """Normalize a user-facing identifier to a lowercase hyphenated slug."""

    if not isinstance(value, str):
        raise TaxonomyValidationError(f"{field} must be a string")
    normalized = _TOKEN_SEPARATOR.sub("-", value.strip().casefold())
    normalized = re.sub(r"-+", "-", normalized).strip("-")
    if not normalized or not _IDENTIFIER.fullmatch(normalized):
        raise TaxonomyValidationError(
            f"{field} must be a lowercase hyphenated identifier: {value!r}"
        )
    return normalized


def normalize_pattern_id(value: Any) -> str:
    """Normalize a pattern ID without requiring it to be pre-registered.

    Proposed IDs are intentionally accepted.  Registration and review can add
    a pattern later without invalidating a draft that references it.
    """

    return normalize_identifier(value, "pattern_id")


def _normalize_vocab_value(field: str, value: Any) -> str:
    normalized = normalize_identifier(value, field)
    canonical = _FIELD_ALIASES[field].get(normalized, normalized)
    if canonical not in _VOCABULARIES[field]:
        allowed = ", ".join(sorted(_VOCABULARIES[field]))
        raise TaxonomyValidationError(
            f"invalid {field} {value!r}; expected one of: {allowed}"
        )
    return canonical


def _legacy_dimension(category: str, dimension: str) -> str:
    tokens = set(category.split("-"))
    if dimension == "kind":
        if "boundary" in tokens:
            return "boundary"
        if "interface" in tokens or "protocol" in tokens:
            return "interface"
        if tokens & {"control", "loop", "scheduler", "scheduling", "coordination"}:
            return "control"
        if tokens & {"state", "lifecycle", "maintenance", "recovery"}:
            return "state"
        if "workflow" in tokens:
            return "workflow"
        if tokens & {"validation", "safety", "consistency", "reliability", "fault"}:
            return "property"
        return "model" if "model" in tokens or "architecture" in tokens else "mechanism"

    if dimension == "domain":
        groups = (
            (
                {"storage", "persistence", "durability", "backup", "restore", "log"},
                "storage",
            ),
            (
                {"data", "query", "schema", "collection", "serialization", "content"},
                "data",
            ),
            (
                {
                    "execution",
                    "runtime",
                    "process",
                    "compute",
                    "virtual",
                    "compiler",
                    "compilation",
                    "code",
                    "program",
                },
                "execution",
            ),
            (
                {
                    "network",
                    "networking",
                    "protocol",
                    "transport",
                    "message",
                    "messaging",
                    "communication",
                    "http",
                    "ipc",
                    "connection",
                    "routing",
                    "request",
                },
                "communication",
            ),
            (
                {
                    "security",
                    "authentication",
                    "authorization",
                    "credential",
                    "isolation",
                    "safety",
                },
                "security",
            ),
            (
                {
                    "build",
                    "compile",
                    "linking",
                    "linkage",
                    "toolchain",
                    "tooling",
                    "test",
                    "development",
                },
                "build",
            ),
            ({"media", "audio", "codec", "rendering", "renderable", "scene"}, "media"),
            ({"resource", "memory", "kernel"}, "resource"),
            (
                {
                    "failure",
                    "recovery",
                    "fault",
                    "availability",
                    "liveness",
                    "reliability",
                },
                "reliability",
            ),
            (
                {
                    "control",
                    "coordination",
                    "orchestration",
                    "scheduler",
                    "scheduling",
                    "queue",
                    "workflow",
                },
                "coordination",
            ),
            ({"ui", "input", "output", "layout", "presentation", "terminal"}, "ui"),
            ({"language", "parser", "parse", "type", "object", "module"}, "language"),
            (
                {
                    "deployment",
                    "platform",
                    "library",
                    "integration",
                    "extension",
                    "embedding",
                    "provider",
                    "repository",
                },
                "integration",
            ),
        )
        for group, domain in groups:
            if tokens & group:
                return domain
        return "integration"

    groups = (
        (
            {"storage", "persistence", "durability", "backup", "restore", "log"},
            "storage",
        ),
        ({"data", "query", "schema", "collection", "serialization", "content"}, "data"),
        (
            {
                "control",
                "coordination",
                "orchestration",
                "scheduler",
                "scheduling",
                "queue",
                "workflow",
            },
            "control",
        ),
        (
            {
                "interface",
                "protocol",
                "transport",
                "network",
                "networking",
                "api",
                "connection",
                "request",
                "message",
                "http",
                "ipc",
            },
            "interface",
        ),
        (
            {
                "execution",
                "runtime",
                "process",
                "compute",
                "compiler",
                "memory",
                "virtual",
                "program",
            },
            "runtime",
        ),
        (
            {
                "ui",
                "input",
                "output",
                "layout",
                "presentation",
                "rendering",
                "terminal",
            },
            "application",
        ),
        (
            {"resource", "security", "platform", "deployment", "kernel", "library"},
            "platform",
        ),
    )
    for group, layer in groups:
        if tokens & group:
            return layer
    return "system"


# Each current category has an explicit compatibility entry.  New pattern IDs
# need not be added here before proposal/review; this table is only the legacy
# migration boundary.
def _legacy_taxonomy(category: str) -> dict[str, str]:
    return {
        "kind": _legacy_dimension(category, "kind"),
        "domain": _legacy_dimension(category, "domain"),
        "layer": _legacy_dimension(category, "layer"),
        "pattern_id": _LEGACY_SEPARATOR.sub("-", category).strip("-"),
    }


CATEGORY_ALIASES = MappingProxyType(
    {
        category: MappingProxyType(
            _legacy_taxonomy(_LEGACY_SEPARATOR.sub("-", category.casefold()).strip("-"))
        )
        for category in LEGACY_CATEGORY_VALUES
    }
)


def category_alias(category: Any) -> dict[str, str]:
    """Return the deterministic taxonomy entry represented by a legacy category."""

    if not isinstance(category, str):
        raise TaxonomyValidationError("category must be a string")
    normalized = _LEGACY_SEPARATOR.sub("-", category.strip().casefold()).strip("-")
    if not normalized or not _IDENTIFIER.fullmatch(normalized):
        raise TaxonomyValidationError(
            f"category must contain an identifier: {category!r}"
        )
    alias = CATEGORY_ALIASES.get(category)
    if alias is None:
        alias = _legacy_taxonomy(normalized)
    return dict(alias)


def normalize_feature_taxonomy(
    value: Mapping[str, Any], *, allow_legacy_category: bool = True
) -> dict[str, str]:
    """Normalize and validate a feature taxonomy mapping.

    New producers should provide ``kind``, ``domain``, ``layer``, and
    ``pattern_id``.  A feature containing only the historical ``category`` is
    accepted by default and translated through :func:`category_alias`.
    """

    if not isinstance(value, Mapping):
        raise TaxonomyValidationError("feature taxonomy must be an object")
    if not allow_legacy_category and "category" in value:
        raise TaxonomyValidationError("legacy category is not allowed")
    has_dimensions = any(field in value for field in ("kind", "domain", "layer"))
    category = value.get("category")
    if not has_dimensions and category is not None:
        if not allow_legacy_category:
            raise TaxonomyValidationError("legacy category is not allowed")
        result = category_alias(category)
        if "pattern_id" in value:
            result["pattern_id"] = normalize_pattern_id(value["pattern_id"])
        return result

    result: dict[str, str] = {}
    for field in ("kind", "domain", "layer"):
        if field not in value:
            raise TaxonomyValidationError(f"missing taxonomy field: {field}")
        result[field] = _normalize_vocab_value(field, value[field])
    if "pattern_id" in value:
        result["pattern_id"] = normalize_pattern_id(value["pattern_id"])
    elif category is not None:
        result["pattern_id"] = category_alias(category)["pattern_id"]
    return result


def validate_feature_taxonomy(
    value: Mapping[str, Any],
    *,
    allow_legacy_category: bool = True,
    require_pattern_id: bool = False,
) -> None:
    """Raise :class:`TaxonomyValidationError` unless ``value`` is valid."""

    normalized = normalize_feature_taxonomy(
        value, allow_legacy_category=allow_legacy_category
    )
    if require_pattern_id and "pattern_id" not in normalized:
        raise TaxonomyValidationError("missing taxonomy field: pattern_id")


def is_valid_feature_taxonomy(
    value: Mapping[str, Any], *, allow_legacy_category: bool = True
) -> bool:
    """Return whether a taxonomy mapping can be normalized."""

    try:
        validate_feature_taxonomy(value, allow_legacy_category=allow_legacy_category)
    except (TaxonomyValidationError, TypeError):
        return False
    return True


TAXONOMY_CONFIG = MappingProxyType(
    {
        "kinds": tuple(sorted(FEATURE_KINDS)),
        "domains": tuple(sorted(FEATURE_DOMAINS)),
        "layers": tuple(sorted(FEATURE_LAYERS)),
        "pattern_id": "proposed IDs are accepted when they are valid slugs",
    }
)

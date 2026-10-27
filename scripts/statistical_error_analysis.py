#!/usr/bin/env python3
"""Build deterministic, research-only statistical error analysis for MTH-0177.

The module deliberately separates protocol capacity from observations.  Empty
observation sets produce ``null`` metrics and no interval.  It has no provider,
model, reviewer, or network integration; callers supply normalized observations
from a future run.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "benchmark" / "mth-0177-statistical-analysis.json"
MTH_0174_ARTIFACT = ROOT / "data" / "benchmark" / "mth-0174-cross-system.json"
MTH_0174_COMMIT = "9dbed68"
MTH_0174_DIGEST = (
    "sha256:0079440b630a7319b73d0934fd01610b2773854047ab62787a8b3560bfb0b2e1"
)
MTH_0172_DIGEST = (
    "sha256:77c06204f5c8286dd07d237b8ef4ffe6351f2a2652b48b0eeb1293528ea3b1c8"
)

ERROR_TAXONOMY = (
    "false-link",
    "scope-loss",
    "claim-discipline",
    "abstention",
    "counterexample-miss",
    "reviewer-disagreement",
)
SMALL_SAMPLE_THRESHOLD = 5


def canonical_digest(value: Any) -> str:
    """Return a stable digest for JSON-compatible data."""

    payload = json.dumps(
        value, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )
    return "sha256:" + hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _metric(
    name: str,
    numerator: int,
    denominator: int,
    *,
    reason: str,
    interval: Mapping[str, Any] | None = None,
    warnings: Sequence[str] = (),
) -> dict[str, Any]:
    """Create a bounded rate with explicit null and warning semantics."""

    if denominator < 0 or numerator < 0 or numerator > denominator:
        raise ValueError("metric counts must satisfy 0 <= numerator <= denominator")
    return {
        "name": name,
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
        "status": "measured" if denominator else "not-evaluated",
        "reason": reason if denominator else f"No observations: {reason}",
        "interval": interval,
        "warnings": list(warnings),
    }


def exact_binomial_interval(
    successes: int, trials: int, *, confidence: float = 0.95
) -> dict[str, Any] | None:
    """Return a Clopper-Pearson interval without external statistical packages."""

    if trials == 0:
        return None
    if not 0 <= successes <= trials:
        raise ValueError("successes must satisfy 0 <= successes <= trials")
    if not 0 < confidence < 1:
        raise ValueError("confidence must be between zero and one")
    alpha = 1.0 - confidence
    # scipy is intentionally not a dependency.  The inverse beta CDF is
    # implemented by deterministic bisection over the regularized beta CDF.
    lower = (
        0.0
        if successes == 0
        else _beta_ppf(alpha / 2, successes, trials - successes + 1)
    )
    upper = (
        1.0
        if successes == trials
        else _beta_ppf(1 - alpha / 2, successes + 1, trials - successes)
    )
    return {
        "method": "clopper-pearson-exact",
        "confidence": confidence,
        "lower": lower,
        "upper": upper,
    }


def bootstrap_interval(
    values: Sequence[float],
    *,
    confidence: float = 0.95,
    resamples: int = 2000,
    seed: int = 0,
) -> dict[str, Any] | None:
    """Return a deterministic percentile bootstrap interval for observed values."""

    if not values:
        return None
    if not 0 < confidence < 1 or resamples < 1:
        raise ValueError("confidence must be in (0, 1) and resamples must be positive")
    if any(not math.isfinite(value) for value in values):
        raise ValueError("bootstrap values must be finite")
    # A local deterministic PRNG avoids global state and external dependencies.
    state = seed & ((1 << 64) - 1)
    samples: list[float] = []
    for _ in range(resamples):
        total = 0.0
        for _ in values:
            state = (6364136223846793005 * state + 1442695040888963407) & (
                (1 << 64) - 1
            )
            total += values[state % len(values)]
        samples.append(total / len(values))
    samples.sort()
    tail = (1.0 - confidence) / 2
    return {
        "method": "percentile-bootstrap",
        "confidence": confidence,
        "resamples": resamples,
        "seed": seed,
        "lower": _quantile(samples, tail),
        "upper": _quantile(samples, 1 - tail),
    }


def aggregate_rate(
    observations: Iterable[Mapping[str, Any]], *, metric: str, confidence: float = 0.95
) -> dict[str, Any]:
    """Aggregate binary observations using exact intervals when observations exist."""

    rows = list(observations)
    successes = sum(bool(row.get(metric)) for row in rows)
    warnings = _small_sample_warnings(len(rows))
    return _metric(
        metric,
        successes,
        len(rows),
        reason=f"Binary observations for {metric}.",
        interval=exact_binomial_interval(successes, len(rows), confidence=confidence),
        warnings=warnings,
    )


def _small_sample_warnings(denominator: int) -> list[str]:
    return (
        [f"small sample: denominator {denominator} is below {SMALL_SAMPLE_THRESHOLD}"]
        if 0 < denominator < SMALL_SAMPLE_THRESHOLD
        else []
    )


def error_analysis(observations: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Compute separate taxonomy rates and deterministic slice aggregations.

    Each row represents one evaluated candidate/task observation and may carry
    ``domain``, ``task_id``, and boolean taxonomy fields.  Reviewer disagreement
    is counted only when explicit reviewer labels are present.
    """

    rows = list(observations)
    metrics = {category: _error_metric(rows, category) for category in ERROR_TAXONOMY}
    return {
        "observed_count": len(rows),
        "metrics": metrics,
        "by_domain": _slice_metrics(rows, "domain"),
        "by_task": _slice_metrics(rows, "task_id"),
        "warnings": _small_sample_warnings(len(rows)),
    }


def repeated_run_aggregation(
    runs: Sequence[Mapping[str, Any]], *, confidence: float = 0.95
) -> dict[str, Any]:
    """Aggregate repeated run-level binary metrics without fabricating runs."""

    result: dict[str, Any] = {"run_count": len(runs), "metrics": {}}
    for metric_name in ERROR_TAXONOMY:
        values = [
            run["metrics"][metric_name]["value"]
            for run in runs
            if run.get("metrics", {}).get(metric_name, {}).get("value") is not None
        ]
        result["metrics"][metric_name] = {
            "run_denominator": len(values),
            "mean": sum(values) / len(values) if values else None,
            "interval": bootstrap_interval(values, confidence=confidence)
            if values
            else None,
            "status": "measured" if values else "not-evaluated",
            "warnings": _small_sample_warnings(len(values)),
        }
    return result


def _error_metric(rows: Sequence[Mapping[str, Any]], category: str) -> dict[str, Any]:
    eligible = [
        row for row in rows if category in row.get("evaluated_errors", ERROR_TAXONOMY)
    ]
    errors = sum(category in row.get("errors", []) for row in eligible)
    return _metric(
        category,
        errors,
        len(eligible),
        reason=f"{category} observations among rows that evaluated this dimension.",
        interval=exact_binomial_interval(errors, len(eligible)),
        warnings=_small_sample_warnings(len(eligible)),
    )


def _slice_metrics(
    rows: Sequence[Mapping[str, Any]], field: str
) -> list[dict[str, Any]]:
    groups: defaultdict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for row in rows:
        value = row.get(field)
        if value is not None:
            groups[str(value)].append(row)
    return [
        {
            "slice": key,
            "metrics": {
                category: _error_metric(group, category) for category in ERROR_TAXONOMY
            },
            "warnings": _small_sample_warnings(len(group)),
        }
        for key, group in sorted(groups.items())
    ]


def _quantile(values: Sequence[float], probability: float) -> float:
    position = (len(values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return values[lower]
    weight = position - lower
    return values[lower] * (1 - weight) + values[upper] * weight


def _beta_ppf(probability: float, a: int, b: int) -> float:
    low, high = 0.0, 1.0
    for _ in range(80):
        mid = (low + high) / 2
        if _regularized_beta(mid, a, b) < probability:
            low = mid
        else:
            high = mid
    return (low + high) / 2


def _regularized_beta(x: float, a: int, b: int) -> float:
    if x <= 0:
        return 0.0
    if x >= 1:
        return 1.0
    total = 0.0
    for k in range(a, a + b):
        total += math.comb(a + b - 1, k) * x**k * (1 - x) ** (a + b - 1 - k)
    return total


def _capacity_from_source(path: Path) -> dict[str, Any]:
    source_artifact = path.relative_to(ROOT).as_posix()
    if not path.exists():
        return {
            "status": "protocol-capacity",
            "source_artifact": source_artifact,
            "source_commit": MTH_0174_COMMIT,
            "source_digest": MTH_0174_DIGEST,
            "domain_slices": _known_mth_0174_slices(),
            "task_count": 12,
            "reason": (
                "Authored MTH-0174 capacity is copied from its immutable protocol "
                "digest; no observations are included."
            ),
        }
    source = json.loads(path.read_text(encoding="utf-8"))
    return {
        "status": "protocol-capacity",
        "source_artifact": source_artifact,
        "source_commit": MTH_0174_COMMIT,
        "source_digest": "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest(),
        "domain_slices": [
            {
                "domain": item["domain"],
                "task_ids": sorted(item["task_ids"]),
                "system_ids": sorted(item["system_ids"]),
            }
            for item in sorted(source["domain_slices"], key=lambda item: item["domain"])
        ],
        "task_count": len(source["task_cards"]),
        "reason": (
            "Authored tasks define capacity only; no empirical observations are "
            "included."
        ),
    }


def _known_mth_0174_slices() -> list[dict[str, Any]]:
    """Keep protocol capacity visible when integration ancestry is not checked out."""

    return [
        {
            "domain": "isolation",
            "system_ids": ["firecracker", "git"],
            "task_ids": [
                "task-10-boundary-isolation",
                "task-11-boundary-isolation",
                "task-12-boundary-isolation",
            ],
        },
        {
            "domain": "orchestration",
            "system_ids": ["airflow", "carryctx", "kubernetes"],
            "task_ids": [
                "task-07-reconciliation",
                "task-08-reconciliation",
                "task-09-reconciliation",
            ],
        },
        {
            "domain": "storage",
            "system_ids": ["duckdb", "postgresql", "sqlite"],
            "task_ids": [
                "task-01-storage-mechanism",
                "task-02-storage-mechanism",
                "task-03-storage-mechanism",
            ],
        },
        {
            "domain": "streaming",
            "system_ids": ["kafka", "temporal"],
            "task_ids": [
                "task-04-stream-history",
                "task-05-stream-history",
                "task-06-stream-history",
            ],
        },
    ]


def build_artifact() -> dict[str, Any]:
    """Build the checked-in artifact with no fabricated observations."""

    capacity = _capacity_from_source(MTH_0174_ARTIFACT)
    empty = error_analysis([])
    empty["by_domain"] = [
        _empty_slice(item["domain"]) for item in capacity["domain_slices"]
    ]
    empty["by_task"] = [
        _empty_slice(task_id)
        for item in capacity["domain_slices"]
        for task_id in item["task_ids"]
    ]
    return {
        "schema_version": "1.0",
        "analysis_id": "mth-0177-statistical-analysis",
        "research_only": True,
        "purpose": (
            "Deterministic aggregation and error-analysis hooks for MTH-0174 and "
            "MTH-0172."
        ),
        "sources": {
            "mth_0174": {
                "artifact": "data/benchmark/mth-0174-cross-system.json",
                "commit": MTH_0174_COMMIT,
                "digest": MTH_0174_DIGEST,
            },
            "mth_0172": {
                "artifact": "data/benchmark/mth-0172-candidate-quality.json",
                "digest": MTH_0172_DIGEST,
            },
        },
        "protocol_capacity": capacity,
        "observations": {
            "runs": [],
            "reviewer_labels": [],
            "llm_outputs": [],
            "rows": [],
        },
        "aggregation": {
            "overall": empty,
            "repeated_runs": repeated_run_aggregation([]),
            "interval_policy": {
                "binary": (
                    "Clopper-Pearson exact interval only when denominator is positive."
                ),
                "continuous": (
                    "Deterministic percentile bootstrap only when values are present."
                ),
                "empty_denominator": (
                    "value and interval are null; status is not-evaluated."
                ),
            },
        },
        "error_taxonomy": [
            {"id": category, "definition": _taxonomy_definition(category)}
            for category in ERROR_TAXONOMY
        ],
        "small_sample_policy": {
            "threshold": SMALL_SAMPLE_THRESHOLD,
            "warning": (
                "A warning is emitted when a measured denominator is below the "
                "threshold; observations are not discarded."
            ),
        },
        "non_claims": [
            (
                "No run, reviewer label, model output, interval, or statistical "
                "power is asserted."
            ),
            "Separate dimensions are retained; no aggregate quality score is computed.",
            "Protocol capacity and task repetition are not empirical replication.",
        ],
        "outcome": {
            "status": "not-evaluated",
            "reason": "No repeated run, reviewer, or LLM observations were supplied.",
        },
    }


def _taxonomy_definition(category: str) -> str:
    return {
        "false-link": (
            "A returned candidate is labeled as an invalid relation or irrelevant link."
        ),
        "scope-loss": (
            "A result omits or changes the task/system/deployment scope needed for "
            "interpretation."
        ),
        "claim-discipline": (
            "A result changes claim type, overstates status, or lacks required "
            "evidence discipline."
        ),
        "abstention": (
            "The method abstains on an eligible observation; abstention is retained "
            "as its own dimension."
        ),
        "counterexample-miss": (
            "A supplied counterexample or negative-knowledge target is not surfaced "
            "when eligible."
        ),
        "reviewer-disagreement": (
            "Explicit reviewer labels disagree for the same observation."
        ),
    }[category]


def _empty_slice(label: str) -> dict[str, Any]:
    return {
        "slice": label,
        "metrics": {
            category: _error_metric([], category) for category in ERROR_TAXONOMY
        },
        "warnings": [],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(build_artifact(), indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )


if __name__ == "__main__":
    main()

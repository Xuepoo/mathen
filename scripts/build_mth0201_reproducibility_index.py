"""Build the deterministic MTH-0201 research reproducibility index."""

# Reproduction commands and source-boundary prose are kept as exact strings.
# Their line lengths are intentionally not wrapped in the generated contract.
# ruff: noqa: E501

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]
OUTPUT = ROOT / "data/reproducibility/mth-0201-reproducibility-index.json"
BASELINE = "2308f260547e3a618d5498fc4038cef9a297e2b8"


def _digest(path: Path) -> str | None:
    if not path.is_file():
        return None
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def _file(path: str) -> dict[str, Any]:
    return {
        "path": path,
        "present": _digest(ROOT / path) is not None,
        "digest": _digest(ROOT / path),
    }


def _commands(*items: tuple[str, str, str, str | None]) -> list[dict[str, str]]:
    return [
        {
            **{"kind": kind, "command": command, "status": status},
            **({"reason": reason} if reason else {}),
        }
        for kind, command, status, reason in items
    ]


def _item(
    item_id: str,
    title: str,
    status: str,
    files: list[str],
    commands: list[dict[str, str]],
    environment: list[str],
    observations: list[tuple[str, str, str]],
    limitations: list[str],
    *,
    reviewer_kind: str = "not-applicable",
    human_review: bool = False,
    human_stratum: str = "not-applicable",
    direct_llm_status: str = "not-applicable",
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "id": item_id,
        "title": title,
        "status": status,
        "files": [_file(path) for path in files],
        "commands": commands,
        "environment_assumptions": environment,
        "observations": [
            {"name": name, "status": state, "scope": scope}
            for name, state, scope in observations
        ],
        "limitations": limitations,
        "boundary": {
            "research_only": True,
            "canonical": False,
            "review_state": "under-review",
            "promotion_decision": "not-determined",
            "inference_allowed": False,
        },
    }
    if (
        reviewer_kind != "not-applicable"
        or human_stratum != "not-applicable"
        or direct_llm_status != "not-applicable"
    ):
        result["provenance"] = {
            "reviewer_kind": reviewer_kind,
            "human_review": human_review,
            "human_stratum": human_stratum,
            "direct_llm_status": direct_llm_status,
        }
    return result


def build_index() -> dict[str, Any]:
    common_env = [
        "Commands are offline and run from the repository root.",
        "Paths and digests refer to the checked-in origin/main baseline; absent files are not reconstructed.",
    ]
    common_limits = [
        "The record is research-only and does not promote evidence or infer an unmeasured result.",
        "The indexed artifact remains bounded by its own protocol and source revision.",
    ]
    items = [
        _item(
            "MTH-0169",
            "Architecture exploration benchmark fixture",
            "not-present",
            [
                "data/benchmark/mth-0169-exploration.json",
                "schemas/exploration-benchmark.schema.json",
                "scripts/exploration_benchmark.py",
                "docs/mth-0170-exploration-benchmark.md",
            ],
            _commands(
                (
                    "regenerate",
                    "python scripts/exploration_benchmark.py",
                    "unavailable",
                    "The MTH-0169 fixture and builder are historical artifacts and are not present on the baseline.",
                ),
                (
                    "validate",
                    "python scripts/exploration_benchmark.py --validate data/benchmark/mth-0169-exploration.json",
                    "unavailable",
                    "The historical validator cannot run without the absent script.",
                ),
            ),
            common_env
            + [
                "Historical protocol used deterministic normalized token overlap and an offline authored fixture."
            ],
            [
                (
                    "empirical benchmark result",
                    "not-evaluated",
                    "No model output or reviewer labels are present in the historical fixture.",
                ),
                (
                    "direct-LLM condition",
                    "not-evaluated",
                    "No exact provider, model, prompt, runtime, or output provenance.",
                ),
            ],
            common_limits
            + [
                "Historical files are indexed as absent rather than copied from old commits."
            ],
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0172",
            "Candidate discovery quality fixture evaluation",
            "not-present",
            [
                "data/benchmark/mth-0172-candidate-quality.json",
                "scripts/evaluate_exploration.py",
                "docs/mth-0172-candidate-quality.md",
            ],
            _commands(
                (
                    "regenerate",
                    "python scripts/evaluate_exploration.py",
                    "unavailable",
                    "The MTH-0172 evaluator and result are not present on the baseline.",
                ),
                (
                    "validate",
                    "PYTHONPATH=src uv run python -m unittest tests.test_evaluate_exploration -v",
                    "unavailable",
                    "The historical test is not present on the baseline.",
                ),
            ),
            common_env
            + [
                "Historical fixture compared bounded lexical discovery with authored evidence-bounded records."
            ],
            [
                (
                    "authored fixture metrics",
                    "not-evaluated",
                    "The current checkout contains no MTH-0172 result to measure.",
                ),
                (
                    "direct-LLM condition",
                    "not-evaluated",
                    "No direct model run was supplied.",
                ),
            ],
            common_limits
            + [
                "Historical documentation must not be treated as a current checked-in result."
            ],
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0174",
            "Cross-system exploration task set",
            "not-present",
            [
                "data/benchmark/mth-0174-cross-system.json",
                "schemas/expanded-exploration-benchmark.schema.json",
                "scripts/expand_exploration_benchmark.py",
                "docs/mth-0174-cross-system-benchmark.md",
            ],
            _commands(
                (
                    "regenerate",
                    "python scripts/expand_exploration_benchmark.py",
                    "unavailable",
                    "The MTH-0174 task set and builder are absent from the baseline.",
                ),
                (
                    "validate",
                    "python scripts/expand_exploration_benchmark.py --validate data/benchmark/mth-0174-cross-system.json",
                    "unavailable",
                    "The historical validator cannot run without the absent files.",
                ),
            ),
            common_env
            + [
                "Historical task set was authored, offline, and split into train/evaluation/holdout partitions."
            ],
            [
                (
                    "task-set result",
                    "not-evaluated",
                    "Task capacity is not an empirical quality result.",
                ),
                (
                    "direct-LLM condition",
                    "not-evaluated",
                    "No model provenance or output.",
                ),
            ],
            common_limits
            + [
                "Repeated task keys were not independent measurements or statistical power."
            ],
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0175",
            "Blinded reviewer study protocol",
            "partial",
            [
                "data/research-review/mth-0175-study.json",
                "schemas/reviewer-study.schema.json",
                "scripts/reviewer_study.py",
                "docs/mth-0175-review-study.md",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/reviewer_study.py generate <tasks.json> --output <study.json> --study-id mth-0175-example --assignment-seed <seed>",
                    "available",
                    None,
                ),
                (
                    "validate",
                    "uv run python scripts/reviewer_study.py validate data/research-review/mth-0175-study.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_reviewer_pilot -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "The checked-in study is a protocol with empty review records; no human session is assumed."
            ],
            [
                (
                    "review labels",
                    "not-evaluated",
                    "The study contains no completed human labels.",
                ),
                (
                    "human stratum",
                    "not-evaluated",
                    "Empty by protocol, not a zero score.",
                ),
                ("timing", "not-measured", "No completed review timing is supplied."),
            ],
            common_limits
            + [
                "Reviewer assignment balance does not establish agreement, quality, or promotion."
            ],
            reviewer_kind="human",
            human_stratum="empty",
        ),
        _item(
            "MTH-0176",
            "Direct-LLM control boundary",
            "partial",
            [
                "data/benchmark/mth-0176-direct-llm-control.json",
                "schemas/direct-llm-control.schema.json",
                "scripts/direct_llm_control.py",
                "docs/mth-0176-direct-llm-control.md",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/direct_llm_control.py dry-run --provider unavailable --model unavailable --output data/benchmark/mth-0176-direct-llm-control.json",
                    "unavailable",
                    "The checked-in manifest is absent on the baseline.",
                ),
                (
                    "validate",
                    "uv run python scripts/direct_llm_control.py validate data/benchmark/mth-0176-direct-llm-control.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_direct_llm_control -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "A dry run hashes only supplied prompt/input files and performs no inference or network request."
            ],
            [
                (
                    "direct-LLM evaluation",
                    "not-evaluated",
                    "Exact provider/model, runtime, prompt, input, and secret-safe output are required.",
                ),
                (
                    "candidate quality",
                    "not-measured",
                    "No candidates or model output are indexed.",
                ),
            ],
            common_limits
            + [
                "The control contract is not an adapter and cannot establish direct-LLM quality."
            ],
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0177",
            "Statistical error analysis",
            "present",
            [
                "data/benchmark/mth-0177-statistical-analysis.json",
                "schemas/statistical-analysis.schema.json",
                "scripts/statistical_error_analysis.py",
                "docs/mth-0177-statistical-analysis.md",
                "tests/test_statistical_error_analysis.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/statistical_error_analysis.py",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_statistical_error_analysis -v",
                    "available",
                    None,
                ),
                (
                    "audit",
                    "uv run ruff format --check scripts/statistical_error_analysis.py tests/test_statistical_error_analysis.py && uv run ruff check scripts/statistical_error_analysis.py tests/test_statistical_error_analysis.py",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "Statistics are computed offline from checked-in agent observations and benchmark capacity."
            ],
            [
                (
                    "agent stratum",
                    "measured",
                    "Observed agent-only rows and deterministic interval calculations.",
                ),
                (
                    "human stratum",
                    "not-evaluated",
                    "Explicitly empty; null metrics are not zero.",
                ),
                (
                    "direct-LLM condition",
                    "not-evaluated",
                    "No direct model evaluation.",
                ),
            ],
            common_limits
            + [
                "Small samples and authored protocol capacity do not support general quality or human-productivity claims."
            ],
            reviewer_kind="agent",
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0178",
            "SQLite WAL/savepoint composition prototype",
            "not-present",
            [
                "data/experiments/g6-sqlite-composition-mth-0178-results.json",
                "data/experiments/g6-sqlite-composition-observation-mth-0178.json",
                "data/mathviews/sqlite-wal-savepoint-composition-mth-0178.json",
                "scripts/g6_sqlite_composition_experiment.py",
                "docs/mth-0178-prototype-experiment.md",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/g6_sqlite_composition_experiment.py",
                    "unavailable",
                    "The MTH-0178 prototype artifacts are absent from the baseline.",
                ),
                (
                    "validate",
                    "PYTHONPATH=src uv run python -m unittest tests.test_composition_experiment -v",
                    "unavailable",
                    "The historical test is not present on the baseline.",
                ),
            ),
            common_env
            + [
                "Historical protocol assumed CPython 3.13.13, SQLite 3.50.4, Linux 7.3.0-4-cachyos, WAL/FULL, and three repetitions."
            ],
            [
                (
                    "SQLite transition observation",
                    "not-evaluated",
                    "No current result artifact is present.",
                ),
                ("timing", "not-measured", "The historical protocol excluded timing."),
            ],
            common_limits
            + [
                "A finite state-machine candidate would not be a proof or general composition claim."
            ],
        ),
        _item(
            "MTH-0185",
            "Enriched review packet",
            "present",
            [
                "data/research-review/mth-0185-enriched-study.json",
                "schemas/enriched-review-packet.schema.json",
                "scripts/enriched_review_packet.py",
                "docs/mth-0185-enriched-review-packet.md",
                "tests/test_enriched_review_packet.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/enriched_review_packet.py",
                    "available",
                    None,
                ),
                (
                    "validate",
                    "uv run python scripts/enriched_review_packet.py --validate data/research-review/mth-0185-enriched-study.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_enriched_review_packet -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "The packet is built offline from reviewed cards and the bounded negative-knowledge record."
            ],
            [
                (
                    "packet construction",
                    "measured",
                    "Deterministic assignment and evidence digest closure are present.",
                ),
                ("human labels", "not-evaluated", "No reviewer result is generated."),
                ("direct-LLM", "not-evaluated", "No model output is included."),
            ],
            common_limits
            + [
                "Packet construction is not reviewer evidence, a model result, or a promotion decision."
            ],
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0186",
            "Enriched packet A agent pilot",
            "present",
            [
                "data/research-review/pilots/mth-0186.json",
                "schemas/agent-review-pilot.schema.json",
                "scripts/agent_review_pilot.py",
                "tests/test_agent_review_pilot.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/agent_review_pilot.py",
                    "available",
                    None,
                ),
                (
                    "validate",
                    "uv run python scripts/agent_review_pilot.py --validate data/research-review/pilots/mth-0186.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_agent_review_pilot -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "The pilot records bounded payload-handling timing, not conversational reasoning or human review."
            ],
            [
                (
                    "agent payload handling",
                    "observed",
                    "Eight agent-only records retain evidence and timing boundaries.",
                ),
                (
                    "human review",
                    "not-evaluated",
                    "human_review is false and no human stratum is supplied.",
                ),
                ("direct-LLM", "not-evaluated", "Provider/model are not recorded."),
            ],
            common_limits
            + [
                "Agent observations are not human labels, agreement, productivity, or canonical evidence."
            ],
            reviewer_kind="agent",
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0187",
            "Enriched packet B agent pilot",
            "present",
            [
                "data/research-review/pilots/mth-0187.json",
                "schemas/agent-review-pilot-b.schema.json",
                "scripts/agent_review_pilot_b.py",
                "tests/test_agent_review_pilot_b.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/agent_review_pilot_b.py",
                    "available",
                    None,
                ),
                (
                    "validate",
                    "uv run python scripts/agent_review_pilot_b.py --validate data/research-review/pilots/mth-0187.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_agent_review_pilot_b -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "The pilot records bounded payload-handling timing, not conversational reasoning or human review."
            ],
            [
                (
                    "agent payload handling",
                    "observed",
                    "Eight agent-only records retain evidence and timing boundaries.",
                ),
                (
                    "human review",
                    "not-evaluated",
                    "human_review is false and no human stratum is supplied.",
                ),
                ("direct-LLM", "not-evaluated", "Provider/model are not recorded."),
            ],
            common_limits
            + [
                "Agent observations are not human labels, agreement, productivity, or canonical evidence."
            ],
            reviewer_kind="agent",
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0188",
            "Agent-review pilot scoring",
            "present",
            [
                "data/research-review/scoring/mth-0188-agent-review-scoring.json",
                "schemas/agent-review-scoring.schema.json",
                "scripts/agent_review_scoring.py",
                "docs/mth-0188-agent-review-scoring.md",
                "tests/test_agent_review_scoring.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/agent_review_scoring.py",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_agent_review_scoring -v",
                    "available",
                    None,
                ),
                (
                    "audit",
                    "uv run ruff format --check scripts/agent_review_scoring.py tests/test_agent_review_scoring.py && uv run ruff check scripts/agent_review_scoring.py tests/test_agent_review_scoring.py",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "Scoring is deterministic and separates agent observations from the empty human stratum."
            ],
            [
                (
                    "agent scores",
                    "measured",
                    "Observed rows and non-zero/non-null metrics are retained where applicable.",
                ),
                ("human stratum", "not-evaluated", "Empty slices with null metrics."),
                ("direct-LLM", "not-evaluated", "No provider/model evaluation."),
            ],
            common_limits
            + [
                "Agent agreement is not human inter-rater agreement and no aggregate quality score is inferred."
            ],
            reviewer_kind="agent",
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0193",
            "Repeated agent-only review pilot",
            "present",
            [
                "data/research-review/pilots/mth-0193.json",
                "schemas/repeated-agent-review-pilot.schema.json",
                "scripts/repeated_agent_review_pilot.py",
                "docs/mth-0193-repeated-agent-review-pilot.md",
                "tests/test_repeated_agent_review_pilot.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/repeated_agent_review_pilot.py",
                    "available",
                    "A regeneration records new wall-clock timestamps and is a new observation.",
                ),
                (
                    "validate",
                    "uv run python scripts/repeated_agent_review_pilot.py --validate data/research-review/pilots/mth-0193.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_repeated_agent_review_pilot -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "The two runs use independent seeds and packet orders over the frozen MTH-0185 packet."
            ],
            [
                (
                    "agent observations",
                    "observed",
                    "Two runs and 32 bounded agent-only observations are recorded.",
                ),
                ("human stratum", "not-evaluated", "No human records are supplied."),
                ("direct-LLM", "not-evaluated", "Provider/model are not recorded."),
            ],
            common_limits
            + [
                "Timing excludes conversational reasoning, human review, and reviewer productivity."
            ],
            reviewer_kind="agent",
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0194",
            "Direct-LLM local readiness",
            "present",
            [
                "data/analyses/mth-0194-direct-llm-readiness.json",
                "schemas/direct-llm-readiness.schema.json",
                "scripts/direct_llm_readiness.py",
                "docs/mth-0194-direct-llm-readiness.md",
                "tests/test_direct_llm_readiness.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/direct_llm_readiness.py inspect --root . --output data/analyses/mth-0194-direct-llm-readiness.json",
                    "available",
                    "The inspection is environment-dependent and should not overwrite the recorded baseline without review.",
                ),
                (
                    "validate",
                    "uv run python scripts/direct_llm_readiness.py validate data/analyses/mth-0194-direct-llm-readiness.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_direct_llm_readiness -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "Inspection is secret-safe, local, and must not load a model, invoke inference, or contact an endpoint."
            ],
            [
                (
                    "approved runtime",
                    "not-evaluated",
                    "No approved local runtime was recorded.",
                ),
                (
                    "direct-LLM output",
                    "not-evaluated",
                    "Prompt/output and model metrics are null.",
                ),
                (
                    "secret access",
                    "not-measured",
                    "Secret values are deliberately not read.",
                ),
            ],
            common_limits
            + [
                "Cache presence is not runtime approval and readiness is not an inference result."
            ],
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0195",
            "Independent cross-system exploration benchmark",
            "present",
            [
                "data/benchmark/mth-0195-independent-exploration.json",
                "schemas/independent-exploration-benchmark.schema.json",
                "scripts/build_mth0195_benchmark.py",
                "docs/mth-0195-independent-exploration-benchmark.md",
                "tests/test_mth0195_benchmark.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/build_mth0195_benchmark.py",
                    "available",
                    None,
                ),
                (
                    "validate",
                    "uv run python scripts/build_mth0195_benchmark.py --validate data/benchmark/mth-0195-independent-exploration.json",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_mth0195_benchmark -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "The benchmark is authored, offline, and stores task/evidence/source digests without model outputs."
            ],
            [
                (
                    "task set",
                    "protocol-defined",
                    "Twenty-four task instances and exhaustive partitions are defined.",
                ),
                (
                    "empirical quality",
                    "not-measured",
                    "No reviewer labels or model outputs are present.",
                ),
                (
                    "direct-LLM",
                    "not-evaluated",
                    "The condition is explicit but unevaluated.",
                ),
            ],
            common_limits
            + [
                "Task capacity and composition candidates do not establish statistical power, truth, compatibility, or superiority."
            ],
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0196",
            "Agent-review aggregation release",
            "represented",
            [
                "data/benchmark/mth-0177-statistical-analysis.json",
                "data/research-review/scoring/mth-0188-agent-review-scoring.json",
                "docs/mth-0188-agent-review-scoring.md",
                "docs/mth-0177-statistical-analysis.md",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run python scripts/statistical_error_analysis.py && uv run python scripts/agent_review_scoring.py",
                    "available",
                    None,
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_statistical_error_analysis tests.test_agent_review_scoring -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "MTH-0196 is represented by the checked-in statistical and scoring artifacts rather than a separate file."
            ],
            [
                (
                    "agent aggregation",
                    "measured",
                    "Repeated agent observations are aggregated with explicit uncertainty and slices.",
                ),
                ("human stratum", "not-evaluated", "Empty by contract."),
                ("direct-LLM", "not-evaluated", "No direct model evaluation."),
            ],
            common_limits
            + [
                "This release preserves observed strata and does not infer a combined quality result."
            ],
            reviewer_kind="agent",
            human_stratum="empty",
            direct_llm_status="not-evaluated",
        ),
        _item(
            "MTH-0197",
            "SQLite busy-timeout observation",
            "present",
            [
                "data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json",
                "data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json",
                "data/mathviews/sqlite-busy-timeout-mth-0197.json",
                "scripts/g5_sqlite_busy_timeout_experiment.py",
                "docs/mth-0197-sqlite-busy-timeout-observation.md",
                "tests/test_experiments.py",
            ],
            _commands(
                (
                    "regenerate",
                    "uv run --offline python scripts/g5_sqlite_busy_timeout_experiment.py --expected-source-id 4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3 --repetitions 3 --output data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json --observation-output data/experiments/g5-sqlite-busy-timeout-observation-mth-0197.json",
                    "available",
                    "Requires the same SQLite source ID; a new run is a new observation.",
                ),
                (
                    "test",
                    "PYTHONPATH=src uv run python -m unittest tests.test_experiments -v",
                    "available",
                    None,
                ),
            ),
            common_env
            + [
                "Recorded environment is Linux 7.3.0-4-cachyos, Python 3.13.13, SQLite 3.50.4, two local writers, and SQLite defaults."
            ],
            [
                (
                    "lock/reopen/integrity sequence",
                    "observed",
                    "Three bounded repetitions observed the declared lock failure and successful post-release state.",
                ),
                ("timing", "not-measured", "Timing is explicitly null."),
                (
                    "canonical status",
                    "not-measured",
                    "The observation and math view remain canonical=false and under review.",
                ),
            ],
            common_limits
            + [
                "This does not establish general concurrency, timeout policy, durability, crash recovery, performance, or deployment behavior."
            ],
        ),
        _item(
            "MTH-0198",
            "Graph browser and local performance audit",
            "present",
            ["docs/mth-0198-graph-browser-audit.md", "tests/test_graph_audit.py"],
            _commands(
                (
                    "regenerate",
                    "bun run db:reset:local && bun run build",
                    "available",
                    "The documentation records the completed local audit; browser execution requires local services and system Chromium.",
                ),
                (
                    "test",
                    "bun run check:web && bun test apps/web/src/*.test.ts",
                    "available",
                    None,
                ),
                (
                    "audit",
                    "lighthouse http://127.0.0.1:4174/ --output=json --output-path=/tmp/opencode/mth-0198-lighthouse.json --chrome-path=/usr/bin/chromium --chrome-flags='--no-sandbox' --quiet",
                    "available",
                    "Requires a local production preview.",
                ),
            ),
            common_env
            + [
                "Audit used headed Chromium 156.0.8078.47, Playwright 1.64.0, Vite production output, and local API/web services."
            ],
            [
                (
                    "desktop/local browser checks",
                    "observed",
                    "Graph load, mode switching, search, inspector, path panel, catalog, and card metadata were checked.",
                ),
                (
                    "local Lighthouse smoke",
                    "measured",
                    "The recorded audit contains local performance/accessibility metrics.",
                ),
                (
                    "Firefox/mobile/touch/edge targeting",
                    "not-measured",
                    "The audit explicitly makes no pass claim for these surfaces.",
                ),
            ],
            common_limits
            + [
                "A desktop Chromium viewport and local Lighthouse run are not representative mobile, network, or production metrics."
            ],
        ),
    ]
    return {
        "schema_version": "1.0",
        "index_id": "mth-0201-reproducibility-index",
        "research_only": True,
        "canonical": False,
        "promotion_boundary": {
            "human_review_required": True,
            "promotion_decision": "not-determined",
            "inference_allowed": False,
        },
        "baseline": {
            "source_ref": "origin/main after PR #74 merge",
            "source_revision": BASELINE,
            "scope": "Current Architecture Exploration Methodology research artifacts only; no canonical, API, MCP, migration, relation, production, or paper changes.",
        },
        "package_sources": [
            _file("schemas/reproducibility-index.schema.json"),
            _file("scripts/build_mth0201_reproducibility_index.py"),
            _file("docs/mth-0201-reproducibility-index.md"),
        ],
        "work_items": items,
    }


def validate_index(value: dict[str, Any]) -> None:
    if value != build_index():
        raise ValueError("index differs from deterministic builder output")
    if [item["id"] for item in value["work_items"]] != [
        f"MTH-{n:04d}"
        for n in (
            169,
            172,
            174,
            175,
            176,
            177,
            178,
            185,
            186,
            187,
            188,
            193,
            194,
            195,
            196,
            197,
            198,
        )
    ]:
        raise ValueError("work item coverage is incomplete or out of order")
    for item in value["work_items"]:
        for record in item["files"]:
            if record["present"] != (record["digest"] is not None):
                raise ValueError(f"presence/digest mismatch: {record['path']}")
        if item["boundary"] != {
            "research_only": True,
            "canonical": False,
            "review_state": "under-review",
            "promotion_decision": "not-determined",
            "inference_allowed": False,
        }:
            raise ValueError(f"promotion boundary changed: {item['id']}")
        if (
            item.get("provenance", {}).get("reviewer_kind") == "agent"
            and item["provenance"]["human_review"] is not False
        ):
            raise ValueError(f"agent record has human_review=true: {item['id']}")
        if item.get("provenance", {}).get("human_stratum") == "empty" and any(
            obs["status"] != "not-evaluated"
            for obs in item["observations"]
            if obs["name"] == "human stratum"
        ):
            raise ValueError(f"human stratum is not empty/not-evaluated: {item['id']}")
        if item.get("provenance", {}).get(
            "direct_llm_status"
        ) == "not-evaluated" and any(
            "direct-llm" in obs["name"].lower() and obs["status"] != "not-evaluated"
            for obs in item["observations"]
        ):
            raise ValueError(f"direct-LLM status changed: {item['id']}")


def main() -> int:
    import argparse

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT)
    parser.add_argument("--validate", type=Path)
    args = parser.parse_args()
    if args.validate:
        value = json.loads(args.validate.read_text(encoding="utf-8"))
        validate_index(value)
        return 0
    value = build_index()
    validate_index(value)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

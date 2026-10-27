"""Run a bounded SQLite two-writer busy/timeout observation."""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import platform
import shlex
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Any

SYSTEM_COMMIT = "4d8adfb30e03f9cf27f800a2c1ba3c48fb4ca1b08b0f5ed59a4d5ecbf45e20a3"
DATASET_ROWS = (
    (1, "alpha", 10),
    (2, "beta", 20),
    (3, "gamma", 30),
    (4, "delta", 40),
)
APPENDED_ROW = (5, "epsilon", 50)
OUTPUT_REFERENCE = "data/experiments/g5-sqlite-busy-timeout-results-mth-0197.json"
PROTOCOL_SPEC = {
    "question": "bounded two-writer lock contention with zero busy timeout",
    "journal_mode": "SQLite default",
    "synchronous_mode": "SQLite default",
    "connections": 2,
    "holder_timeout_seconds": 5.0,
    "contender_timeout_seconds": 0.0,
    "seed_rows": [list(row) for row in DATASET_ROWS],
    "appended_row": list(APPENDED_ROW),
    "failure_oracle": [
        "the holder begins an IMMEDIATE transaction and keeps its appended row "
        "uncommitted",
        "the zero-timeout contender receives sqlite3.OperationalError: database "
        "is locked",
        "the holder commit and contender post-release read contain the seed plus "
        "appended row",
        "close/reopen contains the seed plus appended row and integrity_check is ok",
        "all repetitions produce equal observations",
    ],
}


def _sha256_json(value: object) -> str:
    encoded = json.dumps(value, separators=(",", ":"), sort_keys=True).encode()
    return hashlib.sha256(encoded).hexdigest()


def _state(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT id, name, value FROM records ORDER BY id"
    ).fetchall()
    return {
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
        "value_sum": sum(row[2] for row in rows),
    }


def _configuration(connection: sqlite3.Connection) -> dict[str, Any]:
    return {
        "journal_mode": connection.execute("PRAGMA journal_mode").fetchone()[0],
        "synchronous": connection.execute("PRAGMA synchronous").fetchone()[0],
        "busy_timeout_ms": connection.execute("PRAGMA busy_timeout").fetchone()[0],
    }


def _run_once() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="mathen-g5-busy-timeout-") as directory:
        database = Path(directory) / "experiment.sqlite"
        holder = sqlite3.connect(database, timeout=5.0)
        holder.execute(
            "CREATE TABLE records "
            "(id INTEGER PRIMARY KEY, name TEXT NOT NULL, value INTEGER NOT NULL)"
        )
        holder.executemany(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)", DATASET_ROWS
        )
        holder.commit()
        holder_configuration = _configuration(holder)

        contender = sqlite3.connect(database, timeout=0.0)
        contender_configuration = _configuration(contender)
        holder.execute("BEGIN IMMEDIATE")
        holder.execute(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)", APPENDED_ROW
        )
        holder_uncommitted = _state(holder)

        try:
            contender.execute("BEGIN IMMEDIATE")
            contender_failure: dict[str, Any] = {
                "status": "not-observed",
                "exception_type": None,
                "exception_message": None,
            }
        except sqlite3.OperationalError as error:
            contender_failure = {
                "status": "observed",
                "exception_type": type(error).__name__,
                "exception_message": str(error),
            }

        holder.commit()
        holder_after_commit = _state(holder)
        integrity_check = holder.execute("PRAGMA integrity_check").fetchone()[0]
        contender_after_release = _state(contender)
        contender.close()
        holder.close()

        reopened = sqlite3.connect(database, timeout=0.0)
        reopened_state = _state(reopened)
        reopened_integrity_check = reopened.execute(
            "PRAGMA integrity_check"
        ).fetchone()[0]
        reopened.close()

    seed = {
        "rows": [list(row) for row in DATASET_ROWS],
        "row_count": 4,
        "value_sum": 100,
    }
    committed = {
        "rows": [list(row) for row in DATASET_ROWS] + [list(APPENDED_ROW)],
        "row_count": 5,
        "value_sum": 150,
    }
    checks = {
        "holder_started_from_seed": holder_uncommitted["rows"] == committed["rows"],
        "zero_timeout_lock_observed": contender_failure
        == {
            "status": "observed",
            "exception_type": "OperationalError",
            "exception_message": "database is locked",
        },
        "holder_commit_preserved": holder_after_commit == committed,
        "contender_read_after_release": contender_after_release == committed,
        "reopen_preserved": reopened_state == committed,
        "integrity_checks_ok": integrity_check == "ok"
        and reopened_integrity_check == "ok",
    }
    return {
        "configuration": {
            "holder": holder_configuration,
            "contender": contender_configuration,
        },
        "seed": seed,
        "holder_uncommitted": holder_uncommitted,
        "contender_failure": contender_failure,
        "holder_after_commit": holder_after_commit,
        "contender_after_release": contender_after_release,
        "reopened": reopened_state,
        "integrity_check": integrity_check,
        "reopened_integrity_check": reopened_integrity_check,
        "checks": checks,
        "oracle_passed": all(checks.values()),
    }


def _environment() -> dict[str, str]:
    connection = sqlite3.connect(":memory:")
    version, source_id = connection.execute(
        "SELECT sqlite_version(), sqlite_source_id()"
    ).fetchone()
    connection.close()
    return {
        "os": platform.system(),
        "os_release": platform.release(),
        "architecture": platform.machine(),
        "python": platform.python_version(),
        "sqlite": version,
        "sqlite_source_id": source_id,
    }


def build_report(repetitions: int, output: Path) -> dict[str, Any]:
    if repetitions < 1:
        raise ValueError("repetitions must be positive")
    results = [_run_once() for _ in range(repetitions)]
    consistent = all(result == results[0] for result in results[1:])
    environment = _environment()
    commit = environment["sqlite_source_id"].split()[-1]
    runner_digest = hashlib.sha256(
        Path(__file__).read_bytes().replace(b"\r\n", b"\n")
    ).hexdigest()
    passed = all(result["oracle_passed"] for result in results) and consistent
    status = "observed" if passed else "failed"
    return {
        "id": "g5-sqlite-busy-timeout-mth-0197",
        "kind": "experiment",
        "title": "SQLite two-writer busy timeout behavior — MTH-0197",
        "uri": f"https://sqlite.org/src/info/{commit}",
        "observation_version": "1",
        "protocol": (
            "For each repetition, create a fresh SQLite database with the default "
            "journal and synchronous settings, commit a fixed four-row seed, begin "
            "an IMMEDIATE transaction on a holder connection, insert one row without "
            "committing, and attempt BEGIN IMMEDIATE on a second connection with a "
            "zero-second timeout. Then commit the holder and compare the contender's "
            "post-release read, close/reopen state, integrity checks, and repetitions."
        ),
        "system_commit": commit,
        "environment": environment,
        "command": (
            "uv run --offline python scripts/g5_sqlite_busy_timeout_experiment.py "
            f"--expected-source-id {commit} --repetitions {repetitions} "
            f"--output {shlex.quote(OUTPUT_REFERENCE)}"
        ),
        "dataset": {
            "name": "fixed-records-v1",
            "rows": [list(row) for row in DATASET_ROWS],
            "appended_row": list(APPENDED_ROW),
            "schema": (
                "records(id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                "value INTEGER NOT NULL)"
            ),
        },
        "repetitions": repetitions,
        "metrics": {
            "seed_rows": 4,
            "holder_uncommitted_rows": 5,
            "contender_lock_failures": sum(
                result["checks"]["zero_timeout_lock_observed"] for result in results
            ),
            "holder_commit_rows": 5,
            "contender_post_release_rows": 5,
            "reopened_rows": 5,
            "integrity_checks_passed": sum(
                result["checks"]["integrity_checks_ok"] for result in results
            ),
            "oracle_checks_passed": sum(result["oracle_passed"] for result in results),
            "repetitions_consistent": int(consistent),
        },
        "artifacts": [
            {
                "id": "g5-sqlite-busy-timeout-runner-mth-0197",
                "kind": "runner-source",
                "path": "scripts/g5_sqlite_busy_timeout_experiment.py",
                "digest": f"sha256:{runner_digest}",
                "results": results,
            }
        ],
        "workload": {
            "name": "fixed four-row seed with one uncommitted holder row",
            "protocol": (
                "two local writers; zero-timeout BEGIN IMMEDIATE contention; "
                "commit; reopen"
            ),
        },
        "conditions": {
            "journal_mode": "SQLite default",
            "synchronous_mode": "SQLite default",
            "connections": "one holder and one zero-timeout contender",
            "holder_timeout_seconds": 5.0,
            "contender_timeout_seconds": 0.0,
            "failure_oracle": PROTOCOL_SPEC["failure_oracle"],
            "timing": "not measured",
        },
        "provenance": {
            "run_id": "g5-sqlite-busy-timeout-mth-0197",
            "source_revision": commit,
            "protocol_digest": f"sha256:{_sha256_json(PROTOCOL_SPEC)}",
            "recorded_at": "2026-10-28T00:00:00Z",
            "runner": "mathen-local-experiment-runner",
            "toolchain": {
                "python": environment["python"],
                "sqlite": environment["sqlite"],
                "os": environment["os_release"],
                "runner_sha256": f"sha256:{runner_digest}",
            },
        },
        "result_boundary": {
            "canonical": False,
            "promotion_requires_human_review": True,
            "storage_scope": "research",
            "limits": [
                "one fixed four-row dataset and one appended row",
                "three repetitions on one Linux host and one Python/SQLite build",
                "two local writers with a zero-second contender timeout",
                "SQLite default journal and synchronous settings",
                "does not test process crashes, power loss, checkpoint behavior, "
                "durability, performance, other journal modes, nonzero timeout "
                "policy, or general concurrency compatibility",
            ],
        },
        "result": {
            "status": status,
            "summary": (
                "The bounded zero-timeout contender received database is locked while "
                "the holder transaction was open; after the holder committed, the "
                "contender and a close/reopen observed the five-row state in all "
                f"{repetitions} repetitions."
                if passed
                else (
                    "The bounded two-writer protocol did not satisfy every "
                    "declared oracle check."
                )
            ),
            "measurements": [
                {
                    "id": "contender-lock-failures",
                    "value": sum(
                        result["checks"]["zero_timeout_lock_observed"]
                        for result in results
                    ),
                    "unit": "repetitions",
                    "status": "observed" if passed else "not-observed",
                },
                {
                    "id": "committed-rows",
                    "value": 5 if passed else None,
                    "unit": "rows",
                    "status": "observed" if passed else "not-observed",
                },
                {
                    "id": "timing",
                    "value": None,
                    "unit": "milliseconds",
                    "status": "not-measured",
                    "notes": "Timing was outside the protocol.",
                },
            ],
        },
        "review": {"status": "unreviewed", "card_claim_refs": []},
        "scope_context": {
            "validity_scope": {
                "status": "specified",
                "systems": ["SQLite"],
                "versions": [f"SQLite source {commit}"],
                "deployment_origins": ["local-process"],
                "conditions": [
                    "Linux x86_64",
                    "SQLite default journal and synchronous settings",
                    "two local writer connections",
                    "zero-second contender timeout",
                ],
                "exclusions": [
                    "process crash",
                    "power loss",
                    "checkpoint behavior",
                    "durability",
                    "performance",
                    "other journal modes",
                    "nonzero timeout policy",
                ],
                "evidence_ids": ["g5-sqlite-busy-timeout-observation-mth-0197"],
                "claim_type": "fact",
                "claim_status": "under-review",
            },
            "workload": {
                "status": "specified",
                "values": [
                    "fixed four-row seed",
                    "one appended holder row",
                    f"{repetitions} repetitions",
                ],
                "evidence_ids": ["g5-sqlite-busy-timeout-observation-mth-0197"],
                "claim_type": "fact",
                "claim_status": "under-review",
            },
            "runtime_conditions": {
                "status": "specified",
                "values": [
                    f"CPython {environment['python']}",
                    f"SQLite {environment['sqlite']}",
                    f"Linux {environment['os_release']}",
                    "two local writers",
                    "zero-second contender timeout",
                ],
                "evidence_ids": ["g5-sqlite-busy-timeout-observation-mth-0197"],
                "claim_type": "fact",
                "claim_status": "under-review",
            },
            "scale": {
                "status": "specified",
                "values": [
                    "4 seed rows",
                    "5 holder and committed rows",
                    "2 local writer connections",
                    f"{repetitions} repetitions",
                ],
                "evidence_ids": ["g5-sqlite-busy-timeout-observation-mth-0197"],
                "claim_type": "fact",
                "claim_status": "under-review",
            },
            "failure_conditions": {
                "status": "specified",
                "values": PROTOCOL_SPEC["failure_oracle"],
                "evidence_ids": ["g5-sqlite-busy-timeout-observation-mth-0197"],
                "claim_type": "fact",
                "claim_status": "under-review",
            },
        },
        "result_details": {"checks": results[0]["checks"], "per_repetition": results},
    }


def build_observation(report: dict[str, Any], raw_digest: str) -> dict[str, Any]:
    """Build the detached observation contract from a raw runner report."""

    observation = copy.deepcopy(report)
    observation["id"] = "g5-sqlite-busy-timeout-observation-mth-0197"
    observation["artifacts"] = [
        {
            "id": "g5-sqlite-busy-timeout-results-mth-0197",
            "kind": "experiment-results",
            "path": OUTPUT_REFERENCE,
            "digest": f"sha256:{raw_digest}",
        },
        {
            "id": "g5-sqlite-busy-timeout-runner-mth-0197",
            "kind": "runner-source",
            "path": "scripts/g5_sqlite_busy_timeout_experiment.py",
            "digest": report["artifacts"][0]["digest"],
        },
    ]
    observation.pop("result_details", None)
    return observation


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--observation-output", type=Path)
    parser.add_argument("--expected-source-id", default=SYSTEM_COMMIT)
    args = parser.parse_args()
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    source_id = _environment()["sqlite_source_id"].split()[-1]
    if source_id != args.expected_source_id:
        parser.error("SQLite source ID differs from --expected-source-id")
    report = build_report(args.repetitions, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    if args.observation_output:
        raw_digest = hashlib.sha256(args.output.read_bytes()).hexdigest()
        args.observation_output.parent.mkdir(parents=True, exist_ok=True)
        args.observation_output.write_text(
            json.dumps(build_observation(report, raw_digest), indent=2) + "\n",
            encoding="utf-8",
        )
    print(json.dumps(report["metrics"], sort_keys=True))
    return 0 if report["result"]["status"] == "observed" else 1


if __name__ == "__main__":
    sys.exit(main())

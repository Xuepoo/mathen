"""Run a fixed SQLite savepoint partial-rollback experiment."""

from __future__ import annotations

import argparse
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


def _state(connection: sqlite3.Connection) -> dict[str, Any]:
    rows = connection.execute(
        "SELECT id, name, value FROM records ORDER BY id"
    ).fetchall()
    return {
        "rows": [list(row) for row in rows],
        "row_count": len(rows),
        "value_sum": sum(row[2] for row in rows),
    }


def _run_once() -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="mathen-g5-savepoint-") as directory:
        database = Path(directory) / "experiment.sqlite"
        connection = sqlite3.connect(database)
        connection.execute(
            "CREATE TABLE records "
            "(id INTEGER PRIMARY KEY, name TEXT NOT NULL, value INTEGER NOT NULL)"
        )

        connection.execute("BEGIN")
        connection.executemany(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)", DATASET_ROWS
        )
        connection.commit()
        seeded = _state(connection)

        connection.execute("BEGIN")
        connection.execute(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)",
            (5, "epsilon", 50),
        )
        before_savepoint_rollback = _state(connection)
        connection.execute("SAVEPOINT add_second_row")
        connection.execute(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)",
            (6, "zeta", 60),
        )
        after_savepoint_insert = _state(connection)
        connection.execute("ROLLBACK TO add_second_row")
        after_savepoint_rollback = _state(connection)
        connection.execute("RELEASE add_second_row")
        connection.commit()
        after_outer_commit = _state(connection)
        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        connection.close()

        reopened = sqlite3.connect(database)
        reopened_state = _state(reopened)
        reopened.close()

    final_rows = after_outer_commit["rows"]
    digest = hashlib.sha256(
        json.dumps(final_rows, separators=(",", ":"), sort_keys=False).encode()
    ).hexdigest()
    return {
        "seeded": seeded,
        "before_savepoint_rollback": before_savepoint_rollback,
        "after_savepoint_insert": after_savepoint_insert,
        "after_savepoint_rollback": after_savepoint_rollback,
        "after_outer_commit": after_outer_commit,
        "reopened": reopened_state,
        "integrity_check": integrity_check,
        "final_rows_sha256": digest,
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
    final = results[0]
    environment = _environment()
    commit = environment["sqlite_source_id"].split()[-1]
    expected_seed = [list(row) for row in DATASET_ROWS]
    expected_outer = expected_seed + [[5, "epsilon", 50]]
    expected_inner = expected_outer + [[6, "zeta", 60]]
    for result in results:
        if not (
            result["seeded"]["rows"] == expected_seed
            and result["before_savepoint_rollback"]["rows"] == expected_outer
            and result["after_savepoint_insert"]["rows"] == expected_inner
            and result["after_savepoint_rollback"]["rows"] == expected_outer
            and result["after_outer_commit"]["rows"] == expected_outer
            and result["reopened"] == result["after_outer_commit"]
            and result["integrity_check"] == "ok"
        ):
            raise RuntimeError(
                "Savepoint observations differ from protocol expectations"
            )
    if not consistent:
        raise RuntimeError("Repetitions produced inconsistent observations")
    return {
        "id": "g5-sqlite-savepoint",
        "kind": "experiment",
        "title": "SQLite savepoint partial rollback preserves outer transaction work",
        "uri": f"https://sqlite.org/src/info/{commit}",
        "protocol": (
            "For each repetition, create a fresh SQLite database, commit a fixed "
            "four-row dataset, begin a transaction and insert a fifth row, create "
            "a savepoint, insert a sixth row, roll back to and release the savepoint, "
            "then commit the outer transaction. Compare states before and after the "
            "savepoint rollback, check integrity, reopen, and compare repetitions."
        ),
        "system_commit": commit,
        "environment": environment,
        "command": (
            "uv run --offline python scripts/g5_sqlite_savepoint_experiment.py "
            f"--expected-source-id {commit} --repetitions {repetitions} "
            f"--output {shlex.quote(str(output))}"
        ),
        "dataset": {
            "name": "fixed-records-v1",
            "rows": [list(row) for row in DATASET_ROWS],
            "schema": (
                "records(id INTEGER PRIMARY KEY, name TEXT NOT NULL, "
                "value INTEGER NOT NULL)"
            ),
        },
        "repetitions": repetitions,
        "metrics": {
            "seed_rows": final["seeded"]["row_count"],
            "outer_rows_before_savepoint": final["before_savepoint_rollback"][
                "row_count"
            ],
            "inner_rows_before_savepoint_rollback": final["after_savepoint_insert"][
                "row_count"
            ],
            "rows_after_savepoint_rollback": final["after_savepoint_rollback"][
                "row_count"
            ],
            "rows_after_outer_commit": final["after_outer_commit"]["row_count"],
            "reopened_rows": final["reopened"]["row_count"],
            "integrity_checks_passed": sum(
                result["integrity_check"] == "ok" for result in results
            ),
            "savepoint_rollback_checks_passed": sum(
                result["after_savepoint_rollback"]
                == result["before_savepoint_rollback"]
                for result in results
            ),
            "outer_commit_checks_passed": sum(
                result["after_outer_commit"]["rows"] == expected_outer
                for result in results
            ),
            "repetitions_consistent": int(consistent),
        },
        "artifacts": [
            {
                "name": "per-repetition-observations",
                "results": results,
                "runner_sha256": hashlib.sha256(
                    Path(__file__).read_bytes().replace(b"\r\n", b"\n")
                ).hexdigest(),
            }
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repetitions", type=int, default=3)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--expected-source-id", default=SYSTEM_COMMIT)
    args = parser.parse_args()
    if _environment()["sqlite_source_id"].split()[-1] != args.expected_source_id:
        parser.error("SQLite source ID differs from --expected-source-id")
    if args.repetitions < 1:
        parser.error("--repetitions must be positive")
    report = build_report(args.repetitions, args.output)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(report, indent=2, sort_keys=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(report["metrics"], sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())

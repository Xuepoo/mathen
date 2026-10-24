"""Run the fixed-dataset SQLite transaction reproducibility experiment."""

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
    with tempfile.TemporaryDirectory(prefix="mathen-g5-") as directory:
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
        try:
            connection.execute(
                "INSERT INTO records (id, name, value) VALUES (?, ?, ?)",
                (5, "epsilon", 50),
            )
            connection.execute(
                "INSERT INTO records (id, name, value) VALUES (?, ?, ?)",
                (1, "duplicate-alpha", 999),
            )
        except sqlite3.IntegrityError:
            connection.rollback()
            failed_transaction_rolled_back = True
        else:
            raise AssertionError("duplicate primary key did not raise IntegrityError")
        after_rollback = _state(connection)

        connection.execute("BEGIN")
        connection.execute(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)",
            (5, "epsilon", 50),
        )
        connection.commit()
        recovered = _state(connection)
        integrity_check = connection.execute("PRAGMA integrity_check").fetchone()[0]
        connection.close()

        reopened = sqlite3.connect(database)
        reopened_state = _state(reopened)
        reopened.close()

    final_rows = recovered["rows"]
    digest = hashlib.sha256(
        json.dumps(final_rows, separators=(",", ":"), sort_keys=False).encode()
    ).hexdigest()
    return {
        "seeded": seeded,
        "after_rollback": after_rollback,
        "recovered": recovered,
        "reopened": reopened_state,
        "failed_transaction_rolled_back": failed_transaction_rolled_back,
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
    expected_final = expected_seed + [[5, "epsilon", 50]]
    for result in results:
        if not (
            result["seeded"]["rows"] == expected_seed
            and result["after_rollback"] == result["seeded"]
            and result["recovered"]["rows"] == expected_final
            and result["reopened"] == result["recovered"]
            and result["integrity_check"] == "ok"
        ):
            raise RuntimeError(
                "Transaction observations differ from protocol expectations"
            )
    if not consistent:
        raise RuntimeError("Repetitions produced inconsistent observations")
    return {
        "id": "g5-sqlite-transaction",
        "kind": "experiment",
        "title": "SQLite transaction rollback and post-rollback recovery",
        "uri": f"https://sqlite.org/src/info/{commit}",
        "protocol": (
            "For each repetition, create a fresh SQLite database, insert the fixed "
            "four-row dataset in a committed transaction, attempt a transaction "
            "that contains a duplicate primary key and roll it back, then commit "
            "the pending fifth row in a new transaction. Check integrity, reopen "
            "the database, and compare all observations across repetitions."
        ),
        "system_commit": commit,
        "environment": environment,
        "command": (
            "uv run --offline python scripts/g5_sqlite_transaction_experiment.py "
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
            "seed_value_sum": final["seeded"]["value_sum"],
            "rollback_preserved_rows": final["after_rollback"]["row_count"],
            "rollback_preserved_sum": final["after_rollback"]["value_sum"],
            "recovered_rows": final["recovered"]["row_count"],
            "recovered_value_sum": final["recovered"]["value_sum"],
            "reopened_rows": final["reopened"]["row_count"],
            "integrity_checks_passed": sum(
                result["integrity_check"] == "ok" for result in results
            ),
            "rollback_checks_passed": sum(
                result["failed_transaction_rolled_back"] for result in results
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

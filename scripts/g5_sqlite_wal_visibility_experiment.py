"""Run a fixed-dataset SQLite WAL reader-visibility experiment."""

from __future__ import annotations

import argparse
import hashlib
import json
import platform
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
OUTPUT_REFERENCE = "data/experiments/g5-sqlite-wal-visibility-results.json"


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
    with tempfile.TemporaryDirectory(prefix="mathen-g5-wal-") as directory:
        database = Path(directory) / "experiment.sqlite"
        writer = sqlite3.connect(database, timeout=5)
        writer.execute("PRAGMA journal_mode=WAL")
        writer.execute("PRAGMA synchronous=FULL")
        writer.execute(
            "CREATE TABLE records "
            "(id INTEGER PRIMARY KEY, name TEXT NOT NULL, value INTEGER NOT NULL)"
        )
        writer.executemany(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)", DATASET_ROWS
        )
        writer.commit()

        reader = sqlite3.connect(database, timeout=5)
        reader.execute("PRAGMA synchronous=FULL")
        journal_mode = reader.execute("PRAGMA journal_mode").fetchone()[0]
        reader.execute("BEGIN")
        reader_snapshot = _state(reader)

        writer.execute("BEGIN")
        writer.execute(
            "INSERT INTO records (id, name, value) VALUES (?, ?, ?)", APPENDED_ROW
        )
        writer.commit()
        writer_after_commit = _state(writer)
        reader_during_writer_commit = _state(reader)

        reader.commit()
        reader.execute("BEGIN")
        reader_after_refresh = _state(reader)
        reader.commit()
        integrity_check = writer.execute("PRAGMA integrity_check").fetchone()[0]
        reader.close()
        writer.close()

    final_rows = reader_after_refresh["rows"]
    digest = hashlib.sha256(
        json.dumps(final_rows, separators=(",", ":"), sort_keys=False).encode()
    ).hexdigest()
    return {
        "journal_mode": journal_mode,
        "reader_snapshot": reader_snapshot,
        "writer_after_commit": writer_after_commit,
        "reader_during_writer_commit": reader_during_writer_commit,
        "reader_after_refresh": reader_after_refresh,
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
    expected_final = expected_seed + [list(APPENDED_ROW)]
    for result in results:
        if not (
            result["journal_mode"] == "wal"
            and result["reader_snapshot"]["rows"] == expected_seed
            and result["reader_during_writer_commit"] == result["reader_snapshot"]
            and result["writer_after_commit"]["rows"] == expected_final
            and result["reader_after_refresh"] == result["writer_after_commit"]
            and result["integrity_check"] == "ok"
        ):
            raise RuntimeError(
                "WAL visibility observations differ from protocol expectations"
            )
    if not consistent:
        raise RuntimeError("Repetitions produced inconsistent observations")
    return {
        "id": "g5-sqlite-wal-visibility",
        "kind": "experiment",
        "title": "SQLite WAL reader snapshot visibility after writer commit",
        "uri": f"https://sqlite.org/src/info/{commit}",
        "protocol": (
            "For each repetition, create a fresh SQLite database, enable WAL and "
            "FULL synchronous mode, commit a fixed four-row dataset, begin a "
            "reader transaction, commit one appended row from a writer connection, "
            "read again from the held reader snapshot, then start a fresh reader "
            "transaction and compare all observations across repetitions."
        ),
        "system_commit": commit,
        "environment": environment,
        "command": (
            "uv run --offline python scripts/g5_sqlite_wal_visibility_experiment.py "
            f"--expected-source-id {commit} --repetitions {repetitions} "
            f"--output {OUTPUT_REFERENCE}"
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
            "seed_rows": final["reader_snapshot"]["row_count"],
            "snapshot_rows_during_writer_commit": final["reader_during_writer_commit"][
                "row_count"
            ],
            "writer_rows_after_commit": final["writer_after_commit"]["row_count"],
            "refreshed_reader_rows": final["reader_after_refresh"]["row_count"],
            "integrity_checks_passed": sum(
                result["integrity_check"] == "ok" for result in results
            ),
            "snapshot_checks_passed": sum(
                result["reader_during_writer_commit"] == result["reader_snapshot"]
                for result in results
            ),
            "refresh_checks_passed": sum(
                result["reader_after_refresh"] == result["writer_after_commit"]
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

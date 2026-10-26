#!/usr/bin/env python3
"""Fail-closed validation helpers for the CarryCtx snapshot wrappers."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import tomllib
from pathlib import Path
from typing import NoReturn

HEX_SHA = re.compile(r"^[0-9a-f]{40,64}$")
SOURCE = re.compile(r"^mathen@([0-9a-f]{7,64})(?: \([A-Za-z0-9._/-]{1,100}\))?$")
CLI = re.compile(r"^0\.12\.(\d+)$")
FORMAT = "carryctx-pack-dir"
SCHEMA = 18
ACTIVE_SESSIONS = {"active", "paused"}
ACTIVE_OPERATIONS = {"prepared"}
ACTIVE_CLEANUP = {"running"}


def fail(message: str) -> NoReturn:
    raise SystemExit(f"workflow-snapshot: FAIL: {message}")


def load_config(path: Path) -> dict:
    if not path.is_file() or path.is_symlink():
        fail(".carryctx/config.toml must be a regular non-symlink file")
    try:
        with path.open("rb") as stream:
            value = tomllib.load(stream)
    except (OSError, tomllib.TOMLDecodeError) as exc:
        fail(f"cannot parse .carryctx/config.toml: {exc}")
    if not isinstance(value, dict):
        fail(".carryctx/config.toml is not a TOML table")
    project = value.get("project")
    git = value.get("git")
    if not isinstance(project, dict) or project.get("name") != "mathen":
        fail("configured CarryCtx project name is not mathen")
    if not isinstance(project.get("id"), str) or not project["id"]:
        fail("configured CarryCtx project id is missing")
    if not isinstance(git, dict) or not isinstance(git.get("main_branch"), str):
        fail("configured CarryCtx main branch is missing")
    branch = git["main_branch"]
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]{0,99}", branch):
        fail("configured CarryCtx main branch is invalid")
    return value


def manifest(path: Path, project_id: str) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        fail(f"malformed manifest: {exc}")
    if not isinstance(value, dict):
        fail("manifest must be a JSON object")
    if value.get("redacted") is not True:
        fail("manifest redacted must be boolean true")
    if value.get("format") != FORMAT or value.get("format_version") != 2:
        fail("manifest format is not carryctx-pack-dir v2")
    if not isinstance(value.get("export_id"), str) or not re.fullmatch(
        r"[0-9A-Z]{26}", value["export_id"]
    ):
        fail("manifest export_id is invalid")
    if value.get("project_id") != project_id:
        fail("manifest project identity does not match local Mathen")
    if value.get("schema_version") != SCHEMA:
        fail(f"manifest schema_version is not {SCHEMA}")
    carryctx_version = value.get("carryctx_version")
    if not isinstance(carryctx_version, str) or CLI.fullmatch(carryctx_version) is None:
        fail("manifest CarryCtx version is below or incompatible with 0.12.0")
    source_data = value.get("source")
    if (
        not isinstance(source_data, dict)
        or not isinstance(source_data.get("git_commit"), str)
        or not re.fullmatch(r"[0-9a-f]{7,64}", source_data["git_commit"])
    ):
        fail("manifest source git_commit is missing or malformed")
    return value


def source(value: str) -> str:
    match = SOURCE.fullmatch(value)
    if not match:
        fail(
            "CarryCtx-Source must be exactly mathen@<7-64 lowercase hex SHA> "
            "with an optional bounded branch"
        )
    return match.group(1)


def provenance(message: str, export_id: str) -> str:
    source_lines = [
        line.removeprefix("CarryCtx-Source: ")
        for line in message.splitlines()
        if line.startswith("CarryCtx-Source: ")
    ]
    export_lines = [
        line.removeprefix("CarryCtx-Export-Id: ")
        for line in message.splitlines()
        if line.startswith("CarryCtx-Export-Id: ")
    ]
    if len(source_lines) != 1 or len(export_lines) != 1:
        fail("publication provenance trailers are missing or duplicated")
    if export_lines[0] != export_id:
        fail("CarryCtx-Export-Id does not match manifest")
    return source(source_lines[0])


def _table_names(db: sqlite3.Connection) -> list[str]:
    rows = db.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name NOT LIKE 'sqlite_%' ORDER BY name"
    ).fetchall()
    names = [row[0] for row in rows]
    if not names:
        fail("CarryCtx state database has no tables")
    return names


def db_state(path: Path, project_id: str, project_root: Path, common_dir: Path) -> dict:
    if not path.exists():
        return {
            "exists": False,
            "project_id": None,
            "durable_rows": 0,
            "data_rows": 0,
            "table_counts": {},
            "active": [],
        }
    if path.is_symlink() or not path.is_file():
        fail("CarryCtx state.sqlite must be a regular file")
    try:
        db = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        db.execute("PRAGMA query_only=ON")
        db.execute("PRAGMA foreign_keys=ON")
        integrity = db.execute("PRAGMA integrity_check").fetchone()
        if integrity != ("ok",):
            fail("CarryCtx state database integrity check failed")
        names = _table_names(db)
        required = {"projects", "sessions", "operations", "schema_migrations"}
        missing = sorted(required - set(names))
        if missing:
            fail(
                "CarryCtx state database is missing required tables: "
                f"{','.join(missing)}"
            )
        migration = db.execute(
            "SELECT MIN(version), MAX(version), COUNT(*) FROM schema_migrations"
        ).fetchone()
        if migration != (1, SCHEMA, SCHEMA):
            fail("CarryCtx schema migration state is incomplete or unexpected")
        rows = db.execute(
            "SELECT id, repository_root, git_common_dir, main_branch, "
            "schema_version FROM projects"
        ).fetchall()
        if len(rows) > 1:
            fail("CarryCtx state database contains multiple projects")
        local_id = rows[0][0] if rows else None
        if rows and rows[0][4] != 4:
            fail("CarryCtx project schema_version is unexpected")
        expected_repository_root = common_dir.resolve().parent
        if rows and (
            local_id != project_id
            or Path(rows[0][1]).resolve() != expected_repository_root
            or Path(rows[0][2]).resolve() != common_dir.resolve()
        ):
            fail("CarryCtx state database identity does not match this Mathen checkout")
        durable = 0
        data_rows = 0
        table_counts: dict[str, int] = {}
        for name in names:
            if (
                name.endswith("_fts")
                or name.endswith("_fts_config")
                or name.endswith("_fts_content")
                or name.endswith("_fts_data")
                or name.endswith("_fts_docsize")
                or name.endswith("_fts_idx")
                or name == "schema_migrations"
            ):
                continue
            try:
                count = db.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            except sqlite3.DatabaseError as exc:
                fail(f"cannot count CarryCtx table {name}: {exc}")
            if not isinstance(count, int):
                fail(f"invalid count for CarryCtx table {name}")
            table_counts[name] = count
            durable += count
            if name != "projects":
                data_rows += count
        if not rows and data_rows:
            fail("CarryCtx state database has durable rows but no project identity")
        active: list[str] = []
        for row in db.execute(
            "SELECT id FROM sessions WHERE state IN ('active','paused')"
        ):
            active.append(f"session:{row[0]}")
        for row in db.execute("SELECT id FROM operations WHERE state = 'prepared'"):
            active.append(f"operation:{row[0]}")
        if "tasks" in names:
            for row in db.execute(
                "SELECT id FROM tasks "
                "WHERE status IN ('in_progress','review','blocked')"
            ):
                active.append(f"task:{row[0]}")
        if "worktree_cleanup_requests" in names:
            for row in db.execute(
                "SELECT id FROM worktree_cleanup_requests WHERE state = 'running'"
            ):
                active.append(f"cleanup:{row[0]}")
        return {
            "exists": True,
            "project_id": local_id,
            "durable_rows": durable,
            "data_rows": data_rows,
            "table_counts": table_counts,
            "active": active,
        }
    except sqlite3.Error as exc:
        fail(f"cannot inspect CarryCtx state database: {exc}")
    finally:
        try:
            db.close()
        except UnboundLocalError:
            pass


def capability(payload: dict) -> None:
    try:
        versions = payload["data"]["contract_versions"]
        cli = CLI.fullmatch(versions["cli"])
        if cli is None or versions["db_schema"] != SCHEMA:
            fail(
                "installed CarryCtx capability/version is below or incompatible "
                "with 0.12.0/schema 18"
            )
        if versions["ctxpack_format"] != {"format": FORMAT, "format_version": 2}:
            fail("installed CarryCtx pack capability is not carryctx-pack-dir v2")
    except (KeyError, TypeError):
        fail("installed CarryCtx version response is malformed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=(
            "config",
            "manifest",
            "manifest-source",
            "source",
            "provenance",
            "db",
            "capability",
        ),
    )
    parser.add_argument("args", nargs="*")
    ns = parser.parse_args()
    if ns.command == "config":
        value = load_config(Path(ns.args[0]))
        print(value["git"]["main_branch"])
    elif ns.command == "manifest":
        value = manifest(Path(ns.args[0]), ns.args[1])
        print(value["export_id"])
    elif ns.command == "manifest-source":
        value = manifest(Path(ns.args[0]), ns.args[1])
        print(value["source"]["git_commit"])
    elif ns.command == "source":
        print(source(ns.args[0]))
    elif ns.command == "provenance":
        print(provenance(Path(ns.args[0]).read_text(encoding="utf-8"), ns.args[1]))
    elif ns.command == "db":
        result = db_state(
            Path(ns.args[0]), ns.args[1], Path(ns.args[2]), Path(ns.args[3])
        )
        print(json.dumps(result, sort_keys=True))
    else:
        capability(json.loads(Path(ns.args[0]).read_text(encoding="utf-8")))
        print("ok")


if __name__ == "__main__":
    main()

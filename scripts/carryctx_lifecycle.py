#!/usr/bin/env python3
"""Run deterministic verification and safely complete CarryCtx tasks.

CarryCtx currently exposes verification commands and Git hooks, but does not
invoke project verification as part of ``task complete``.  This module is the
repository-owned, fail-closed adapter for that gap.  It never removes a
worktree, branch, or file; cleanup remains CarryCtx's gated operation.
"""

from __future__ import annotations

import argparse
import json
import os
import shlex
import subprocess
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

EXIT_USAGE = 2
EXIT_VERIFICATION = 10
EXIT_UNSAFE = 11
EXIT_CARRYCTX = 12


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    output: str


def repository_root(start: Path) -> Path:
    """Return the Git root, refusing paths outside a repository."""

    result = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"],
        cwd=start,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError("not inside a Git repository; refusing external path")
    root = Path(result.stdout.strip()).resolve()
    if not (root / ".carryctx" / "config.toml").is_file():
        raise RuntimeError(
            f"{root} has no .carryctx/config.toml; refusing unmanaged repository"
        )
    return root


def _envelope(command: list[str], root: Path) -> dict[str, Any]:
    result = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise RuntimeError(
            f"{' '.join(command)} failed with exit {result.returncode}: {detail}"
        )
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"{' '.join(command)} returned invalid JSON: {exc}") from exc
    if not payload.get("success", False):
        raise RuntimeError(
            f"{' '.join(command)} returned an unsuccessful CarryCtx response: "
            f"{payload.get('error', payload)}"
        )
    return payload


def load_profiles(root: Path) -> dict[str, list[str]]:
    path = root / ".carryctx" / "verification.toml"
    try:
        with path.open("rb") as stream:
            raw = tomllib.load(stream)
    except (FileNotFoundError, tomllib.TOMLDecodeError) as exc:
        raise RuntimeError(f"cannot load verification policy {path}: {exc}") from exc

    profiles = raw.get("profiles")
    if not isinstance(profiles, dict):
        raise RuntimeError(f"{path} must define a [profiles] table")
    parsed: dict[str, list[str]] = {}
    for name, value in profiles.items():
        commands = value.get("commands") if isinstance(value, dict) else None
        if (
            not isinstance(commands, list)
            or not commands
            or not all(
                isinstance(command, str) and command.strip() for command in commands
            )
        ):
            raise RuntimeError(
                f"verification profile {name!r} must contain non-empty string commands"
            )
        parsed[name] = [command.strip() for command in commands]
    return parsed


def git_status(root: Path) -> list[str]:
    result = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=all"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"git status failed with exit {result.returncode}")
    return [line for line in result.stdout.splitlines() if line]


def carryctx_state(root: Path) -> dict[str, Any]:
    """Read lifecycle state without mutating CarryCtx SQLite."""

    worktrees = _envelope(["carryctx", "worktree", "list", "--json"], root)["data"]
    sessions = _envelope(["carryctx", "session", "list", "--json"], root)["data"]
    cleanup = _envelope(["carryctx", "worktree", "cleanup", "list", "--json"], root)[
        "data"
    ]
    managed = next(
        (item for item in worktrees if Path(item["path"]).resolve() == root), None
    )
    active_sessions = [
        item
        for item in sessions
        if item.get("state") in {"active", "paused"}
        and item.get("cwd")
        and Path(item["cwd"]).resolve() == root
    ]
    return {
        "managed_worktree": managed,
        "active_sessions": active_sessions,
        "cleanup_requests": [
            item
            for item in cleanup
            if item.get("state") not in {"completed", "cancelled"}
        ],
    }


def verify_profile(
    root: Path, profile: str, *, dry_run: bool = False
) -> list[CommandResult]:
    profiles = load_profiles(root)
    if profile not in profiles:
        available = ", ".join(sorted(profiles))
        raise RuntimeError(
            f"unknown verification profile {profile!r}; choose: {available}"
        )

    results: list[CommandResult] = []
    environment = os.environ.copy()
    environment.update({"CI": "1", "PYTHONUNBUFFERED": "1"})
    for command in profiles[profile]:
        if dry_run:
            result = CommandResult(command, 0, "dry-run: not executed")
        else:
            try:
                argv = shlex.split(command)
            except ValueError as exc:
                raise RuntimeError(
                    f"invalid command in verification profile {profile!r}: {exc}"
                ) from exc
            if not argv or any(
                token in {";", "&&", "||", "|", ">", "<"} for token in argv
            ):
                raise RuntimeError(
                    f"verification command must be a direct argv command: {command!r}"
                )
            completed = subprocess.run(
                argv,
                cwd=root,
                env=environment,
                check=False,
                text=True,
                capture_output=True,
            )
            output = (completed.stdout + completed.stderr).strip()
            result = CommandResult(command, completed.returncode, output)
            if output:
                print(output)
            if completed.returncode:
                results.append(result)
                return results
        results.append(result)
    return results


def audit(root: Path, task_ref: str | None = None) -> dict[str, Any]:
    state = carryctx_state(root)
    result: dict[str, Any] = {
        "path": str(root),
        "managed_worktree": state["managed_worktree"],
        "dirty": git_status(root),
        "active_sessions": state["active_sessions"],
        "pending_cleanup": state["cleanup_requests"],
        "action": "preserve; audit is read-only",
    }
    if task_ref:
        result["task"] = _envelope(
            ["carryctx", "task", "show", task_ref, "--json"], root
        )["data"]
    if result["managed_worktree"] is None:
        result["action"] = "preserve; path is unmanaged or external"
    elif result["dirty"]:
        result["action"] = "preserve; worktree is dirty"
    elif result["active_sessions"]:
        result["action"] = "preserve; active session blocks cleanup"
    return result


def complete(root: Path, task_ref: str, profile: str, *, dry_run: bool = False) -> int:
    state = carryctx_state(root)
    managed = state["managed_worktree"]
    if managed is None:
        print(
            "refusing completion: current path is not a CarryCtx-managed worktree; "
            "inspect with --audit and obtain explicit owner confirmation",
            file=sys.stderr,
        )
        return EXIT_UNSAFE

    dirty = git_status(root)
    if dirty:
        print(
            "refusing completion: worktree is dirty; preserve user files and "
            "commit or review them before retrying",
            file=sys.stderr,
        )
        for line in dirty:
            print(f"  {line}", file=sys.stderr)
        return EXIT_UNSAFE

    task = _envelope(["carryctx", "task", "show", task_ref, "--json"], root)["data"]
    if task.get("status") == "completed":
        print(f"{task_ref} is already completed; no dispatch or cleanup re-run")
        return 0

    if task.get("status") in {"cancelled", "blocked"}:
        print(
            f"refusing completion: {task_ref} has status {task.get('status')}; "
            "reopen or resolve it explicitly first",
            file=sys.stderr,
        )
        return EXIT_UNSAFE
    if task.get("status") not in {"in_progress", "review"}:
        print(
            f"refusing completion: {task_ref} has status {task.get('status')}; "
            "start or review the task explicitly first",
            file=sys.stderr,
        )
        return EXIT_UNSAFE

    if state["active_sessions"]:
        print(
            "notice: active session detected; completion may succeed, but cleanup "
            "must remain deferred until the session ends",
            file=sys.stderr,
        )

    print(f"verification profile: {profile}")
    results = verify_profile(root, profile, dry_run=dry_run)
    failed = next((result for result in results if result.returncode), None)
    if failed:
        print(
            f"verification failed: {failed.command} (exit {failed.returncode}); "
            "worktree preserved and task remains incomplete",
            file=sys.stderr,
        )
        return EXIT_VERIFICATION
    if dry_run:
        print(f"dry-run: would complete {task_ref}; no CarryCtx state changed")
        return 0

    after = git_status(root)
    if after:
        print(
            "refusing completion: verification changed the worktree; inspect and "
            "preserve the changes before retrying",
            file=sys.stderr,
        )
        return EXIT_UNSAFE

    completed = subprocess.run(
        ["carryctx", "task", "complete", task_ref, "--json"],
        cwd=root,
        check=False,
        text=True,
    )
    if completed.returncode:
        print(
            f"CarryCtx completion failed with exit {completed.returncode}; "
            "no cleanup retry was attempted",
            file=sys.stderr,
        )
        return EXIT_CARRYCTX
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("verify", "complete", "audit"))
    parser.add_argument("task_ref", nargs="?")
    parser.add_argument("--profile", default="full")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = repository_root(Path.cwd())
        if args.command == "audit":
            result: Any = audit(root, args.task_ref)
            if args.as_json:
                print(json.dumps(result, indent=2, sort_keys=True))
            else:
                print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "verify":
            results = verify_profile(root, args.profile, dry_run=args.dry_run)
            failed = next((item for item in results if item.returncode), None)
            return EXIT_VERIFICATION if failed else 0
        if not args.task_ref:
            print("complete requires a CarryCtx task reference", file=sys.stderr)
            return EXIT_USAGE
        return complete(root, args.task_ref, args.profile, dry_run=args.dry_run)
    except (OSError, RuntimeError) as exc:
        print(f"carryctx lifecycle refused: {exc}", file=sys.stderr)
        return EXIT_UNSAFE


if __name__ == "__main__":
    raise SystemExit(main())

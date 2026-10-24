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
EXIT_READBACK = 13
PR_STATES = frozenset(
    {"open", "merged", "closed", "draft", "absent", "local-only", "lookup-error"}
)
RETRYABLE_CLEANUP_STATES = frozenset({"pending", "failed", "blocked", "retryable"})
SAFE_RETRY_CLEANUP_STATES = frozenset({"pending", "failed", "retryable"})
LIFECYCLE_TRANSITIONS = {
    "ready": {"start": "in_progress"},
    "in_progress": {"submit_for_review": "review", "complete": "completed"},
    "review": {"complete": "completed", "reopen": "in_progress"},
    "completed": {"observe_cleanup": "cleanup_deferred"},
    "cleanup_deferred": {},
    "cancelled": {"reopen": "ready"},
    "blocked": {"unblock": "ready"},
}


@dataclass(frozen=True)
class CommandResult:
    command: str
    returncode: int
    output: str


@dataclass(frozen=True)
class PullRequestLookup:
    """Read-only result from the optional GitHub CLI lookup."""

    payload: dict[str, Any] | None
    candidates: list[dict[str, Any]]
    source: str
    error: str | None = None


def lifecycle_transition(state: str, event: str) -> str:
    """Apply one explicit, fail-closed task lifecycle transition."""

    try:
        return LIFECYCLE_TRANSITIONS[state][event]
    except KeyError as exc:
        raise RuntimeError(
            f"invalid lifecycle transition: state={state!r}, event={event!r}"
        ) from exc


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


def git_worktree_inventory(
    root: Path, managed: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Inventory Git worktrees without adopting or changing any of them."""

    result = subprocess.run(
        ["git", "worktree", "list", "--porcelain"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"git worktree list failed with exit {result.returncode}")

    records: list[dict[str, Any]] = []
    current: dict[str, Any] = {}
    for line in result.stdout.splitlines() + [""]:
        if not line:
            if current:
                records.append(current)
                current = {}
            continue
        key, _, value = line.partition(" ")
        if key == "worktree":
            current["path"] = value
        elif key == "HEAD":
            current["head"] = value
        elif key == "branch":
            current["branch"] = value.removeprefix("refs/heads/")
        elif key == "detached":
            current["detached"] = True
        elif key == "prunable":
            current["prunable"] = value or True

    managed_by_path = {
        str(Path(item["path"]).resolve()): item for item in managed if item.get("path")
    }
    inventory: list[dict[str, Any]] = []
    root = root.resolve()
    for record in records:
        path = Path(str(record["path"])).expanduser()
        resolved = path.resolve(strict=False)
        exists = path.exists()
        managed_item = managed_by_path.get(str(resolved))
        external = root not in resolved.parents and resolved != root
        detached = bool(record.get("detached")) or not record.get("branch")
        dirty: bool | None = None
        status: list[str] = []
        if exists:
            status = git_status(path)
            dirty = bool(status)
        elif not external:
            dirty = None
        labels = []
        if managed_item is not None:
            labels.append("managed")
        else:
            labels.append("unmanaged")
        if external:
            labels.append("external")
        if detached:
            labels.append("detached")
        if not exists:
            labels.append("missing")
        if dirty:
            labels.append("dirty")
        inventory.append(
            {
                "path": str(path),
                "resolved_path": str(resolved),
                "head": record.get("head"),
                "branch": record.get("branch"),
                "managed": managed_item is not None,
                "managed_record": managed_item,
                "external": external,
                "detached": detached,
                "missing": not exists,
                "dirty": dirty,
                "status": status,
                "prunable": "prunable" in record,
                "labels": labels,
            }
        )
    return sorted(inventory, key=lambda item: item["resolved_path"])


def git_prune_observation(root: Path) -> dict[str, Any]:
    """Observe Git's prune candidates without pruning worktree metadata."""

    command = ["git", "worktree", "prune", "--dry-run", "-v"]
    result = subprocess.run(
        command,
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(
            f"git worktree prune observation failed with exit {result.returncode}"
        )
    output = (result.stdout + result.stderr).splitlines()
    return {
        "command": command,
        "candidates": [line for line in output if line],
        "mutation_performed": False,
    }


def validate_branch_name(root: Path, branch: str) -> str:
    """Validate a branch name with Git before using it in any command."""

    if not branch or branch.startswith("-"):
        raise RuntimeError("branch name must be non-empty and must not start with '-'")
    result = subprocess.run(
        ["git", "check-ref-format", "--branch", branch],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
    )
    if result.returncode:
        raise RuntimeError(f"invalid Git branch name: {branch!r}")
    return branch


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
        "worktrees": worktrees,
        "sessions": sorted(sessions, key=lambda item: str(item.get("id", ""))),
        "active_sessions": sorted(
            active_sessions, key=lambda item: str(item.get("id", ""))
        ),
        "cleanup_requests": sorted(cleanup, key=lambda item: str(item.get("id", ""))),
        "pending_cleanup": [
            item
            for item in sorted(cleanup, key=lambda item: str(item.get("id", "")))
            if item.get("state") not in {"completed", "cancelled"}
        ],
    }


def cleanup_audit(requests: list[dict[str, Any]]) -> dict[str, Any]:
    """Return an audit-friendly, non-mutating cleanup outbox projection."""

    counts: dict[str, int] = {}
    pending: list[dict[str, Any]] = []
    retryable: list[dict[str, Any]] = []
    normalized: list[dict[str, Any]] = []
    for request in requests:
        state = str(request.get("state", request.get("status", "unknown")))
        counts[state] = counts.get(state, 0) + 1
        retryable_state = state in RETRYABLE_CLEANUP_STATES
        safe_to_retry = state in SAFE_RETRY_CLEANUP_STATES
        if state == "blocked":
            preservation_reason = str(
                request.get("blocked_reason")
                or "cleanup gate blocked; preserve the worktree and owner files"
            )
            operator_action = (
                "review the blocking gate and owner state, then retry with a dry-run"
            )
        elif state in {"pending", "failed", "retryable"}:
            preservation_reason = str(
                request.get("blocked_reason")
                or "cleanup remains deferred until all safety gates pass"
            )
            operator_action = (
                "run the cleanup dry-run; retry only after it reports safe"
            )
        elif state == "completed":
            preservation_reason = (
                "cleanup completed; retain the historical outbox record"
            )
            operator_action = "no action"
        elif state == "cancelled":
            preservation_reason = (
                "cleanup was cancelled; preserve the historical record"
            )
            operator_action = "no action unless an owner explicitly reopens the request"
        else:
            preservation_reason = "unknown cleanup state; preserve pending work"
            operator_action = "inspect the request before any retry"
        item = {
            **request,
            "state": state,
            "retryable": retryable_state,
            "safe_to_retry": safe_to_retry,
            "preservation_reason": preservation_reason,
            "operator_action": operator_action,
        }
        if state not in {"completed", "cancelled"}:
            pending.append(item)
        if retryable_state:
            retryable.append(item)
        normalized.append(item)
    return {
        "total": len(requests),
        "counts": dict(sorted(counts.items())),
        "requests": normalized,
        "pending": pending,
        "retryable": retryable,
        "retry_command": "carryctx worktree cleanup run --dry-run",
        "mutation_performed": False,
    }


def git_branch(root: Path, requested: str | None = None) -> dict[str, Any]:
    """Read the current or requested branch without changing Git metadata."""

    if requested:
        branch = requested
    else:
        result = subprocess.run(
            ["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
        branch = result.stdout.strip() if result.returncode == 0 else None

    if not branch:
        return {"name": None, "local": False, "detached": True}

    validate_branch_name(root, branch)

    result = subprocess.run(
        ["git", "show-ref", "--verify", "--quiet", f"refs/heads/{branch}"],
        cwd=root,
        check=False,
    )
    return {"name": branch, "local": result.returncode == 0, "detached": False}


def classify_pr_state(
    payload: dict[str, Any] | None,
    *,
    local_branch: bool,
    lookup_error: str | None = None,
) -> str:
    """Classify a PR payload, distinguishing a local-only branch from absence."""

    if lookup_error:
        return "lookup-error"
    if payload is not None:
        state = str(payload.get("state", "")).upper()
        if payload.get("isDraft") is True and state == "OPEN":
            return "draft"
        if state == "OPEN":
            return "open"
        if state == "MERGED" or payload.get("mergedAt"):
            return "merged"
        if state == "CLOSED":
            return "closed"
        return "lookup-error"
    return "local-only" if local_branch else "absent"


def lookup_pull_request(root: Path, branch: str) -> PullRequestLookup:
    """Look up PRs with ``gh`` using a read-only command and no credentials in code."""

    validate_branch_name(root, branch)

    command = [
        "gh",
        "pr",
        "list",
        "--head",
        branch,
        "--state",
        "all",
        "--limit",
        "20",
        "--json",
        "number,state,isDraft,mergedAt,url,headRefName,baseRefName",
    ]
    try:
        result = subprocess.run(
            command,
            cwd=root,
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError as exc:
        return PullRequestLookup(None, [], "github-cli", str(exc))
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        return PullRequestLookup(
            None,
            [],
            "github-cli",
            detail or f"gh exited with status {result.returncode}",
        )
    try:
        raw = json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        return PullRequestLookup(None, [], "github-cli", f"invalid gh JSON: {exc}")
    if not isinstance(raw, list):
        return PullRequestLookup(
            None, [], "github-cli", "gh returned a non-list PR result"
        )
    candidates = [item for item in raw if isinstance(item, dict)]
    candidates.sort(key=lambda item: int(item.get("number", 0)), reverse=True)
    return PullRequestLookup(
        candidates[0] if candidates else None,
        candidates,
        "github-cli",
    )


def cleanup_eligibility(
    pr_state: str,
    *,
    local_deliverable: bool = False,
    lookup_error: str | None = None,
    detached: bool = False,
    managed: bool = True,
    external: bool = False,
    clean: bool | None = None,
    no_active_session: bool | None = None,
    task_completed: bool | None = None,
) -> dict[str, Any]:
    """Return a deterministic, fail-closed cleanup eligibility decision.

    This function only describes policy.  It never removes a worktree, branch,
    file, or CarryCtx record.  A local-only deliverable requires the explicit
    ``local_deliverable`` policy switch; a lookup error is never absence.
    """

    gates: dict[str, Any] = {
        "pr_state": pr_state,
        "merged_or_explicit_local_deliverable": pr_state == "merged"
        or (pr_state == "local-only" and local_deliverable),
        "clean": clean,
        "no_active_session": no_active_session,
        "task_completed": task_completed,
        "managed": managed,
        "external": external,
        "detached": detached,
        "lookup_confirmed": lookup_error is None,
    }
    if lookup_error:
        reason = "GitHub PR lookup failed; preserve because absence was not proven"
    elif detached:
        reason = "detached worktree has no validated branch owner; preserve"
    elif external:
        reason = "external worktree requires explicit owner confirmation; preserve"
    elif not managed:
        reason = "unmanaged worktree is not eligible for automated cleanup; preserve"
    elif pr_state in {"open", "draft", "closed", "absent"}:
        reason = f"PR state {pr_state!r} is not cleanup-eligible; preserve"
    elif pr_state == "local-only" and not local_deliverable:
        reason = "local-only cleanup requires the explicit local-deliverable policy"
    elif pr_state not in {"merged", "local-only"}:
        reason = f"unknown PR state {pr_state!r}; preserve"
    elif clean is not True:
        reason = "worktree cleanliness is not confirmed; preserve"
    elif no_active_session is not True:
        reason = "active-session gate is not confirmed; preserve"
    elif task_completed is not True:
        reason = "task completion gate is not confirmed; preserve"
    else:
        reason = "PR and cleanup gates are confirmed; cleanup may be considered"
    eligible_pr = pr_state == "merged" or (
        pr_state == "local-only" and local_deliverable
    )
    eligible = (
        (not lookup_error and not detached and not external and managed and eligible_pr)
        and clean is True
        and no_active_session is True
        and task_completed is True
    )
    return {
        "eligible": eligible,
        "decision": "eligible" if eligible else "preserve",
        "preserve": not eligible,
        "delete_branch": "never",
        "preservation_reason": None if eligible else reason,
        "operator_action": (
            "run the separately reviewed CarryCtx cleanup dry-run"
            if eligible
            else "preserve; resolve the stated gate or obtain explicit owner review"
        ),
        "gates": gates,
    }


def branch_policy(
    pr_state: str,
    *,
    lookup_error: str | None = None,
    local_deliverable: bool = False,
    detached: bool = False,
    managed: bool = True,
    external: bool = False,
    clean: bool | None = None,
    no_active_session: bool | None = None,
    task_completed: bool | None = None,
) -> dict[str, Any]:
    """Describe branch preservation and cleanup eligibility; never delete."""

    eligibility = cleanup_eligibility(
        pr_state,
        local_deliverable=local_deliverable,
        lookup_error=lookup_error,
        detached=detached,
        managed=managed,
        external=external,
        clean=clean,
        no_active_session=no_active_session,
        task_completed=task_completed,
    )
    return {
        "preserve_branch": True,
        "delete_branch": "never",
        "merge_confirmed": pr_state == "merged" and lookup_error is None,
        **eligibility,
        "reason": eligibility["preservation_reason"]
        or "merged PR confirmed and all cleanup gates passed",
    }


def observe(
    root: Path, branch: str | None = None, *, dry_run: bool = False
) -> dict[str, Any]:
    """Build a deterministic PR, branch, and cleanup observability report."""

    branch_info = git_branch(root, branch)
    name = branch_info["name"]
    lookup = (
        lookup_pull_request(root, name)
        if name and name != "main"
        else PullRequestLookup(None, [], "not-applicable")
    )
    pr_state = classify_pr_state(
        lookup.payload,
        local_branch=branch_info["local"],
        lookup_error=lookup.error,
    )
    state = carryctx_state(root)
    cleanup = cleanup_audit(state["cleanup_requests"])
    dirty = git_status(root)
    managed = state["managed_worktree"] is not None
    report: dict[str, Any] = {
        "schema_version": 1,
        "mode": "dry-run" if dry_run else "read-only",
        "path": str(root),
        "branch": {**branch_info, "pr_state": pr_state},
        "pull_request": {
            "state": pr_state,
            "source": lookup.source,
            "error": lookup.error,
            "selected": lookup.payload,
            "candidates": lookup.candidates,
        },
        "branch_policy": branch_policy(
            pr_state,
            lookup_error=lookup.error,
            detached=branch_info["detached"],
            managed=managed,
            clean=not dirty,
            no_active_session=not state["active_sessions"],
        ),
        "cleanup": cleanup,
        "action": "preserve; observation is read-only and no cleanup was requested",
    }
    return report


def verify_profile(
    root: Path, profile: str, *, dry_run: bool = False, emit_output: bool = True
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
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise RuntimeError(
                f"invalid command in verification profile {profile!r}: {exc}"
            ) from exc
        if not argv or any(token in {";", "&&", "||", "|", ">", "<"} for token in argv):
            raise RuntimeError(
                f"verification command must be a direct argv command: {command!r}"
            )
        if dry_run:
            result = CommandResult(command, 0, "dry-run: not executed")
        else:
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
            if output and emit_output:
                print(output)
            if completed.returncode:
                results.append(result)
                return results
        results.append(result)
    return results


def verification_report(
    root: Path, profile: str, *, dry_run: bool = False
) -> dict[str, Any]:
    """Return stable profile, argv, and projected-result verification data."""

    commands = load_profiles(root).get(profile)
    if commands is None:
        available = ", ".join(sorted(load_profiles(root)))
        raise RuntimeError(
            f"unknown verification profile {profile!r}; choose: {available}"
        )
    entries = []
    for command in commands:
        try:
            argv = shlex.split(command)
        except ValueError as exc:
            raise RuntimeError(
                f"invalid command in verification profile {profile!r}: {exc}"
            ) from exc
        if not argv or any(token in {";", "&&", "||", "|", ">", "<"} for token in argv):
            raise RuntimeError(
                f"verification command must be a direct argv command: {command!r}"
            )
        entries.append(
            {
                "command": command,
                "argv": argv,
                "projected_result": "not-executed" if dry_run else "pending",
            }
        )
    return {
        "schema_version": 1,
        "mode": "dry-run" if dry_run else "execution",
        "profile": profile,
        "commands": entries,
        "projected_result": {
            "status": "pass" if dry_run else "pending",
            "exit_code": 0 if dry_run else None,
            "completion_dispatched": False,
            "worktree_mutated": False,
        },
    }


def _gate(name: str, passed: bool, reason: str | None = None) -> dict[str, Any]:
    """Return the stable shape used for completion gate evidence."""

    return {
        "name": name,
        "passed": passed,
        "reason": reason,
    }


def _completion_gate_report(
    root: Path,
    state: dict[str, Any],
    task: dict[str, Any] | None,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Observe completion gates without changing Git or CarryCtx state."""

    managed = state.get("managed_worktree")
    dirty = git_status(root)
    active_sessions = state.get("active_sessions", [])
    branch = git_branch(root)
    detached = branch["detached"] or bool(
        isinstance(managed, dict) and "branch" in managed and not managed.get("branch")
    )
    gates = [
        _gate(
            "managed",
            managed is not None,
            None
            if managed is not None
            else "current path is not a CarryCtx-managed worktree",
        ),
        _gate(
            "detached",
            not detached,
            None
            if not detached
            else "current worktree is detached and has no branch owner",
        ),
        _gate(
            "clean",
            not dirty,
            None if not dirty else "worktree contains uncommitted changes",
        ),
        _gate(
            "no-active-session",
            not active_sessions,
            None
            if not active_sessions
            else "an active CarryCtx session owns this worktree",
        ),
    ]
    if task is not None:
        status = task.get("status")
        gates.append(
            _gate(
                "task-active",
                status in {"in_progress", "review"},
                None
                if status in {"in_progress", "review"}
                else f"task status is {status!r}; expected in_progress or review",
            )
        )
    failures = [gate["name"] for gate in gates if not gate["passed"]]
    return gates, failures


def completion_evidence(
    root: Path,
    task_ref: str,
    profile: str,
    *,
    dry_run: bool = False,
    dispatch: bool = True,
    emit_output: bool = False,
) -> tuple[int, dict[str, Any]]:
    """Run verified completion and return stable, machine-readable evidence.

    The function is deliberately repository-owned: it observes all gates again
    after verification and dispatches CarryCtx only when every gate passes. It
    never performs cleanup, edits Git metadata, or resets files.
    """

    state_before = carryctx_state(root)
    task: dict[str, Any] | None = None
    if state_before.get("managed_worktree") is not None:
        task = _envelope(["carryctx", "task", "show", task_ref, "--json"], root)["data"]

    before_gates, before_failures = _completion_gate_report(root, state_before, task)
    evidence: dict[str, Any] = {
        "schema_version": 2,
        "command": "complete-verified",
        "mode": "dry-run" if dry_run else "execution",
        "path": str(root),
        "task_ref": task_ref,
        "profile": profile,
        "task_before": task,
        "gates_before": before_gates,
        "verification": None,
        "gates_after": [],
        "dispatch": {
            "attempted": False,
            "command": ["carryctx", "task", "complete", task_ref, "--json"],
            "returncode": None,
            "readback": {
                "attempted": False,
                "command": ["carryctx", "task", "show", task_ref, "--json"],
                "task": None,
            },
        },
        "mutation_performed": False,
        "status": "refused" if before_failures else "pending",
        "failure_reasons": before_failures,
    }

    if task is not None and task.get("status") == "completed":
        evidence["status"] = "already-completed"
        evidence["failure_reasons"] = []
        return 0, evidence
    if before_failures:
        return EXIT_UNSAFE, evidence

    results = verify_profile(root, profile, dry_run=dry_run, emit_output=emit_output)
    verification = verification_report(root, profile, dry_run=dry_run)
    for entry, result in zip(verification["commands"], results, strict=False):
        entry["returncode"] = result.returncode
        entry["output"] = result.output
        entry["projected_result"] = "pass" if result.returncode == 0 else "fail"
    failed = next((result for result in results if result.returncode), None)
    verification["projected_result"] = {
        "status": "fail" if failed else "pass",
        "exit_code": failed.returncode if failed else 0,
        "completion_dispatched": False,
        "worktree_mutated": False,
    }
    evidence["verification"] = verification
    if failed:
        evidence["status"] = "verification-failed"
        evidence["failure_reasons"] = ["verification"]
        return EXIT_VERIFICATION, evidence

    state_after = carryctx_state(root)
    task_after = task
    if state_after.get("managed_worktree") is not None:
        task_after = _envelope(["carryctx", "task", "show", task_ref, "--json"], root)[
            "data"
        ]
    after_gates, after_failures = _completion_gate_report(root, state_after, task_after)
    evidence["task_after"] = task_after
    evidence["gates_after"] = after_gates
    evidence["failure_reasons"] = after_failures
    if after_failures:
        evidence["status"] = "refused"
        return EXIT_UNSAFE, evidence
    if dry_run or not dispatch:
        evidence["status"] = "would-complete"
        return 0, evidence

    evidence["dispatch"]["attempted"] = True
    completed = subprocess.run(
        evidence["dispatch"]["command"], cwd=root, check=False, text=True
    )
    evidence["dispatch"]["returncode"] = completed.returncode
    if completed.returncode:
        evidence["status"] = "carryctx-failed"
        evidence["failure_reasons"] = ["carryctx-completion"]
        return EXIT_CARRYCTX, evidence

    readback = evidence["dispatch"]["readback"]
    readback["attempted"] = True
    try:
        readback["task"] = _envelope(readback["command"], root)["data"]
    except (KeyError, OSError, RuntimeError, TypeError) as exc:
        readback["error"] = str(exc)
        evidence["status"] = "completion-readback-failed"
        evidence["failure_reasons"] = ["completion-readback"]
        return EXIT_READBACK, evidence
    if readback["task"].get("status") != "completed":
        evidence["status"] = "completion-readback-failed"
        evidence["failure_reasons"] = ["completion-readback"]
        return EXIT_READBACK, evidence

    evidence["dispatch"]["completed"] = True
    evidence["status"] = "completed"
    evidence["mutation_performed"] = True
    return 0, evidence


def audit(
    root: Path,
    task_ref: str | None = None,
    *,
    all_worktrees: bool = False,
    observe_prune: bool = True,
) -> dict[str, Any]:
    state = carryctx_state(root)
    result: dict[str, Any] = {
        "schema_version": 1,
        "path": str(root),
        "managed_worktree": state["managed_worktree"],
        "dirty": git_status(root),
        "active_sessions": state["active_sessions"],
        "pending_cleanup": state["pending_cleanup"],
        "sessions": state["sessions"],
        "cleanup": cleanup_audit(state["cleanup_requests"]),
        "mutation_performed": False,
        "action": "preserve; audit is read-only",
    }
    if all_worktrees:
        result["worktrees"] = git_worktree_inventory(root, state["worktrees"])
        result["prune_observation"] = (
            git_prune_observation(root) if observe_prune else None
        )
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

    managed_branch = managed.get("branch") if isinstance(managed, dict) else None
    if "branch" in managed and not managed_branch:
        print(
            "refusing completion: detached HEAD has no validated branch owner; "
            "check out the task branch explicitly",
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
    parser.add_argument(
        "command",
        choices=("verify", "complete", "complete-verified", "audit", "observe"),
        help=(
            "complete-verified is the recommended repository-owned wrapper; "
            "complete is retained for compatibility"
        ),
    )
    parser.add_argument("task_ref", nargs="?")
    parser.add_argument(
        "--branch", help="branch to observe instead of the current branch"
    )
    parser.add_argument("--profile", default="full")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--all",
        action="store_true",
        dest="all_worktrees",
        help="audit every Git worktree instead of only the current path",
    )
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        root = repository_root(Path.cwd())
        if args.command == "audit":
            result: Any = audit(root, args.task_ref, all_worktrees=args.all_worktrees)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "observe":
            result = observe(root, args.branch, dry_run=args.dry_run)
            print(json.dumps(result, indent=2, sort_keys=True))
            return 0
        if args.command == "verify":
            if args.dry_run:
                print(
                    json.dumps(
                        verification_report(root, args.profile, dry_run=args.dry_run),
                        indent=2,
                        sort_keys=True,
                    )
                )
                return 0
            results = verify_profile(root, args.profile, dry_run=args.dry_run)
            if args.as_json:
                report = verification_report(root, args.profile)
                for entry, result in zip(report["commands"], results, strict=False):
                    entry["returncode"] = result.returncode
                    entry["output"] = result.output
                    entry["projected_result"] = (
                        "pass" if result.returncode == 0 else "fail"
                    )
                failed = next((item for item in results if item.returncode), None)
                report["projected_result"] = {
                    "status": "fail" if failed else "pass",
                    "exit_code": failed.returncode if failed else 0,
                    "completion_dispatched": False,
                    "worktree_mutated": False,
                }
                print(json.dumps(report, indent=2, sort_keys=True))
                return EXIT_VERIFICATION if failed else 0
            failed = next((item for item in results if item.returncode), None)
            return EXIT_VERIFICATION if failed else 0
        if not args.task_ref:
            print("complete requires a CarryCtx task reference", file=sys.stderr)
            return EXIT_USAGE
        if args.command == "complete-verified":
            exit_code, evidence = completion_evidence(
                root, args.task_ref, args.profile, dry_run=args.dry_run
            )
            print(json.dumps(evidence, indent=2, sort_keys=True))
            return exit_code
        return complete(root, args.task_ref, args.profile, dry_run=args.dry_run)
    except (OSError, RuntimeError) as exc:
        print(f"carryctx lifecycle refused: {exc}", file=sys.stderr)
        return EXIT_UNSAFE


if __name__ == "__main__":
    raise SystemExit(main())

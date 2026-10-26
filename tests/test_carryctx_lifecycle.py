import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).parents[1] / "scripts" / "carryctx_lifecycle.py"
SPEC = importlib.util.spec_from_file_location("carryctx_lifecycle", SCRIPT)
assert SPEC and SPEC.loader
LIFECYCLE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = LIFECYCLE
SPEC.loader.exec_module(LIFECYCLE)


class LifecyclePolicyTests(unittest.TestCase):
    def test_lifecycle_state_machine_is_explicit_and_fail_closed(self):
        self.assertEqual(
            LIFECYCLE.lifecycle_transition("ready", "start"), "in_progress"
        )
        self.assertEqual(
            LIFECYCLE.lifecycle_transition("completed", "observe_cleanup"),
            "cleanup_deferred",
        )
        with self.assertRaisesRegex(RuntimeError, "invalid lifecycle transition"):
            LIFECYCLE.lifecycle_transition("completed", "complete")

    def test_pull_request_states_are_deterministic(self):
        cases = (
            ({"state": "OPEN"}, False, "open"),
            ({"state": "OPEN", "isDraft": True}, False, "draft"),
            ({"state": "MERGED"}, False, "merged"),
            ({"state": "CLOSED"}, False, "closed"),
            ({"state": "CLOSED", "isDraft": True}, False, "closed"),
            (None, True, "local-only"),
            (None, False, "absent"),
        )
        for payload, local_branch, expected in cases:
            with self.subTest(expected=expected):
                self.assertEqual(
                    LIFECYCLE.classify_pr_state(payload, local_branch=local_branch),
                    expected,
                )

    def test_branch_policy_never_authorizes_deletion(self):
        for state in LIFECYCLE.PR_STATES:
            with self.subTest(state=state):
                policy = LIFECYCLE.branch_policy(state)
                self.assertTrue(policy["preserve_branch"])
                self.assertEqual(policy["delete_branch"], "never")
                self.assertEqual(policy["decision"], "preserve")

    def test_cleanup_audit_exposes_retryable_requests_without_mutation(self):
        requests = [
            {"id": "done", "state": "completed"},
            {"id": "blocked", "state": "blocked", "attempt_count": 4},
            {"id": "pending", "state": "pending"},
            {"id": "cancelled", "state": "cancelled"},
        ]

        report = LIFECYCLE.cleanup_audit(requests)

        self.assertEqual(
            report["counts"],
            {"blocked": 1, "cancelled": 1, "completed": 1, "pending": 1},
        )
        self.assertEqual(
            [item["id"] for item in report["pending"]], ["blocked", "pending"]
        )
        self.assertEqual(
            [item["id"] for item in report["retryable"]], ["blocked", "pending"]
        )
        self.assertFalse(report["mutation_performed"])

    def test_failed_github_lookup_is_preservation_signal(self):
        completed = type(
            "Completed", (), {"returncode": 1, "stdout": "", "stderr": "not logged in"}
        )()
        validation = type(
            "Completed", (), {"returncode": 0, "stdout": "", "stderr": ""}
        )()
        with patch.object(
            LIFECYCLE.subprocess,
            "run",
            side_effect=[validation, completed],
        ) as run:
            lookup = LIFECYCLE.lookup_pull_request(Path.cwd(), "carryctx/mth-1")

        self.assertEqual(lookup.source, "github-cli")
        self.assertEqual(lookup.error, "not logged in")
        self.assertEqual(lookup.candidates, [])
        self.assertEqual(run.call_count, 2)
        self.assertEqual(
            LIFECYCLE.classify_pr_state(
                lookup.payload, local_branch=True, lookup_error=lookup.error
            ),
            "lookup-error",
        )
        self.assertEqual(
            LIFECYCLE.branch_policy("lookup-error", lookup_error=lookup.error)[
                "decision"
            ],
            "preserve",
        )

    def test_invalid_branch_name_is_rejected_before_lookup(self):
        with self.assertRaisesRegex(RuntimeError, "invalid Git branch"):
            LIFECYCLE.validate_branch_name(Path.cwd(), "bad branch")

    def test_cleanup_eligibility_requires_confirmed_pr_and_all_gates(self):
        base = dict(clean=True, no_active_session=True, task_completed=True)
        merged = LIFECYCLE.cleanup_eligibility("merged", **base)
        self.assertTrue(merged["eligible"])
        local = LIFECYCLE.cleanup_eligibility("local-only", **base)
        self.assertFalse(local["eligible"])
        local = LIFECYCLE.cleanup_eligibility(
            "local-only", local_deliverable=True, **base
        )
        self.assertTrue(local["eligible"])
        lookup_error = LIFECYCLE.cleanup_eligibility(
            "lookup-error", lookup_error="offline", **base
        )
        self.assertFalse(lookup_error["eligible"])
        self.assertIn("not proven", lookup_error["preservation_reason"])

    def test_cleanup_orchestration_preserves_every_pr_and_worktree_safety_state(self):
        cases = (
            ("open", {"state": "OPEN"}, {}, False, "open"),
            ("draft", {"state": "OPEN", "isDraft": True}, {}, False, "draft"),
            ("merged", {"state": "MERGED"}, {}, True, "merged"),
            ("closed", {"state": "CLOSED"}, {}, False, "closed"),
            ("lookup-error", None, {"error": "offline"}, False, "lookup-error"),
            ("absent", None, {"local": False}, False, "absent"),
            ("local-only", None, {"local": True}, False, "local-only"),
            ("unmanaged", {"state": "MERGED"}, {"managed": False}, False, "merged"),
            ("external", {"state": "MERGED"}, {"external": True}, False, "merged"),
            ("detached", {"state": "MERGED"}, {"detached": True}, False, "absent"),
            ("dirty", {"state": "MERGED"}, {"dirty": True}, False, "merged"),
            ("active", {"state": "MERGED"}, {"active": True}, False, "merged"),
        )
        for name, payload, options, expected_eligible, expected_state in cases:
            with self.subTest(name=name):
                path = f"/repo/{name}"
                request = {
                    "id": name,
                    "state": "pending",
                    "branch": f"carryctx/{name}",
                    "task_status": "completed",
                    "worktree_path": path,
                }
                worktree = {
                    "resolved_path": path,
                    "path": path,
                    "branch": request["branch"],
                    "managed": options.get("managed", True),
                    "external": options.get("external", False),
                    "detached": options.get("detached", False),
                    "missing": not options.get("local", True),
                    "dirty": options.get("dirty", False),
                }
                state = {
                    "cleanup_requests": [request],
                    "worktrees": [{"path": path}],
                    "sessions": (
                        [{"id": "s1", "state": "active", "cwd": path}]
                        if options.get("active")
                        else []
                    ),
                }
                lookup = LIFECYCLE.PullRequestLookup(
                    payload,
                    [payload] if payload else [],
                    "github-cli",
                    options.get("error"),
                )
                with (
                    patch.object(LIFECYCLE, "carryctx_state", return_value=state),
                    patch.object(
                        LIFECYCLE, "git_worktree_inventory", return_value=[worktree]
                    ),
                    patch.object(
                        LIFECYCLE, "lookup_pull_request", return_value=lookup
                    ) as lookup_pr,
                    patch.object(LIFECYCLE.subprocess, "run") as run,
                ):
                    report = LIFECYCLE.cleanup_orchestration(
                        Path("/repo"), worktree_path=path
                    )

                item = report["requests"][0]
                self.assertEqual(item["pull_request"]["state"], expected_state)
                self.assertEqual(item["eligibility"]["eligible"], expected_eligible)
                self.assertEqual(item["branch_policy"]["delete_branch"], "never")
                self.assertFalse(report["native_cleanup_dispatched"])
                self.assertFalse(report["mutation_performed"])
                run.assert_not_called()
                if options.get("detached"):
                    lookup_pr.assert_not_called()

    def test_cleanup_orchestration_confirmation_is_preview_only(self):
        path = "/repo/merged"
        request = {
            "id": "merged-request",
            "state": "pending",
            "branch": "carryctx/merged",
            "task_status": "completed",
            "worktree_path": path,
        }
        state = {
            "cleanup_requests": [request],
            "worktrees": [{"path": path}],
            "sessions": [],
        }
        worktree = {
            "resolved_path": path,
            "path": path,
            "branch": request["branch"],
            "managed": True,
            "external": False,
            "detached": False,
            "missing": False,
            "dirty": False,
        }
        lookup = LIFECYCLE.PullRequestLookup(
            {"state": "MERGED"}, [{"state": "MERGED"}], "github-cli"
        )
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_worktree_inventory", return_value=[worktree]),
            patch.object(LIFECYCLE, "lookup_pull_request", return_value=lookup),
            patch.object(LIFECYCLE.subprocess, "run") as run,
        ):
            preview = LIFECYCLE.cleanup_orchestration(Path("/repo"))
            confirmed = LIFECYCLE.cleanup_orchestration(
                Path("/repo"), confirm=True, dry_run=False
            )

        self.assertTrue(preview["confirmation"]["required"])
        self.assertEqual(preview["mode"], "dry-run")
        self.assertFalse(confirmed["confirmation"]["required"])
        self.assertTrue(confirmed["confirmation"]["requested"])
        self.assertEqual(confirmed["mode"], "policy-preview")
        self.assertFalse(confirmed["native_cleanup_dispatched"])
        self.assertFalse(confirmed["mutation_performed"])
        run.assert_not_called()

    def test_blocked_outbox_request_remains_preserved(self):
        state = {
            "cleanup_requests": [
                {
                    "id": "blocked",
                    "state": "blocked",
                    "blocked_reason": "dirty",
                    "worktree_path": "/repo/task",
                }
            ],
            "worktrees": [],
            "sessions": [],
        }
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_worktree_inventory", return_value=[]),
            patch.object(LIFECYCLE, "lookup_pull_request") as lookup_pr,
        ):
            report = LIFECYCLE.cleanup_orchestration(Path("/repo"))

        item = report["requests"][0]
        self.assertFalse(item["eligibility"]["eligible"])
        self.assertIn("dirty", item["eligibility"]["preservation_reason"])
        lookup_pr.assert_not_called()

    def test_local_only_requires_explicit_operator_policy_switch(self):
        path = "/repo/local"
        request = {
            "id": "local-request",
            "state": "pending",
            "branch": "carryctx/local",
            "task_status": "completed",
            "worktree_path": path,
        }
        state = {
            "cleanup_requests": [request],
            "worktrees": [{"path": path}],
            "sessions": [],
        }
        worktree = {
            "resolved_path": path,
            "path": path,
            "branch": request["branch"],
            "managed": True,
            "external": False,
            "detached": False,
            "missing": False,
            "dirty": False,
        }
        lookup = LIFECYCLE.PullRequestLookup(None, [], "github-cli")
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_worktree_inventory", return_value=[worktree]),
            patch.object(LIFECYCLE, "lookup_pull_request", return_value=lookup),
        ):
            without_switch = LIFECYCLE.cleanup_orchestration(Path("/repo"))
            with_switch = LIFECYCLE.cleanup_orchestration(
                Path("/repo"), local_deliverable=True, confirm=True
            )

        self.assertFalse(without_switch["eligible"])
        self.assertEqual(len(with_switch["eligible"]), 1)

    def test_cleanup_parser_exposes_safe_operator_controls(self):
        args = LIFECYCLE.build_parser().parse_args(
            ["cleanup", "MTH-0126", "--worktree", "/repo/task", "--confirm"]
        )

        self.assertEqual(args.command, "cleanup")
        self.assertEqual(args.task_ref, "MTH-0126")
        self.assertEqual(args.worktree, "/repo/task")
        self.assertTrue(args.confirm)
        self.assertFalse(args.dry_run)

    def test_cleanup_observability_normalizes_operator_fields(self):
        report = LIFECYCLE.cleanup_audit(
            [{"id": "blocked", "state": "blocked", "blocked_reason": "dirty"}]
        )
        item = report["requests"][0]
        self.assertTrue(item["retryable"])
        self.assertFalse(item["safe_to_retry"])
        self.assertEqual(item["preservation_reason"], "dirty")
        self.assertIn("review", item["operator_action"])

    def test_successful_github_lookup_is_read_only_and_selects_latest_candidate(self):
        payload = (
            '[{"number": 7, "state": "CLOSED", "isDraft": false}, '
            '{"number": 9, "state": "MERGED", "isDraft": false}]'
        )
        completed = type(
            "Completed", (), {"returncode": 0, "stdout": payload, "stderr": ""}
        )()
        with patch.object(LIFECYCLE.subprocess, "run", return_value=completed) as run:
            lookup = LIFECYCLE.lookup_pull_request(Path("/repo"), "carryctx/mth-1")

        self.assertEqual(lookup.payload["number"], 9)
        self.assertEqual(
            LIFECYCLE.classify_pr_state(lookup.payload, local_branch=True), "merged"
        )
        command = run.call_args.args[0]
        self.assertEqual(command[:3], ["gh", "pr", "list"])
        self.assertIn("--state", command)
        self.assertIn("all", command)

    def test_observe_is_read_only_and_reports_cleanup(self):
        state = {
            "managed_worktree": {"path": "/repo"},
            "active_sessions": [],
            "cleanup_requests": [{"id": "r1", "state": "blocked"}],
            "pending_cleanup": [{"id": "r1", "state": "blocked"}],
        }
        with (
            patch.object(
                LIFECYCLE,
                "git_branch",
                return_value={"name": "feature", "local": True, "detached": False},
            ),
            patch.object(
                LIFECYCLE,
                "lookup_pull_request",
                return_value=LIFECYCLE.PullRequestLookup(
                    None, [], "github-cli", "offline"
                ),
            ),
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
            patch.object(LIFECYCLE, "_envelope") as envelope,
        ):
            report = LIFECYCLE.observe(Path("/repo"), dry_run=True)

        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["pull_request"]["state"], "lookup-error")
        self.assertEqual(report["cleanup"]["retryable"][0]["id"], "r1")
        self.assertFalse(report["branch_policy"]["merge_confirmed"])
        envelope.assert_not_called()

    def test_profiles_are_explicit_and_ordered(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".carryctx"
            config.mkdir()
            (config / "verification.toml").write_text(
                '[profiles.python]\ncommands = ["first", "second"]\n',
                encoding="utf-8",
            )

            self.assertEqual(
                LIFECYCLE.load_profiles(root), {"python": ["first", "second"]}
            )

    def test_dry_run_does_not_execute_commands(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".carryctx"
            config.mkdir()
            (config / "verification.toml").write_text(
                '[profiles.python]\ncommands = ["printf should-not-run"]\n',
                encoding="utf-8",
            )
            with patch.object(LIFECYCLE.subprocess, "run") as run:
                results = LIFECYCLE.verify_profile(root, "python", dry_run=True)

            self.assertEqual(results[0].output, "dry-run: not executed")
            run.assert_not_called()

    def test_verification_dry_run_reports_profile_argv_and_projection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".carryctx"
            config.mkdir()
            (config / "verification.toml").write_text(
                '[profiles.python]\ncommands = ["uv run check", "bun test"]\n',
                encoding="utf-8",
            )

            report = LIFECYCLE.verification_report(root, "python", dry_run=True)

        self.assertEqual(report["mode"], "dry-run")
        self.assertEqual(report["profile"], "python")
        self.assertEqual(report["commands"][0]["argv"], ["uv", "run", "check"])
        self.assertEqual(report["commands"][1]["projected_result"], "not-executed")
        self.assertEqual(report["projected_result"]["status"], "pass")
        self.assertFalse(report["projected_result"]["completion_dispatched"])

    def test_worktree_inventory_preserves_all_git_states(self):
        porcelain = """worktree /repo
HEAD aaa
branch refs/heads/main

worktree /external
HEAD bbb
detached

worktree /missing
HEAD ccc
branch refs/heads/old
prunable gitdir file points to non-existent location
"""
        with (
            patch.object(
                LIFECYCLE.subprocess,
                "run",
                return_value=type(
                    "Completed",
                    (),
                    {"returncode": 0, "stdout": porcelain, "stderr": ""},
                )(),
            ),
            patch.object(LIFECYCLE.Path, "exists", side_effect=[True, True, False]),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
        ):
            inventory = LIFECYCLE.git_worktree_inventory(
                Path("/repo"), [{"path": "/repo", "branch": "main"}]
            )

        by_path = {item["path"]: item for item in inventory}
        self.assertTrue(by_path["/repo"]["managed"])
        self.assertTrue(by_path["/external"]["external"])
        self.assertTrue(by_path["/external"]["detached"])
        self.assertTrue(by_path["/missing"]["missing"])
        self.assertTrue(by_path["/missing"]["prunable"])

    def test_all_worktree_audit_is_read_only_and_observes_prune(self):
        state = {
            "managed_worktree": {"path": "/repo"},
            "worktrees": [{"path": "/repo", "branch": "main"}],
            "sessions": [{"id": "s1", "state": "active"}],
            "active_sessions": [{"id": "s1", "state": "active"}],
            "cleanup_requests": [{"id": "r1", "state": "pending"}],
            "pending_cleanup": [{"id": "r1", "state": "pending"}],
        }
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_status", return_value=[" M file"]),
            patch.object(
                LIFECYCLE,
                "git_worktree_inventory",
                return_value=[{"path": "/repo", "dirty": True}],
            ) as inventory,
            patch.object(
                LIFECYCLE,
                "git_prune_observation",
                return_value={"candidates": [], "mutation_performed": False},
            ) as prune,
            patch.object(LIFECYCLE, "_envelope") as envelope,
        ):
            report = LIFECYCLE.audit(Path("/repo"), all_worktrees=True)

        self.assertEqual(report["worktrees"], [{"path": "/repo", "dirty": True}])
        self.assertEqual(report["cleanup"]["pending"][0]["id"], "r1")
        self.assertFalse(report["mutation_performed"])
        inventory.assert_called_once()
        prune.assert_called_once_with(Path("/repo"))
        envelope.assert_not_called()

    def test_verification_rejects_shell_operators(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / ".carryctx"
            config.mkdir()
            (config / "verification.toml").write_text(
                '[profiles.python]\ncommands = ["printf ok && rm -rf /"]\n',
                encoding="utf-8",
            )

            with self.assertRaisesRegex(RuntimeError, "direct argv"):
                LIFECYCLE.verify_profile(root, "python")

    def test_dirty_worktree_is_preserved_before_verification(self):
        state = {
            "managed_worktree": {"path": "/repo", "branch": None},
            "active_sessions": [],
            "cleanup_requests": [],
        }
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_status", return_value=[" M user.txt"]),
            patch.object(LIFECYCLE, "verify_profile") as verify,
        ):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")

        self.assertEqual(result, LIFECYCLE.EXIT_UNSAFE)
        verify.assert_not_called()

    def test_unmanaged_path_is_refused(self):
        state = {
            "managed_worktree": None,
            "active_sessions": [],
            "cleanup_requests": [],
        }
        with patch.object(LIFECYCLE, "carryctx_state", return_value=state):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")

        self.assertEqual(result, LIFECYCLE.EXIT_UNSAFE)

    def test_detached_path_is_refused_before_verification(self):
        state = {
            "managed_worktree": {"path": "/repo", "branch": None},
            "active_sessions": [],
            "cleanup_requests": [],
        }
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(
                LIFECYCLE,
                "git_branch",
                return_value={"name": None, "local": False, "detached": True},
            ),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
            patch.object(LIFECYCLE, "verify_profile") as verify,
        ):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")
        self.assertEqual(result, LIFECYCLE.EXIT_UNSAFE)
        verify.assert_not_called()

    def test_failed_verification_keeps_task_incomplete(self):
        state = {
            "managed_worktree": {"path": "/repo"},
            "active_sessions": [],
            "cleanup_requests": [],
        }
        task = {"status": "in_progress"}
        failed = [LIFECYCLE.CommandResult("check", 1, "failure")]
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
            patch.object(LIFECYCLE, "_envelope", return_value={"data": task}),
            patch.object(LIFECYCLE, "verify_profile", return_value=failed),
            patch.object(LIFECYCLE.subprocess, "run") as run,
        ):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")

        self.assertEqual(result, LIFECYCLE.EXIT_VERIFICATION)
        run.assert_not_called()

    def test_success_dispatches_completion_once_and_preserves_active_session(self):
        state = {
            "managed_worktree": {"path": "/repo"},
            "active_sessions": [{"id": "session-1", "state": "active"}],
            "cleanup_requests": [],
        }
        task = {"status": "in_progress"}
        passed = [LIFECYCLE.CommandResult("check", 0, "ok")]

        def run(command, **kwargs):
            self.assertEqual(
                command, ["carryctx", "task", "complete", "MTH-1", "--json"]
            )
            return type("Completed", (), {"returncode": 0})()

        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
            patch.object(LIFECYCLE, "_envelope", return_value={"data": task}),
            patch.object(LIFECYCLE, "verify_profile", return_value=passed),
            patch.object(LIFECYCLE.subprocess, "run", side_effect=run) as mocked_run,
        ):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")

        self.assertEqual(result, 0)
        mocked_run.assert_called_once()

    def test_already_completed_task_is_not_dispatched_again(self):
        state = {
            "managed_worktree": {"path": "/repo"},
            "active_sessions": [],
            "cleanup_requests": [],
        }
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(
                LIFECYCLE, "_envelope", return_value={"data": {"status": "completed"}}
            ),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
            patch.object(LIFECYCLE, "verify_profile") as verify,
        ):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")

        self.assertEqual(result, 0)
        verify.assert_not_called()

    def test_ready_task_is_not_dispatched(self):
        state = {
            "managed_worktree": {"path": "/repo"},
            "active_sessions": [],
            "cleanup_requests": [],
        }
        with (
            patch.object(LIFECYCLE, "carryctx_state", return_value=state),
            patch.object(
                LIFECYCLE, "_envelope", return_value={"data": {"status": "ready"}}
            ),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
            patch.object(LIFECYCLE, "verify_profile") as verify,
        ):
            result = LIFECYCLE.complete(Path("/repo"), "MTH-1", "full")

        self.assertEqual(result, LIFECYCLE.EXIT_UNSAFE)
        verify.assert_not_called()

    def _completion_state(self, **overrides):
        state = {
            "managed_worktree": {"path": "/repo", "branch": "carryctx/mth-1"},
            "active_sessions": [],
            "cleanup_requests": [],
        }
        state.update(overrides)
        return state

    def _patch_completion_observations(self, state):
        return (
            patch.object(LIFECYCLE, "carryctx_state", side_effect=[state, state]),
            patch.object(
                LIFECYCLE,
                "git_branch",
                return_value={
                    "name": "carryctx/mth-1",
                    "local": True,
                    "detached": False,
                },
            ),
            patch.object(LIFECYCLE, "git_status", return_value=[]),
        )

    def test_complete_verified_success_emits_evidence_and_dispatches_once(self):
        state = self._completion_state()
        task = {"status": "in_progress"}
        passed = [LIFECYCLE.CommandResult("check", 0, "ok")]
        dispatch = type("Completed", (), {"returncode": 0})()
        with (
            self._patch_completion_observations(state)[0],
            self._patch_completion_observations(state)[1],
            self._patch_completion_observations(state)[2],
            patch.object(
                LIFECYCLE,
                "_envelope",
                side_effect=[
                    {"data": task},
                    {"data": task},
                    {"data": {"status": "completed"}},
                ],
            ),
            patch.object(LIFECYCLE, "verify_profile", return_value=passed),
            patch.object(
                LIFECYCLE,
                "verification_report",
                return_value={
                    "commands": [{"command": "check", "argv": ["check"]}],
                },
            ),
            patch.object(LIFECYCLE.subprocess, "run", return_value=dispatch) as run,
        ):
            result, evidence = LIFECYCLE.completion_evidence(
                Path("/repo"), "MTH-1", "full"
            )

        self.assertEqual(result, 0)
        self.assertEqual(evidence["status"], "completed")
        self.assertTrue(all(gate["passed"] for gate in evidence["gates_after"]))
        self.assertEqual(evidence["dispatch"]["returncode"], 0)
        self.assertEqual(
            evidence["dispatch"]["readback"]["task"]["status"], "completed"
        )
        self.assertTrue(evidence["mutation_performed"])
        run.assert_called_once_with(
            ["carryctx", "task", "complete", "MTH-1", "--json"],
            cwd=Path("/repo"),
            check=False,
            text=True,
        )

    def test_complete_verified_failed_verification_does_not_dispatch(self):
        state = self._completion_state()
        task = {"status": "in_progress"}
        failed = [LIFECYCLE.CommandResult("check", 1, "failure")]
        with (
            self._patch_completion_observations(state)[0],
            self._patch_completion_observations(state)[1],
            self._patch_completion_observations(state)[2],
            patch.object(LIFECYCLE, "_envelope", return_value={"data": task}),
            patch.object(LIFECYCLE, "verify_profile", return_value=failed),
            patch.object(
                LIFECYCLE,
                "verification_report",
                return_value={"commands": [{"command": "check", "argv": ["check"]}]},
            ),
            patch.object(LIFECYCLE.subprocess, "run") as run,
        ):
            result, evidence = LIFECYCLE.completion_evidence(
                Path("/repo"), "MTH-1", "full"
            )

        self.assertEqual(result, LIFECYCLE.EXIT_VERIFICATION)
        self.assertEqual(evidence["status"], "verification-failed")
        self.assertFalse(evidence["dispatch"]["attempted"])
        run.assert_not_called()

    def test_complete_verified_requires_successful_completion_readback(self):
        state = self._completion_state()
        task = {"status": "in_progress"}
        passed = [LIFECYCLE.CommandResult("check", 0, "ok")]
        dispatch = type("Completed", (), {"returncode": 0})()
        for readback in ({"status": "in_progress"}, None):
            with self.subTest(readback=readback):
                envelope_results = [{"data": task}, {"data": task}]
                if readback is not None:
                    envelope_results.append({"data": readback})
                else:
                    envelope_results.append(
                        {"success": False, "error": "readback unavailable"}
                    )
                with (
                    self._patch_completion_observations(state)[0],
                    self._patch_completion_observations(state)[1],
                    self._patch_completion_observations(state)[2],
                    patch.object(LIFECYCLE, "_envelope", side_effect=envelope_results),
                    patch.object(LIFECYCLE, "verify_profile", return_value=passed),
                    patch.object(
                        LIFECYCLE,
                        "verification_report",
                        return_value={
                            "commands": [{"command": "check", "argv": ["check"]}]
                        },
                    ),
                    patch.object(
                        LIFECYCLE.subprocess, "run", return_value=dispatch
                    ) as run,
                ):
                    result, evidence = LIFECYCLE.completion_evidence(
                        Path("/repo"), "MTH-1", "full"
                    )

                self.assertEqual(result, LIFECYCLE.EXIT_READBACK)
                self.assertEqual(evidence["status"], "completion-readback-failed")
                self.assertFalse(evidence["mutation_performed"])
                self.assertTrue(evidence["dispatch"]["readback"]["attempted"])
                run.assert_called_once()

    def test_complete_verified_refuses_dirty_active_detached_and_unmanaged(self):
        cases = (
            ("dirty", self._completion_state(), [" M file"], False, "clean"),
            (
                "active",
                self._completion_state(
                    active_sessions=[{"id": "s1", "state": "active"}]
                ),
                [],
                False,
                "no-active-session",
            ),
            (
                "detached",
                self._completion_state(
                    managed_worktree={"path": "/repo", "branch": None}
                ),
                [],
                True,
                "detached",
            ),
            (
                "unmanaged",
                self._completion_state(managed_worktree=None),
                [],
                False,
                "managed",
            ),
        )
        for name, state, dirty, detached, gate_name in cases:
            with self.subTest(name=name):
                branch = {
                    "name": None if detached else "carryctx/mth-1",
                    "local": not detached,
                    "detached": detached,
                }
                with (
                    patch.object(LIFECYCLE, "carryctx_state", return_value=state),
                    patch.object(LIFECYCLE, "git_branch", return_value=branch),
                    patch.object(LIFECYCLE, "git_status", return_value=dirty),
                    patch.object(
                        LIFECYCLE,
                        "_envelope",
                        return_value={"data": {"status": "in_progress"}},
                    ),
                    patch.object(LIFECYCLE, "verify_profile") as verify,
                ):
                    result, evidence = LIFECYCLE.completion_evidence(
                        Path("/repo"), "MTH-1", "full"
                    )

                self.assertEqual(result, LIFECYCLE.EXIT_UNSAFE)
                self.assertEqual(evidence["status"], "refused")
                self.assertIn(gate_name, evidence["failure_reasons"])
                verify.assert_not_called()

    def test_complete_verified_dry_run_is_structured_and_does_not_dispatch(self):
        state = self._completion_state()
        task = {"status": "in_progress"}
        with (
            self._patch_completion_observations(state)[0],
            self._patch_completion_observations(state)[1],
            self._patch_completion_observations(state)[2],
            patch.object(LIFECYCLE, "_envelope", return_value={"data": task}),
            patch.object(LIFECYCLE, "verify_profile") as verify,
            patch.object(
                LIFECYCLE,
                "verification_report",
                return_value={"commands": []},
            ),
        ):
            result, evidence = LIFECYCLE.completion_evidence(
                Path("/repo"), "MTH-1", "full", dry_run=True
            )

        self.assertEqual(result, 0)
        self.assertEqual(evidence["status"], "would-complete")
        self.assertEqual(evidence["mode"], "dry-run")
        self.assertFalse(evidence["dispatch"]["attempted"])
        self.assertFalse(evidence["mutation_performed"])
        verify.assert_called_once_with(
            Path("/repo"), "full", dry_run=True, emit_output=False
        )

    def test_parser_exposes_complete_verified_command(self):
        args = LIFECYCLE.build_parser().parse_args(["complete-verified", "MTH-1"])
        self.assertEqual(args.command, "complete-verified")
        self.assertEqual(args.task_ref, "MTH-1")


if __name__ == "__main__":
    unittest.main()

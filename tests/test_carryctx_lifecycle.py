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


if __name__ == "__main__":
    unittest.main()

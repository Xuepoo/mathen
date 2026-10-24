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
            "managed_worktree": {"path": "/repo"},
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

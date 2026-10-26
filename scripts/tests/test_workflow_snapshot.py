import importlib.util
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).parents[1] / "workflow_snapshot.py"
SPEC = importlib.util.spec_from_file_location("workflow_snapshot", SCRIPT)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class WorkflowSnapshotTests(unittest.TestCase):
    def test_capability_requires_cargo_carryctx_012(self):
        good = {
            "data": {
                "contract_versions": {
                    "cli": "0.12.0",
                    "ctxpack_format": {
                        "format": "carryctx-pack-dir",
                        "format_version": 2,
                    },
                    "db_schema": 18,
                }
            }
        }
        MODULE.capability(good)
        bad = json.loads(json.dumps(good))
        bad["data"]["contract_versions"]["cli"] = "0.11.6"
        with self.assertRaises(SystemExit):
            MODULE.capability(bad)

    def test_manifest_rejects_unredacted_or_wrong_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            payload = {
                "carryctx_version": "0.12.0",
                "format": "carryctx-pack-dir",
                "format_version": 2,
                "schema_version": 18,
                "project_id": "project",
                "export_id": "01ARZ3NDEKTSV4RRFFQ69G5FAV",
                "source": {"git_commit": "a" * 40},
                "redacted": False,
            }
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(SystemExit):
                MODULE.manifest(path, "project")
            payload["redacted"] = True
            payload["project_id"] = "other"
            path.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(SystemExit):
                MODULE.manifest(path, "project")

    def test_provenance_is_bounded_and_export_bound(self):
        message = (
            "snapshot\n\n"
            "CarryCtx-Export-Id: 01ARZ3NDEKTSV4RRFFQ69G5FAV\n"
            "CarryCtx-Source: mathen@abcdef1 (main)\n"
        )
        self.assertEqual(
            MODULE.provenance(message, "01ARZ3NDEKTSV4RRFFQ69G5FAV"), "abcdef1"
        )
        with self.assertRaises(SystemExit):
            MODULE.provenance(
                message.replace("mathen@abcdef1", "other@abcdef1"),
                "01ARZ3NDEKTSV4RRFFQ69G5FAV",
            )

    def test_db_state_counts_all_durable_tables_and_blocks_active_state(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "mathen"
            common = root / ".git"
            db_path = common / "carryctx" / "state.sqlite"
            db_path.parent.mkdir(parents=True)
            connection = sqlite3.connect(db_path)
            connection.executescript(
                """
                CREATE TABLE projects (
                    id TEXT, repository_root TEXT, git_common_dir TEXT,
                    main_branch TEXT, schema_version INTEGER
                );
                CREATE TABLE schema_migrations (
                    version INTEGER, name TEXT, checksum TEXT, applied_at TEXT
                );
                CREATE TABLE sessions (id TEXT, state TEXT);
                CREATE TABLE operations (id TEXT, state TEXT);
                CREATE TABLE sequences (id INTEGER);
                CREATE TABLE tombstones (id INTEGER);
                CREATE TABLE worktree_cleanup_requests (id INTEGER, state TEXT);
                CREATE TABLE snapshot_state (id INTEGER);
                """
            )
            for version in range(1, 19):
                connection.execute(
                    "INSERT INTO schema_migrations "
                    "VALUES (?, 'migration', 'checksum', 'now')",
                    (version,),
                )
            connection.execute(
                "INSERT INTO projects VALUES (?, ?, ?, 'main', 4)",
                ("project", str(root), str(common)),
            )
            connection.execute("INSERT INTO sequences VALUES (1)")
            connection.execute("INSERT INTO tombstones VALUES (1)")
            connection.execute("INSERT INTO snapshot_state VALUES (1)")
            connection.execute("INSERT INTO sessions VALUES ('s', 'active')")
            connection.execute("INSERT INTO operations VALUES ('o', 'prepared')")
            connection.commit()
            state = MODULE.db_state(db_path, "project", root, common)
            self.assertEqual(state["table_counts"]["sequences"], 1)
            self.assertEqual(state["table_counts"]["tombstones"], 1)
            self.assertEqual(state["table_counts"]["snapshot_state"], 1)
            self.assertGreaterEqual(state["data_rows"], 5)
            self.assertEqual(state["active"], ["session:s", "operation:o"])

    def test_config_symlink_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target.toml"
            config = root / "config.toml"
            target.write_text("[project]\nname='mathen'\n", encoding="utf-8")
            config.symlink_to(target)
            with self.assertRaises(SystemExit):
                MODULE.load_config(config)

    def test_missing_config_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SystemExit):
                MODULE.load_config(Path(directory) / "missing.toml")


if __name__ == "__main__":
    unittest.main()

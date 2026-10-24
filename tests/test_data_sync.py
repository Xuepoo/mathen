import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from mathen.config import default_config
from mathen.data_sync import SyncError, _safe_extract_cards, status

ROOT = Path(__file__).parents[1]


class DataSyncTests(unittest.TestCase):
    def test_status_detects_changed_cards(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            cards = Path(directory) / "systems"
            cards.mkdir()
            card = cards / "git.json"
            card.write_bytes((ROOT / "data/systems/git.json").read_bytes())
            (cards / ".mathen-sync.json").write_text(
                json.dumps({"card_count": 1, "digest": "wrong"}), encoding="utf-8"
            )
            config = default_config()
            config = config.__class__(
                path=config.path,
                paths=config.paths.__class__(
                    data_dir=Path(directory),
                    cards_dir=cards,
                    drafts_dir=config.paths.drafts_dir,
                    analyses_dir=config.paths.analyses_dir,
                    bundles_dir=config.paths.bundles_dir,
                    manifest=config.paths.manifest,
                    cache_dir=config.paths.cache_dir,
                ),
                llm=config.llm,
                mcp=config.mcp,
                sync=config.sync,
            )

            result = status(config)

        self.assertFalse(result.valid)
        self.assertEqual(
            result.error, "card digest differs from synchronization metadata"
        )

    def test_archive_rejects_duplicate_card_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            archive = io.BytesIO()
            with tarfile.open(fileobj=archive, mode="w:gz") as tar:
                for name in ("one/systems/git.json", "two/systems/git.json"):
                    info = tarfile.TarInfo(name)
                    info.size = 2
                    tar.addfile(info, io.BytesIO(b"{}"))
            archive.seek(0)
            with tarfile.open(fileobj=archive, mode="r:gz") as tar:
                with self.assertRaisesRegex(SyncError, "duplicate card"):
                    _safe_extract_cards(tar, Path(directory))


if __name__ == "__main__":
    unittest.main()

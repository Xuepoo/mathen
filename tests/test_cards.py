import http.client
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mathen.cards import (
    CardValidationError,
    discover_cards,
    load_card,
    validate_card,
)
from mathen.modeling import build_modeling_bundle, render_modeling_prompt
from mathen.repositories import (
    RepositoryAnalysisError,
    RepositorySpec,
    _read_url_bytes,
    build_draft_card,
    inspect_repository,
    load_manifest,
)

ROOT = Path(__file__).parents[1]


class CardValidationTests(unittest.TestCase):
    def test_seed_cards_are_valid(self) -> None:
        cards = discover_cards(ROOT / "data" / "systems")
        self.assertGreaterEqual(len(cards), 4)
        for card in cards:
            load_card(card)

    def test_unknown_evidence_is_rejected(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "git.json").read_text())
        card["features"][0]["evidence_ids"] = ["missing"]
        with self.assertRaises(CardValidationError):
            validate_card(card)

    def test_invalid_json_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "invalid.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(CardValidationError):
                load_card(path)

    def test_repository_manifest_is_valid(self) -> None:
        specs = load_manifest(ROOT / "data" / "repositories" / "representative.json")
        self.assertGreaterEqual(len(specs), 15)
        self.assertTrue(
            {"sqlite", "qemu", "docker", "kubernetes"}.issubset(
                spec.id for spec in specs
            )
        )

    def test_generated_draft_card_has_valid_references(self) -> None:
        spec = RepositorySpec(
            id="fixture",
            name="Fixture",
            category="test",
            repository="https://example.com/fixture.git",
            documentation="https://example.com/docs",
            ref="main",
            priority="test",
        )
        card = build_draft_card(
            spec,
            {
                "commit": "a" * 40,
                "commit_url": "https://example.com/fixture/commit/" + "a" * 40,
                "analyzed_at": "2026-01-01T00:00:00+00:00",
                "file_count": 2,
                "top_level_entries": ["README.md", "src"],
                "language_counts": {"Python": 1},
                "build_markers": ["pyproject.toml"],
            },
        )
        validate_card(card)
        self.assertEqual(card["features"][1]["id"], "architecture-path-signals")

    def test_archive_like_checkout_records_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            checkout = Path(directory)
            (checkout / "src").mkdir()
            (checkout / "src" / "main.c").write_text("int main(void) { return 0; }\n")
            (checkout / "Makefile").write_text("all:\n\ttrue\n")
            (checkout / ".mathen-repository.json").write_text(
                json.dumps(
                    {
                        "commit": "b" * 40,
                        "repository": "https://github.com/example/project.git",
                        "requested_ref": "main",
                        "source": "github-archive",
                    }
                )
            )
            spec = RepositorySpec(
                id="fixture",
                name="Fixture",
                category="test",
                repository="https://github.com/example/project.git",
                documentation="https://example.com/docs",
                ref="main",
                priority="test",
            )
            report = inspect_repository(spec, checkout)
            self.assertEqual(report["provenance"], "github-archive")
            self.assertEqual(report["commit"], "b" * 40)

    def test_interrupted_archive_response_is_recoverable(self) -> None:
        class BrokenResponse:
            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

            def read(self):
                raise http.client.IncompleteRead(b"partial", 10)

        with (
            patch("mathen.repositories._open_url", return_value=BrokenResponse()),
            patch("mathen.repositories.time.sleep"),
            self.assertRaises(RepositoryAnalysisError),
        ):
            _read_url_bytes("https://example.com/archive.tar.gz", timeout=1)

    def test_modeling_bundle_contains_fixed_revision_contract(self) -> None:
        spec = RepositorySpec(
            id="fixture",
            name="Fixture",
            category="test",
            repository="https://github.com/example/fixture.git",
            documentation="https://example.com/docs",
            ref="main",
            priority="test",
        )
        analysis = {
            "system_id": "fixture",
            "commit": "c" * 40,
            "commit_url": "https://github.com/example/fixture/commit/" + "c" * 40,
            "provenance": "github-archive",
            "file_count": 1,
        }
        draft = {"id": "fixture", "features": [], "evidence": []}
        bundle = build_modeling_bundle(spec, analysis, draft)
        self.assertEqual(bundle["system"]["commit"], "c" * 40)
        self.assertEqual(bundle["contract_version"], 1)
        self.assertIn("Architecture Card JSON", render_modeling_prompt(bundle))

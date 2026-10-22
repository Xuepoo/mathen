import http.client
import json
import os
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
from mathen.llm import (
    LLMModelError,
    client_from_environment,
    model_bundle,
    model_bundles,
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

    def test_legacy_card_without_evolution_fields_remains_valid(self) -> None:
        card = json.loads((ROOT / "data" / "systems" / "git.json").read_text())
        self.assertNotIn("relations", card)
        validate_card(card)

    def test_temporal_relations_and_composition_contract_is_valid(self) -> None:
        card = self._evolution_fixture()
        validate_card(card)
        self.assertEqual(card["relations"][0]["type"], "extends")
        self.assertEqual(
            card["composition"]["conflicts"][0]["claim_status"], "under-review"
        )

    def test_evolution_claims_need_known_evidence_and_status(self) -> None:
        card = self._evolution_fixture()
        card["relations"][0]["evidence_ids"] = ["missing"]
        with self.assertRaisesRegex(CardValidationError, "unknown evidence ids"):
            validate_card(card)

        card = self._evolution_fixture()
        card["composition"]["claim_status"] = "certain"
        with self.assertRaisesRegex(
            CardValidationError, "invalid composition claim status"
        ):
            validate_card(card)

    def test_composition_rejects_duplicate_inputs(self) -> None:
        card = self._evolution_fixture()
        card["composition"]["inputs"].append(card["composition"]["inputs"][0].copy())
        with self.assertRaisesRegex(CardValidationError, "duplicate composition input"):
            validate_card(card)

    def test_repository_manifest_is_valid(self) -> None:
        specs = load_manifest(ROOT / "data" / "repositories" / "representative.json")
        self.assertGreaterEqual(len(specs), 15)
        self.assertTrue(
            {"sqlite", "qemu", "docker", "kubernetes"}.issubset(
                spec.id for spec in specs
            )
        )

    @staticmethod
    def _evolution_fixture() -> dict:
        return {
            "id": "composed-system",
            "name": "Composed system",
            "summary": "A contract fixture.",
            "scope": ["architecture"],
            "version_context": "release 2",
            "features": [
                {
                    "id": "feature",
                    "name": "Feature",
                    "category": "composition",
                    "claim_type": "fact",
                    "description": "A contract feature.",
                    "evidence_ids": ["spec"],
                }
            ],
            "mathematical_views": [],
            "trade_offs": [],
            "evidence": [
                {
                    "id": "spec",
                    "kind": "official-doc",
                    "title": "Contract specification",
                    "uri": "https://example.com/spec",
                }
            ],
            "temporal_context": {
                "version": "2.0",
                "status": "current",
                "claim_status": "accepted",
                "evidence_ids": ["spec"],
            },
            "relations": [
                {
                    "type": "extends",
                    "target": "base-system",
                    "claim_type": "inference",
                    "claim_status": "under-review",
                    "evidence_ids": ["spec"],
                }
            ],
            "composition": {
                "inputs": [
                    {
                        "system_id": "base-system",
                        "role": "storage boundary",
                        "claim_status": "accepted",
                        "evidence_ids": ["spec"],
                    },
                    {
                        "system_id": "worker-system",
                        "role": "execution boundary",
                        "claim_status": "proposed",
                        "evidence_ids": ["spec"],
                    },
                ],
                "constraints": [
                    {
                        "description": "Inputs must share an identity boundary.",
                        "claim_type": "hypothesis",
                        "claim_status": "proposed",
                        "evidence_ids": ["spec"],
                    }
                ],
                "preserved_properties": [
                    {
                        "description": "Storage remains durable.",
                        "claim_type": "inference",
                        "claim_status": "under-review",
                        "evidence_ids": ["spec"],
                    }
                ],
                "conflicts": [
                    {
                        "description": "Execution isolation may increase latency.",
                        "claim_type": "hypothesis",
                        "claim_status": "under-review",
                        "evidence_ids": ["spec"],
                    }
                ],
                "claim_status": "under-review",
                "evidence_ids": ["spec"],
            },
        }

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

    def test_llm_model_rejects_evidence_not_in_bundle(self) -> None:
        bundle = self._modeling_fixture()
        response = json.loads(json.dumps(bundle["existing_structural_draft"]))
        response["features"][0]["evidence_ids"] = ["invented"]
        with self.assertRaisesRegex(LLMModelError, "not present in the bundle"):
            model_bundle(bundle, _FakeClient(response))

    def test_llm_model_rejects_changed_evidence_record(self) -> None:
        bundle = self._modeling_fixture()
        response = json.loads(json.dumps(bundle["existing_structural_draft"]))
        response["evidence"][0]["title"] = "untrusted replacement"
        with self.assertRaisesRegex(LLMModelError, "changed evidence"):
            model_bundle(bundle, _FakeClient(response))

    def test_llm_model_writes_only_validated_draft(self) -> None:
        bundle = self._modeling_fixture()
        with tempfile.TemporaryDirectory() as directory:
            bundle_path = Path(directory) / "fixture.json"
            bundle_path.write_text(json.dumps(bundle), encoding="utf-8")
            output_dir = Path(directory) / "drafts" / "llm"
            written = model_bundles(
                bundle_path,
                output_dir,
                _FakeClient(bundle["existing_structural_draft"]),
            )
            self.assertEqual(written, [output_dir / "fixture.json"])
            self.assertEqual(json.loads(written[0].read_text())["id"], "fixture")

    def test_llm_model_refuses_systems_output(self) -> None:
        bundle = self._modeling_fixture()
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaisesRegex(LLMModelError, "data/systems"):
                model_bundles(
                    Path(directory),
                    Path(directory) / "data" / "systems",
                    _FakeClient(bundle),
                )

    def test_llm_client_supports_environment_and_explicit_configuration(self) -> None:
        with patch.dict(
            os.environ,
            {
                "OPENAI_API_KEY": "environment-key",
                "MATHEN_LLM_MODEL": "environment-model",
                "MATHEN_LLM_BASE_URL": "https://environment.example/v1",
            },
        ):
            environment_client = client_from_environment()
        self.assertEqual(environment_client.api_key, "environment-key")
        self.assertEqual(environment_client.model, "environment-model")
        self.assertEqual(environment_client.base_url, "https://environment.example/v1")

        explicit_client = client_from_environment(
            base_url="https://explicit.example/v1",
            api_key="explicit-key",
            model="explicit-model",
        )
        self.assertEqual(explicit_client.api_key, "explicit-key")
        self.assertEqual(explicit_client.model, "explicit-model")
        self.assertEqual(explicit_client.base_url, "https://explicit.example/v1")

    @staticmethod
    def _modeling_fixture() -> dict:
        evidence = {
            "id": "repository-commit",
            "kind": "source-code",
            "title": "Fixture source",
            "uri": "https://example.com/commit",
        }
        draft = {
            "id": "fixture",
            "name": "Fixture",
            "summary": "A fixture card.",
            "scope": ["repository"],
            "features": [
                {
                    "id": "observable-structure",
                    "name": "Observable structure",
                    "category": "repository-model",
                    "claim_type": "fact",
                    "description": "The repository has observable structure.",
                    "evidence_ids": ["repository-commit"],
                }
            ],
            "mathematical_views": [],
            "trade_offs": [
                {
                    "feature_id": "observable-structure",
                    "benefits": ["Reproducible inspection"],
                    "costs": ["Incomplete semantics"],
                }
            ],
            "evidence": [evidence],
        }
        return {
            "system": {"id": "fixture", "commit": "a" * 40},
            "existing_structural_draft": draft,
        }


class _FakeClient:
    def __init__(self, response: dict) -> None:
        self.response = response

    def complete(self, _prompt: str) -> str:
        return json.dumps(self.response)

import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "direct_llm_control.py"
SCHEMA = ROOT / "schemas" / "direct-llm-control.schema.json"


spec = importlib.util.spec_from_file_location("direct_llm_control", SCRIPT)
assert spec and spec.loader
direct_llm_control = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = direct_llm_control
spec.loader.exec_module(direct_llm_control)


class DirectLLMControlTests(unittest.TestCase):
    def test_dry_run_is_valid_not_evaluated_and_secret_safe(self) -> None:
        manifest = direct_llm_control.dry_run_manifest(
            provider="local-runtime",
            model="qwen2.5:7b-instruct-q4_K_M",
        )
        direct_llm_control.validate_manifest(manifest)
        self.assertEqual(manifest["outcome"]["status"], "not-evaluated")
        self.assertEqual(manifest["output"]["status"], "absent")
        self.assertTrue(manifest["output"]["secret_safe"])
        self.assertEqual(
            manifest["provider"]["exact_model_id"], "qwen2.5:7b-instruct-q4_K_M"
        )
        self.assertEqual(manifest["candidates"], [])

    def test_missing_output_cannot_be_reported_as_evaluated(self) -> None:
        manifest = direct_llm_control.dry_run_manifest()
        manifest["outcome"]["status"] = "accepted"
        with self.assertRaisesRegex(ValueError, "absent output must be not-evaluated"):
            direct_llm_control.validate_manifest(manifest)

    def test_evaluated_output_requires_exact_runtime_provenance(self) -> None:
        manifest = direct_llm_control.dry_run_manifest()
        manifest["output"] = {
            "status": "redacted",
            "digest": direct_llm_control.digest_json({"candidate": 1}),
            "secret_safe": True,
            "record_count": 1,
        }
        manifest["outcome"] = {
            "status": "undetermined",
            "reason": "Research output requires review.",
        }
        with self.assertRaisesRegex(ValueError, "exact runtime provenance"):
            direct_llm_control.validate_manifest(manifest)

    def test_candidate_and_claim_evidence_are_local(self) -> None:
        manifest = direct_llm_control.dry_run_manifest()
        manifest["output"] = {
            "status": "redacted",
            "digest": direct_llm_control.digest_json({"candidate": 1}),
            "secret_safe": True,
            "record_count": 1,
        }
        manifest["outcome"] = {
            "status": "undetermined",
            "reason": "Research output requires review.",
        }
        manifest["provider"] = {
            "name": "local-runtime",
            "exact_model_id": "model-1",
        }
        manifest["runtime"].update(
            {
                "runtime_kind": "llama.cpp",
                "runtime_version": "1.0",
                "source_revision": "git:abc123",
            }
        )
        manifest["input_bundle"]["evidence_ids"] = ["evidence-1"]
        manifest["candidates"] = [
            {
                "id": "candidate-1",
                "evidence_ids": ["evidence-1"],
                "claims": [
                    {
                        "id": "claim-1",
                        "claim_type": "hypothesis",
                        "text": "A candidate claim requiring review.",
                        "evidence_ids": ["evidence-1"],
                    }
                ],
                "proven": False,
            }
        ]
        direct_llm_control.validate_manifest(manifest)
        manifest["candidates"][0]["claims"][0]["evidence_ids"] = ["outside"]
        with self.assertRaisesRegex(ValueError, "local"):
            direct_llm_control.validate_manifest(manifest)

    def test_secret_bearing_fields_are_rejected(self) -> None:
        manifest = direct_llm_control.dry_run_manifest()
        manifest["runtime"]["api_key"] = "never-record-this"
        with self.assertRaisesRegex(ValueError, "secret-bearing"):
            direct_llm_control.validate_manifest(manifest)

    def test_unknown_fields_and_unproven_boundary_are_rejected(self) -> None:
        manifest = direct_llm_control.dry_run_manifest()
        manifest["unexpected"] = True
        with self.assertRaisesRegex(ValueError, "unknown fields"):
            direct_llm_control.validate_manifest(manifest)
        manifest = direct_llm_control.dry_run_manifest()
        manifest["result_boundary"]["canonical"] = True
        with self.assertRaisesRegex(ValueError, "canonical"):
            direct_llm_control.validate_manifest(manifest)

    def test_cli_dry_run_and_validate(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "control.json"
            dry_run = subprocess.run(
                [sys.executable, str(SCRIPT), "dry-run", "--output", str(output)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(dry_run.returncode, 0, dry_run.stderr)
            self.assertTrue(output.exists())
            validated = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", str(output)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)
            self.assertIn("valid", validated.stdout)

    def test_schema_declares_research_boundary(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["manifest_kind"]["const"], "direct_llm_control"
        )
        self.assertEqual(schema["properties"]["schema_version"]["const"], "1.0")
        self.assertEqual(
            schema["$defs"]["resultBoundary"]["properties"]["canonical"],
            {"const": False},
        )
        self.assertEqual(
            schema["$defs"]["output"]["properties"]["secret_safe"], {"const": True}
        )


if __name__ == "__main__":
    unittest.main()

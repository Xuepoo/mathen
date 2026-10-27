import importlib.util
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "direct_llm_readiness.py"
ARTIFACT = ROOT / "data" / "analyses" / "mth-0194-direct-llm-readiness.json"
SCHEMA = ROOT / "schemas" / "direct-llm-readiness.schema.json"

spec = importlib.util.spec_from_file_location("direct_llm_readiness", SCRIPT)
assert spec and spec.loader
readiness = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = readiness
spec.loader.exec_module(readiness)


class DirectLLMReadinessTests(unittest.TestCase):
    def test_artifact_is_not_evaluated_and_secret_safe(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        readiness.validate_record(value)
        self.assertIsNone(value["provenance"]["provider"])
        self.assertIsNone(value["provenance"]["exact_model_id"])
        self.assertFalse(value["runtime_inventory"]["approved_runtime_available"])
        self.assertFalse(value["cache_inventory"]["model_identifiers_recorded"])
        self.assertFalse(value["configuration_inventory"]["secret_values_read"])
        self.assertTrue(all(metric is None for metric in value["metrics"].values()))
        self.assertFalse(value["provenance"]["prompt"]["raw_stored"])
        self.assertFalse(value["provenance"]["output"]["raw_stored"])

    def test_record_does_not_contain_secret_values_or_paths(self) -> None:
        text = ARTIFACT.read_text(encoding="utf-8")
        self.assertNotIn("API_ACCESS_TOKEN", text)
        self.assertNotIn("ANTHROPIC_API_KEY", text)
        self.assertNotIn(str(Path.home()), text)
        self.assertNotIn("model--", text)

    def test_validation_rejects_evaluated_or_recorded_model(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        value["provenance"]["exact_model_id"] = "model"
        with self.assertRaisesRegex(ValueError, "exact_model_id"):
            readiness.validate_record(value)
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        value["result_boundary"]["status"] = "accepted"
        with self.assertRaisesRegex(ValueError, "not-evaluated"):
            readiness.validate_record(value)

    def test_inspector_does_not_run_inference_and_cli_round_trips(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "readiness.json"
            inspected = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "inspect",
                    "--root",
                    str(ROOT),
                    "--output",
                    str(output),
                ],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(inspected.returncode, 0, inspected.stderr)
            value = json.loads(output.read_text(encoding="utf-8"))
            readiness.validate_record(value)
            self.assertFalse(value["inspection"]["network_requests"])
            validated = subprocess.run(
                [sys.executable, str(SCRIPT), "validate", str(output)],
                cwd=ROOT,
                check=False,
                capture_output=True,
                text=True,
            )
            self.assertEqual(validated.returncode, 0, validated.stderr)

    def test_schema_declares_null_provenance_and_metrics_boundary(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(
            schema["properties"]["manifest_kind"]["const"], "direct_llm_readiness"
        )
        self.assertEqual(
            schema["$defs"]["artifactStatus"]["properties"]["digest"], {"type": "null"}
        )
        self.assertEqual(
            schema["properties"]["result_boundary"]["properties"]["status"]["const"],
            "not-evaluated",
        )


if __name__ == "__main__":
    unittest.main()

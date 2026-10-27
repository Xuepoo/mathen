import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts/build_mth0201_reproducibility_index.py"
ARTIFACT = ROOT / "data/reproducibility/mth-0201-reproducibility-index.json"
SCHEMA = ROOT / "schemas/reproducibility-index.schema.json"

spec = importlib.util.spec_from_file_location("mth0201_index", SCRIPT)
assert spec and spec.loader
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)


class Mth0201ReproducibilityIndexTests(unittest.TestCase):
    def test_checked_in_index_is_deterministic_and_valid(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        module.validate_index(value)
        self.assertEqual(value, module.build_index())

    def test_requested_work_items_and_boundaries_are_explicit(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(
            [item["id"] for item in value["work_items"]],
            [
                "MTH-0169",
                "MTH-0172",
                "MTH-0174",
                "MTH-0175",
                "MTH-0176",
                "MTH-0177",
                "MTH-0178",
                "MTH-0185",
                "MTH-0186",
                "MTH-0187",
                "MTH-0188",
                "MTH-0193",
                "MTH-0194",
                "MTH-0195",
                "MTH-0196",
                "MTH-0197",
                "MTH-0198",
            ],
        )
        self.assertFalse(value["canonical"])
        self.assertFalse(value["promotion_boundary"]["inference_allowed"])
        for item in value["work_items"]:
            self.assertFalse(item["boundary"]["canonical"])
            self.assertEqual(item["boundary"]["review_state"], "under-review")
            self.assertFalse(item["boundary"]["inference_allowed"])

    def test_agent_human_and_direct_llm_boundaries(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        items = {item["id"]: item for item in value["work_items"]}
        for item_id in ("MTH-0186", "MTH-0187", "MTH-0188", "MTH-0193", "MTH-0196"):
            provenance = items[item_id]["provenance"]
            self.assertEqual(provenance["reviewer_kind"], "agent")
            self.assertFalse(provenance["human_review"])
        for item_id in ("MTH-0177", "MTH-0188", "MTH-0193", "MTH-0196"):
            self.assertEqual(items[item_id]["provenance"]["human_stratum"], "empty")
        for item in value["work_items"]:
            if item.get("provenance", {}).get("direct_llm_status") == "not-evaluated":
                self.assertTrue(
                    any(
                        "direct-llm" in obs["name"].lower()
                        and obs["status"] == "not-evaluated"
                        for obs in item["observations"]
                    )
                )

    def test_file_digests_and_missing_historical_files_are_distinguished(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        files = {
            record["path"]: record
            for item in value["work_items"]
            for record in item["files"]
        }
        self.assertTrue(
            files["data/benchmark/mth-0195-independent-exploration.json"]["present"]
        )
        self.assertFalse(files["data/benchmark/mth-0169-exploration.json"]["present"])
        self.assertIsNone(files["data/benchmark/mth-0169-exploration.json"]["digest"])
        self.assertTrue(
            all(
                record["present"] == (record["digest"] is not None)
                for record in files.values()
            )
        )

    def test_schema_is_closed_and_declares_research_boundary(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["research_only"]["const"], True)
        self.assertEqual(schema["properties"]["canonical"]["const"], False)

    def test_sqlite_observation_is_explicitly_under_review(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        item = next(item for item in value["work_items"] if item["id"] == "MTH-0197")
        self.assertFalse(item["boundary"]["canonical"])
        self.assertEqual(item["boundary"]["review_state"], "under-review")


if __name__ == "__main__":
    unittest.main()

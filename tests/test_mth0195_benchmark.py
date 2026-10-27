import json
import unittest
from pathlib import Path

from scripts.build_mth0195_benchmark import (
    build_manifest,
    canonical_digest,
    validate_manifest,
)

ROOT = Path(__file__).parents[1]
ARTIFACT = ROOT / "data/benchmark/mth-0195-independent-exploration.json"
SCHEMA = ROOT / "schemas/independent-exploration-benchmark.schema.json"


class Mth0195BenchmarkTests(unittest.TestCase):
    def test_artifact_is_deterministic(self) -> None:
        value = json.loads(ARTIFACT.read_text(encoding="utf-8"))
        self.assertEqual(value, build_manifest())
        validate_manifest(ARTIFACT)

    def test_instances_are_independent_and_cover_kinds(self) -> None:
        value = build_manifest()
        tasks = value["task_cards"]
        self.assertEqual(len(tasks), 24)
        self.assertEqual(len({task["id"] for task in tasks}), 24)
        self.assertEqual(len({task["task_key"] for task in tasks}), 24)
        self.assertEqual(
            {task["kind"] for task in tasks},
            {"positive", "negative", "unknown", "counterexample", "composition"},
        )
        self.assertEqual(
            {task["domain"] for task in tasks},
            {"storage", "streaming", "orchestration", "isolation"},
        )
        self.assertEqual(len({task["input_digest"] for task in tasks}), 24)

    def test_partitions_and_exclusions(self) -> None:
        value = build_manifest()
        tasks = {task["id"]: task for task in value["task_cards"]}
        sets = value["partitions"]["sets"]
        self.assertEqual(set().union(*(set(ids) for ids in sets.values())), set(tasks))
        self.assertEqual(sum(len(ids) for ids in sets.values()), len(tasks))
        self.assertEqual(
            {task_id for task_id, task in tasks.items() if task["negative_knowledge"]},
            set(value["negative_knowledge"]["holdout_ids"]),
        )
        self.assertTrue(
            all(
                not tasks[task_id]["candidate_generation_allowed"]
                for task_id in value["negative_knowledge"][
                    "candidate_generation_exclusions"
                ]
            )
        )
        self.assertTrue(
            all(
                not tasks[task_id]["candidate_generation_allowed"]
                for task_id in sets["holdout"]
            )
        )

    def test_digests_close_evidence_and_domains(self) -> None:
        value = build_manifest()
        evidence_ids = {record["id"] for record in value["evidence_bundle"]["records"]}
        self.assertEqual(
            value["evidence_bundle"]["digest"],
            canonical_digest(value["evidence_bundle"]["records"]),
        )
        self.assertTrue(
            all(
                set(task["evidence_ids"]) <= evidence_ids
                for task in value["task_cards"]
            )
        )
        self.assertEqual(
            {item["id"] for item in value["task_card_digests"]},
            {task["id"] for task in value["task_cards"]},
        )
        for item in value["domain_slices"]:
            self.assertEqual(
                item["digest"],
                canonical_digest(
                    {key: item[key] for key in ("domain", "system_ids", "task_ids")}
                ),
            )

    def test_candidate_and_evaluation_boundaries(self) -> None:
        value = build_manifest()
        self.assertEqual(
            value["candidate_contract"],
            {
                "proven": False,
                "claim_status": "proposed",
                "canonical": False,
                "promotion_requires_human_review": True,
            },
        )
        direct = next(
            condition
            for condition in value["conditions"]
            if condition["id"] == "direct-llm"
        )
        self.assertEqual(direct["status"], "not-evaluated")
        self.assertFalse(direct["secret_safe_output"])
        self.assertTrue(
            all(
                metric["denominator"] == 0 and metric["value"] is None
                for metric in value["metrics"]
            )
        )

    def test_schema_is_closed(self) -> None:
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertFalse(schema["additionalProperties"])
        self.assertIn("candidate_contract", schema["required"])
        self.assertEqual(schema["properties"]["research_only"]["const"], True)


if __name__ == "__main__":
    unittest.main()

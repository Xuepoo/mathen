import copy
import unittest

from mathen.cards import validate_card
from mathen.evidence import ObservationEvidence


def scope_context() -> dict:
    unspecified = {"status": "unspecified", "values": [], "evidence_ids": []}
    specified = {
        "status": "specified",
        "values": ["fixture workload"],
        "evidence_ids": ["source"],
        "claim_type": "fact",
        "claim_status": "under-review",
    }
    return {
        "validity_scope": {
            "status": "specified",
            "systems": ["fixture"],
            "versions": ["commit-a"],
            "deployment_origins": [],
            "conditions": [],
            "exclusions": [],
            "evidence_ids": ["source"],
            "claim_type": "fact",
            "claim_status": "under-review",
        },
        "workload": specified,
        "runtime_conditions": copy.deepcopy(unspecified),
        "scale": copy.deepcopy(unspecified),
        "failure_conditions": copy.deepcopy(unspecified),
    }


def observation(kind: str = "benchmark") -> dict:
    return {
        "id": "run-a",
        "kind": kind,
        "title": "Bounded fixture observation",
        "uri": "https://example.test/run-a",
        "protocol": "Run the pinned fixture.",
        "system_commit": "commit-a",
        "environment": {"os": "Linux", "runtime": "Python 3.12"},
        "command": "true",
        "dataset": {"id": "fixture-dataset", "digest": "sha256:dataset"},
        "repetitions": 2,
        "metrics": {"latency_ms": None},
        "artifacts": [
            {
                "id": "log-a",
                "kind": "log",
                "path": "artifacts/run-a.log",
                "digest": "sha256:log",
            }
        ],
        "observation_version": "1",
        "workload": {"name": "fixture workload"},
        "conditions": {"mode": "controlled"},
        "provenance": {
            "run_id": "run-a",
            "source_revision": "commit-a",
            "protocol_digest": "sha256:protocol",
            "recorded_at": "2026-10-26T00:00:00Z",
            "runner": "local-runner-1",
            "toolchain": {"python": "3.12"},
        },
        "result_boundary": {
            "canonical": False,
            "promotion_requires_human_review": True,
            "storage_scope": "research",
            "limits": ["one fixture workload", "not a comparison"],
        },
        "result": {
            "status": "abstained",
            "summary": "Latency was not reported by the fixture.",
            "measurements": [
                {
                    "id": "latency",
                    "value": None,
                    "unit": "ms",
                    "status": "not-measured",
                }
            ],
            "abstention_reason": "The fixture emits no timing signal.",
        },
        "review": {"status": "unreviewed", "card_claim_refs": []},
        "scope_context": scope_context(),
    }


class ObservationEvidenceTests(unittest.TestCase):
    def test_observation_model_round_trips_detached_data(self) -> None:
        value = observation()
        model = ObservationEvidence.from_dict(value, {"run-a", "source"})
        value["result"]["summary"] = "changed"
        self.assertEqual(
            model.to_dict()["result"]["summary"],
            "Latency was not reported by the fixture.",
        )

    def test_card_accepts_bounded_observation_and_null_measurement(self) -> None:
        card = {
            "id": "fixture",
            "name": "Fixture",
            "summary": "A bounded observation fixture.",
            "scope": ["test"],
            "features": [
                {
                    "id": "feature",
                    "name": "Feature",
                    "category": "test",
                    "claim_type": "fact",
                    "description": "A fixture feature.",
                    "evidence_ids": ["source"],
                }
            ],
            "mathematical_views": [],
            "trade_offs": [],
            "evidence": [
                {
                    "id": "source",
                    "kind": "official-doc",
                    "title": "Fixture source",
                    "uri": "https://example.test/source",
                },
                observation(),
            ],
        }
        validate_card(card)

    def test_observation_rejects_unbounded_or_unreviewed_closure(self) -> None:
        value = observation()
        value["result_boundary"]["canonical"] = True
        with self.assertRaisesRegex(ValueError, "canonical"):
            ObservationEvidence.from_dict(value, {"run-a", "source"})

        value = observation()
        value["result"]["measurements"][0]["value"] = 0
        with self.assertRaisesRegex(ValueError, "nullability"):
            ObservationEvidence.from_dict(value, {"run-a", "source"})

        value = observation()
        value["review"] = {
            "status": "reviewed",
            "reviewer": "reviewer-a",
            "reviewed_at": "2026-10-26T00:00:00Z",
            "card_claim_refs": [],
        }
        with self.assertRaisesRegex(ValueError, "card_claim_refs"):
            ObservationEvidence.from_dict(value, {"run-a", "source"})

        value = observation()
        value["scope_context"]["workload"]["evidence_ids"] = ["outside"]
        with self.assertRaisesRegex(ValueError, "unknown evidence"):
            ObservationEvidence.from_dict(value, {"run-a", "source"})

    def test_failure_counterexample_and_negative_result_require_local_detail(
        self,
    ) -> None:
        for kind, field, detail in (
            (
                "fault-injection",
                "failure",
                {
                    "trigger": "kill worker",
                    "observed_behavior": "run stops",
                    "boundary": "one worker",
                    "evidence_ids": ["run-a"],
                },
            ),
            (
                "counterexample",
                "counterexample",
                {
                    "target_claim": "latency is always reported",
                    "condition": "empty fixture",
                    "observed_result": "no latency",
                    "implication": "claim is not established here",
                    "evidence_ids": ["run-a"],
                },
            ),
            (
                "negative-result",
                "negative_result",
                {
                    "question": "Does the fixture report latency?",
                    "result": "Not established",
                    "reason": "No timing signal was emitted.",
                    "evidence_ids": ["run-a"],
                },
            ),
        ):
            value = observation(kind)
            value[field] = detail
            ObservationEvidence.from_dict(value, {"run-a", "source"})
            value[field]["evidence_ids"] = ["outside"]
            with self.assertRaisesRegex(ValueError, "unknown evidence"):
                ObservationEvidence.from_dict(value, {"run-a", "source"})


if __name__ == "__main__":
    unittest.main()

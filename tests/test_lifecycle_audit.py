import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).parents[1]
SCRIPT = ROOT / "scripts" / "audit_lifecycle_status.py"
SPEC = importlib.util.spec_from_file_location("audit_lifecycle_status", SCRIPT)
assert SPEC and SPEC.loader
AUDIT = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = AUDIT
SPEC.loader.exec_module(AUDIT)


class LifecycleAuditTests(unittest.TestCase):
    def test_mth_0153_pilot_is_fixed_and_abstains(self) -> None:
        report = AUDIT.pilot_audit(ROOT / "data" / "systems")

        self.assertEqual(report["selected_cards"], list(AUDIT.PILOT_CARD_IDS))
        self.assertFalse(report["mutation_performed"])
        self.assertEqual(report["counts"]["lifecycle_records"], 14)
        self.assertEqual(
            report["statuses_by_surface"],
            {
                "features": {"observed": 7, "unknown/not-recorded": 32},
                "mathematical_views": {
                    "proposed": 7,
                    "unknown/not-recorded": 21,
                },
            },
        )
        boundaries = report["absence_of_evidence_boundaries"]
        self.assertTrue(boundaries["cards_outside_pilot_included"] is False)
        self.assertTrue(boundaries["status_not_inferred_from_claim_type"])
        self.assertTrue(boundaries["missing_lifecycle_is_unknown_not_recorded"])

    def test_pilot_report_round_trips_as_json(self) -> None:
        report = AUDIT.pilot_audit(ROOT / "data" / "systems")
        self.assertEqual(json.loads(json.dumps(report)), report)

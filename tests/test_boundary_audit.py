from pathlib import Path
import unittest

from authentic_controls_db.audit_boundaries import audit_evidence_boundaries


ROOT = Path(__file__).parents[1]


class BoundaryAuditTests(unittest.TestCase):
    def test_current_migration_debt_is_reported_without_changing_data(self) -> None:
        report = audit_evidence_boundaries(ROOT)
        self.assertEqual(report["audit"], "evidence-boundaries")
        self.assertEqual(report["stats"]["records"], 75)
        self.assertGreater(report["stats"]["simulator_only_authentic_claims"], 0)
        self.assertTrue(
            all(item["code"] == "authentic-claim-simulator-only" for item in report["findings"])
        )


if __name__ == "__main__":
    unittest.main()

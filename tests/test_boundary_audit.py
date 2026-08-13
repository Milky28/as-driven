import json
from pathlib import Path
import unittest

from as_driven_db.audit_boundaries import audit_evidence_boundaries


ROOT = Path(__file__).parents[1]


def _indexed_record_count() -> int:
    index = json.loads((ROOT / "data" / "v1" / "index.json").read_text(encoding="utf-8"))
    return len(index["records"])


class BoundaryAuditTests(unittest.TestCase):
    def test_current_migration_debt_is_reported_without_changing_data(self) -> None:
        report = audit_evidence_boundaries(ROOT)
        self.assertEqual(report["audit"], "evidence-boundaries")
        # Derived from the index so promoting a record does not fail this test.
        self.assertEqual(report["stats"]["records"], _indexed_record_count())
        self.assertGreater(report["stats"]["simulator_only_authentic_claims"], 0)
        self.assertTrue(
            all(item["code"] == "authentic-claim-simulator-only" for item in report["findings"])
        )


if __name__ == "__main__":
    unittest.main()

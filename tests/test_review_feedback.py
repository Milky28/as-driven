from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from as_driven_db.review_feedback import ReviewFeedbackError, publish_review_result


def _case(state: str = "promoted") -> dict:
    payload = {
        "schema_version": "1.0.0",
        "case_id": "github-example-project-7",
        "state": state,
        "issue": {
            "repository": "example/project",
            "number": 7,
            "url": "https://github.com/example/project/issues/7",
        },
        "updated_at": "2026-08-24T00:00:00+00:00",
    }
    if state == "promoted":
        payload["review_proposal"] = {
            "status": "promoted",
            "dataset_version": "1.2.3",
            "record_id": "example-car",
        }
    return payload


def _write_case(root: Path, state: str = "promoted") -> Path:
    cases = root / "build" / "review-cases"
    case_path = cases / "issue-7" / "case.json"
    case_path.parent.mkdir(parents=True)
    case_path.write_text(json.dumps(_case(state)), encoding="utf-8")
    return cases


class ReviewFeedbackTests(unittest.TestCase):
    def test_preview_never_calls_github_or_changes_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = _write_case(root)
            before = (cases / "issue-7" / "case.json").read_bytes()

            result = publish_review_result(
                root,
                cases,
                7,
                publisher=lambda *_args: self.fail("preview called GitHub"),
                readiness_checker=lambda *_args: ["push first"],
            )

            self.assertEqual("preview", result["status"])
            self.assertEqual(["push first"], result["blockers"])
            self.assertIn("dataset 1.2.3", result["comment"])
            self.assertEqual(before, (cases / "issue-7" / "case.json").read_bytes())

    def test_approved_result_comments_closes_and_records_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = _write_case(root)
            calls: list[tuple[str, int, str, str]] = []

            result = publish_review_result(
                root,
                cases,
                7,
                approved=True,
                publisher=lambda *args: calls.append(args),
                readiness_checker=lambda *_args: [],
            )

            self.assertEqual("published", result["status"])
            self.assertEqual(1, len(calls))
            self.assertEqual(("example/project", 7, "completed"), calls[0][:3])
            saved = json.loads((cases / "issue-7" / "case.json").read_text())
            self.assertEqual("published", saved["github_feedback"]["status"])
            self.assertEqual("completed", saved["github_feedback"]["close_reason"])

            with self.assertRaisesRegex(ReviewFeedbackError, "already published"):
                publish_review_result(
                    root,
                    cases,
                    7,
                    approved=True,
                    publisher=lambda *_args: self.fail("repeat called GitHub"),
                    readiness_checker=lambda *_args: [],
                )

    def test_approval_refuses_unpublished_release_state(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = _write_case(root)

            with self.assertRaisesRegex(ReviewFeedbackError, "push first"):
                publish_review_result(
                    root,
                    cases,
                    7,
                    approved=True,
                    publisher=lambda *_args: self.fail("blocked result called GitHub"),
                    readiness_checker=lambda *_args: ["push first"],
                )

    def test_duplicate_has_clear_non_corroboration_message(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = _write_case(root, "duplicate")

            result = publish_review_result(
                root,
                cases,
                7,
                readiness_checker=lambda *_args: [],
            )

            self.assertEqual("not planned", result["close_reason"])
            self.assertIn("byte-for-byte identical", result["comment"])
            self.assertIn("does not create a separate corroborating", result["comment"])

    def test_nonterminal_case_is_refused(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = _write_case(root, "identity-research")

            with self.assertRaisesRegex(ReviewFeedbackError, "not ready"):
                publish_review_result(
                    root,
                    cases,
                    7,
                    readiness_checker=lambda *_args: [],
                )


if __name__ == "__main__":
    unittest.main()

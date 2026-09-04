from __future__ import annotations

import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from as_driven_db.review_feedback import (
    ReviewFeedbackError,
    publication_blockers,
    publication_next_step,
    publish_review_result,
)


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
    def test_later_dataset_can_publish_an_earlier_promoted_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "v1").mkdir(parents=True)
            (root / "data" / "v1" / "index.json").write_text(
                json.dumps(
                    {
                        "dataset_version": "1.2.4",
                        "records": ["cars/example-car.json"],
                    }
                ),
                encoding="utf-8",
            )
            (root / "research").mkdir()
            for name in (
                "ams2-coverage-manifest.json",
                "simulator-disagreement-audit.json",
            ):
                (root / "research" / name).write_text(
                    json.dumps({"dataset_version": "1.2.4"}),
                    encoding="utf-8",
                )
            (root / "dist" / "site").mkdir(parents=True)
            (root / "dist" / "site" / "index.html").write_text(
                "test",
                encoding="utf-8",
            )
            git_results = [
                subprocess.CompletedProcess([], 0, "", ""),
                subprocess.CompletedProcess([], 0, "0\n", ""),
            ]

            with patch(
                "as_driven_db.review_feedback._run_git",
                side_effect=git_results,
            ):
                blockers = publication_blockers(root, _case())

            self.assertEqual([], blockers)

    def test_current_dataset_must_still_contain_the_promoted_record(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "v1").mkdir(parents=True)
            (root / "data" / "v1" / "index.json").write_text(
                json.dumps({"dataset_version": "1.2.4", "records": []}),
                encoding="utf-8",
            )
            with patch(
                "as_driven_db.review_feedback._run_git",
                return_value=subprocess.CompletedProcess([], 0, "0\n", ""),
            ):
                blockers = publication_blockers(root, _case())

            self.assertTrue(
                any("promoted record 'example-car' is absent" in item for item in blockers)
            )

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

    def test_existing_car_research_feedback_names_the_amendment(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            cases = _write_case(root)
            case_path = cases / "issue-7" / "case.json"
            case = json.loads(case_path.read_text(encoding="utf-8"))
            case["classification"] = "existing-car-research"
            case_path.write_text(json.dumps(case), encoding="utf-8")

            result = publish_review_result(
                root,
                cases,
                7,
                readiness_checker=lambda *_args: [],
            )

            self.assertIn("research was reviewed and incorporated", result["comment"])
            self.assertIn("checked-in research amendment", result["comment"])

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


class PublicationNextStepTests(unittest.TestCase):
    """The hint has to name the stage that is actually outstanding.

    It used to say "use Finalize release + run tests, then commit and push"
    whatever the blockers were, so a maintainer who had just finalized was told
    to finalize again.
    """

    def test_finalize_comes_before_committing(self) -> None:
        step = publication_next_step(
            [
                "AMS2 coverage manifest is not finalized for dataset 0.4.31",
                "tracked release files are not committed",
            ]
        )
        self.assertIn("Finalize release", step)

    def test_committing_comes_before_pushing(self) -> None:
        step = publication_next_step(
            [
                "tracked release files are not committed",
                "the current branch is 2 commit(s) ahead of its upstream; push first",
            ]
        )
        self.assertIn("commit", step.lower())
        self.assertNotIn("Finalize release", step)

    def test_a_pushed_release_is_asked_for_nothing_else(self) -> None:
        step = publication_next_step(
            ["the current branch is 1 commit(s) ahead of its upstream; push first"]
        )
        self.assertIn("push", step.lower())
        self.assertNotIn("Finalize release", step)

    def test_no_blockers_asks_for_nothing(self) -> None:
        self.assertEqual("", publication_next_step([]))

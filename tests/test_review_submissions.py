from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from as_driven_db.review_submissions import (
    SubmissionSyncError,
    extract_issue_answers,
    extract_observation_attachment,
    list_review_cases,
    sync_submissions,
)


ROOT = Path(__file__).parents[1]


def observation() -> dict:
    return {
        "$schema": "urn:as-driven:schema:v1:verification-observation",
        "schema_version": "1.0.0",
        "observation_id": "ams2.public-test-car.20260824t120000000z-abcd1234",
        "simulator": "ams2",
        "game_version": "1.6.9.91",
        "client_version": "SimHub 9.11.22; As Driven 0.19.0",
        "dataset_version": "0.4.20",
        "observed_at": "2026-08-24T12:00:00.0000000Z",
        "observer": "Test observer",
        "identity": {
            "telemetry_name": "Public Test Car",
            "telemetry_class": "TEST_CLASS",
            "internal_id": "Public Test Car",
        },
        "assists": {
            "automatic_clutch": "disabled",
            "automatic_shifting": "disabled",
            "automatic_throttle_blip": "unavailable",
        },
        "tests": {
            "move_off_without_physical_clutch": "no",
            "forward_gears": 6,
            "direct_gear_selection_behavior": "not-applicable",
            "clutchless_upshift": "yes",
            "automatic_cut": "unknown",
            "clutchless_downshift": "yes",
            "automatic_blip": "yes",
        },
        "cockpit": {
            "visible_shift_actuators": ["paddles"],
            "primary_shift_actuation": "sequential-paddles",
            "shift_pattern": "sequential",
            "wheel_rim": {
                "shape": "gt-formula",
                "integrated_display": "yes",
                "shift_lights": "yes",
                "open_top": "no",
            },
        },
        "review_status": "draft",
    }


def issue_body(url: str = "https://github.com/user-attachments/files/123/test.json") -> str:
    return f"""### Guided-drive draft JSON

[test.json]({url})

### What prompted this observation?

A car or implementation not currently recognized

### What exact real car do you believe this depicts?

2021 Example GT

### Identity or real-car evidence

_No response_

### Uncertainty or reviewer notes

Cockpit year is uncertain.
"""


def issue(number: int = 17) -> dict:
    return {
        "number": number,
        "title": "[Observation]: AMS2 — Public Test Car",
        "body": issue_body(),
        "url": f"https://github.com/example/project/issues/{number}",
        "labels": [{"name": "observation-received"}],
        "createdAt": "2026-08-24T12:01:00Z",
        "updatedAt": "2026-08-24T12:01:00Z",
    }


class ReviewSubmissionTests(unittest.TestCase):
    def test_extracts_one_strict_github_json_attachment_and_answers(self) -> None:
        attachment = extract_observation_attachment(issue_body())
        self.assertEqual("test.json", attachment["filename"])
        self.assertTrue(attachment["url"].startswith("https://github.com/user-attachments/"))
        answers = extract_issue_answers(issue_body())
        self.assertEqual("2021 Example GT", answers["proposed_identity"])
        self.assertIsNone(answers["identity_evidence"])
        self.assertEqual("Cockpit year is uncertain.", answers["uncertainty"])

    def test_rejects_non_github_or_multiple_attachments(self) -> None:
        with self.assertRaises(SubmissionSyncError):
            extract_observation_attachment(issue_body("https://example.com/test.json"))
        duplicate = issue_body() + "\n[test2.json](https://github.com/user-attachments/files/124/test2.json)\n"
        # The second link is outside the attachment section, so it cannot smuggle
        # another payload into this case.
        self.assertEqual("test.json", extract_observation_attachment(duplicate)["filename"])
        within_section = issue_body().replace(
            "\n### What prompted",
            "\n[test2.json](https://github.com/user-attachments/files/124/test2.json)\n\n### What prompted",
        )
        with self.assertRaises(SubmissionSyncError):
            extract_observation_attachment(within_section)

    def test_sync_intakes_stages_and_then_skips_an_unchanged_issue(self) -> None:
        raw = (json.dumps(observation(), indent=2) + "\n").encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            cases_dir = temp / "cases"
            inbox = temp / "inbox"

            def load_issues(repository: str, label: str) -> list[dict]:
                self.assertEqual("example/project", repository)
                self.assertEqual("observation-received", label)
                return [issue()]

            first = sync_submissions(
                ROOT,
                repository="example/project",
                cases_directory=cases_dir,
                inbox=inbox,
                issue_loader=load_issues,
                attachment_fetcher=lambda _: raw,
            )
            self.assertEqual(1, first["processed"])
            self.assertEqual(0, first["error"])
            case_dir = cases_dir / "issue-17"
            for name in ("case.json", "issue.json", "submission.json", "receipt.json", "staged.json"):
                self.assertTrue((case_dir / name).is_file(), name)
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("new-identity", case["classification"])
            self.assertEqual("identity-research", case["state"])
            self.assertTrue(case["research"]["required"])
            self.assertEqual("2021 Example GT", case["issue"]["answers"]["proposed_identity"])
            self.assertEqual("Public Test Car", case["observation"]["identity"]["telemetry_name"])

            second = sync_submissions(
                ROOT,
                repository="example/project",
                cases_directory=cases_dir,
                inbox=inbox,
                issue_loader=load_issues,
                attachment_fetcher=lambda _: self.fail("unchanged cases must not redownload"),
            )
            self.assertEqual(0, second["processed"])
            self.assertEqual(1, second["skipped"])

            queue = list_review_cases(cases_dir)
            self.assertEqual(1, len(queue))
            self.assertEqual(17, queue[0]["issue"])
            self.assertEqual("not-started", queue[0]["research"])

    def test_invalid_submission_becomes_a_retryable_error_case(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            result = sync_submissions(
                ROOT,
                repository="example/project",
                cases_directory=temp / "cases",
                inbox=temp / "inbox",
                issue_loader=lambda _repo, _label: [issue()],
                attachment_fetcher=lambda _: b'{"not":"an observation"}\n',
            )
            self.assertEqual(1, result["error"])
            case = json.loads(
                (temp / "cases" / "issue-17" / "case.json").read_text(encoding="utf-8")
            )
            self.assertEqual("intake-error", case["state"])
            self.assertIn("schema validation failed", case["error"])
            self.assertFalse((temp / "inbox").exists())


if __name__ == "__main__":
    unittest.main()


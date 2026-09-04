from __future__ import annotations

import json
from pathlib import Path
import shutil
import tempfile
import unittest

from as_driven_db.review_submissions import (
    CASE_SCHEMA_VERSION,
    _case_is_current,
    allowed_case_actions,
    SubmissionSyncError,
    extract_issue_answers,
    extract_observation_attachment,
    list_review_cases,
    sync_submissions,
)
from as_driven_db.research_handoff import (
    ResearchHandoffError,
    discover_research_results,
    generate_research_briefs,
    import_research_result,
)
from as_driven_db.importers.observation import import_observation
from as_driven_db.review_proposal import (
    _candidate_source,
    _existing_authentic_control_decisions,
    _preserve_accept_from_drive,
    _same_simulator_disposition,
    _simulator_overrides,
    generate_driver_summary,
    generate_driver_summary_proposal,
    prepare_review_proposal,
)
from as_driven_db.review_promotion import promote_review_case


ROOT = Path(__file__).parents[1]

CONTROL_PATHS = (
    "/authentic_controls/transmission/forward_gears",
    "/authentic_controls/transmission/gearbox_type",
    "/authentic_controls/transmission/shift_actuation",
    "/authentic_controls/transmission/shift_pattern",
    "/authentic_controls/transmission/first_gear_position",
    "/authentic_controls/transmission/upshift/clutch",
    "/authentic_controls/transmission/upshift/throttle_lift",
    "/authentic_controls/transmission/upshift/automatic_cut",
    "/authentic_controls/transmission/upshift/manual_blip",
    "/authentic_controls/transmission/upshift/automatic_blip",
    "/authentic_controls/transmission/downshift/clutch",
    "/authentic_controls/transmission/downshift/throttle_lift",
    "/authentic_controls/transmission/downshift/automatic_cut",
    "/authentic_controls/transmission/downshift/manual_blip",
    "/authentic_controls/transmission/downshift/automatic_blip",
    "/authentic_controls/transmission/standing_start_clutch",
    "/authentic_controls/steering/wheel_rim/shape",
    "/authentic_controls/steering/wheel_rim/integrated_display",
    "/authentic_controls/steering/wheel_rim/shift_lights",
    "/authentic_controls/steering/wheel_rim/open_top",
)


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
        "title": "[Observation]: AMS2 - Public Test Car",
        "body": issue_body(),
        "url": f"https://github.com/example/project/issues/{number}",
        "labels": [{"name": "observation-received"}],
        "createdAt": "2026-08-24T12:01:00Z",
        "updatedAt": "2026-08-24T12:01:00Z",
    }


def research_result(case_id: str) -> dict:
    return {
        "$schema": "../../../schema/v1/submission-research-result.schema.json",
        "schema_version": "1.0.0",
        "case_id": case_id,
        "research_status": "complete",
        "researched_at": "2026-08-24T14:00:00Z",
        "researcher": {
            "name": "Test researcher",
            "kind": "ai-assisted",
            "model": "test-model",
        },
        "identity": {
            "status": "established",
            "record_action": "create-new",
            "record_id": "public-test-car-2021",
            "display_name": "Public Test Car 2021",
            "manufacturer": "Example",
            "model": "Public Test Car",
            "year": {"from": 2021, "label": "2021 Public Test Car"},
            "class": "Example GT",
            "real_world_identity_notes": "Exact 2021 example specification.",
            "confidence": "high",
            "basis": "The manufacturer page identifies the exact model and year.",
            "confusion_risks": ["Do not confuse it with the 2020 model."],
        },
        "sources": [
            {
                "source_id": "example.public-test-car.2021",
                "title": "Public Test Car 2021 technical data",
                "publisher": "Example",
                "author": None,
                "url": "https://example.invalid/public-test-car-2021",
                "archive_url": None,
                "source_type": "manufacturer",
                "published_or_updated_at": "2021-01-01",
                "retrieved_at": "2026-08-24",
                "reuse_status": "facts-only-review",
                "exact_scope": "Names the 2021 race car, not the adjacent model.",
                "locators": [
                    {
                        "locator": "Technical data, identity heading",
                        "quote": "Public Test Car 2021",
                        "supports": ["/identity/manufacturer", "/identity/model", "/identity/year"],
                    }
                ],
                "notes": "Candidate source for maintainer registration.",
            }
        ],
        "claims": [
            {
                "path": "/identity/manufacturer",
                "finding": "established",
                "proposed_value": "Example",
                "confidence": "high",
                "source_refs": ["example.public-test-car.2021"],
                "basis": "The exact-car manufacturer page names Example.",
            },
            {
                "path": "/identity/model",
                "finding": "established",
                "proposed_value": "Public Test Car",
                "confidence": "high",
                "source_refs": ["example.public-test-car.2021"],
                "basis": "The exact-car manufacturer page names the model.",
            },
            {
                "path": "/identity/year",
                "finding": "established",
                "proposed_value": {"from": 2021, "label": "2021 Public Test Car"},
                "confidence": "high",
                "source_refs": ["example.public-test-car.2021"],
                "basis": "The exact-car manufacturer page names the year.",
            }
        ],
        "open_questions": [],
        "notes": "Ready for human review, not promotion.",
    }


def completed_research_result(case_id: str) -> dict:
    completed = research_result(case_id)
    completed["claims"].extend(
        {
            "path": path,
            "finding": "not-established",
            "proposed_value": None if path.endswith("/forward_gears") else "unknown",
            "confidence": "low",
            "source_refs": ["example.public-test-car.2021"],
            "basis": "The reviewed exact-car source does not establish this field.",
        }
        for path in CONTROL_PATHS
    )
    return completed


class ReviewSubmissionTests(unittest.TestCase):
    def test_existing_baseline_changes_are_generated_as_review_decisions(self) -> None:
        path = "/authentic_controls/transmission/downshift/clutch"
        existing = {
            "authentic_controls": {
                "transmission": {"downshift": {"clutch": "not-required"}},
                "steering": {"wheel_rim": {"open_top": "unknown"}},
            }
        }
        real_controls = {
            "transmission": {"downshift": {"clutch": "optional"}},
            "steering": {"wheel_rim": {"open_top": "no"}},
        }
        result = {
            "claims": [
                {
                    "path": path,
                    "finding": "established",
                    "proposed_value": "optional",
                    "confidence": "medium",
                    "source_refs": ["exact.car.report"],
                    "basis": "Exact-car reporting calls clutch use optional.",
                },
                {
                    "path": "/authentic_controls/steering/wheel_rim/open_top",
                    "finding": "established",
                    "proposed_value": "no",
                    "confidence": "high",
                    "source_refs": ["exact.cockpit.photo"],
                    "basis": "The exact-car cockpit image shows a closed rim.",
                },
            ]
        }

        accepted, corrections, effective = _existing_authentic_control_decisions(
            existing, real_controls, result
        )

        self.assertEqual(
            ["/authentic_controls/steering/wheel_rim/open_top"], accepted
        )
        self.assertEqual(path, corrections[0]["path"])
        self.assertEqual("not-required", corrections[0]["from"])
        self.assertEqual("optional", corrections[0]["to"])
        self.assertEqual(
            "optional", effective["transmission"]["downshift"]["clutch"]
        )
        self.assertEqual("no", effective["steering"]["wheel_rim"]["open_top"])

    def test_prepare_review_preserves_explicit_drive_acceptance(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory) / "issue-49"
            case_dir.mkdir()
            (case_dir / "review-manifest.proposed.json").write_text(
                json.dumps(
                    {
                        "records": [
                            {
                                "record_id": "nissan-r390-gt1",
                                "accept_from_drive": [
                                    "/authentic_controls/steering/wheel_rim/shape"
                                ],
                                "game_version_correction": {
                                    "observed": "unknown",
                                    "verified": "24725083",
                                    "basis": "The installed manifest spans the drive.",
                                },
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )
            manifest = {
                "records": [
                    {
                        "record_id": "nissan-r390-gt1",
                        "accept_from_drive": [
                            "/authentic_controls/steering/wheel_rim/open_top"
                        ],
                    }
                ]
            }

            _preserve_accept_from_drive(case_dir, manifest)

            self.assertEqual(
                [
                    "/authentic_controls/steering/wheel_rim/open_top",
                    "/authentic_controls/steering/wheel_rim/shape",
                ],
                manifest["records"][0]["accept_from_drive"],
            )
            self.assertEqual(
                "24725083",
                manifest["records"][0]["game_version_correction"]["verified"],
            )

    def test_candidate_source_normalizes_em_dashes_before_tracking(self) -> None:
        source = research_result("example")["sources"][0]
        source["title"] = "LOTUS 23\u2014FORM FOLLOWS FUNCTION"
        source["notes"] = "Exact-car evidence\u2014review before promotion."

        candidate = _candidate_source(source)

        self.assertEqual("LOTUS 23 - FORM FOLLOWS FUNCTION", candidate["title"])
        self.assertNotIn("\u2014", candidate["notes"])

    def test_review_preserves_simulator_only_manual_blip_result(self) -> None:
        submitted = observation()
        submitted["tests"].update(
            {
                "coast_downshift": "no",
                "clutchless_downshift": "yes",
                "automatic_blip": "no",
            }
        )
        staged = import_observation(submitted)
        staged_controls = staged["record"]["authentic_controls"]
        real_controls = json.loads(json.dumps(staged_controls))

        overrides = _simulator_overrides(staged_controls, real_controls, staged)

        manual_blip = next(
            override
            for override in overrides
            if override["path"]
            == "/authentic_controls/transmission/downshift/manual_blip"
        )
        self.assertEqual("required", manual_blip["value"])
        self.assertIn("simulator behavior", manual_blip["condition"])

    def test_repeat_drive_becomes_an_explicit_audited_correction(self) -> None:
        submitted = observation()
        submitted["tests"].update(
            {
                "coast_downshift": "no",
                "clutchless_downshift": "yes",
                "automatic_blip": "no",
            }
        )
        staged = import_observation(submitted)
        simulator = staged["record"]["simulators"][0]
        live_source = staged["source"]["source_id"]
        existing = json.loads(json.dumps(staged["record"]))
        existing["simulators"][0]["overrides"] = []
        existing["simulators"][0]["source_refs"] = ["example.real", live_source]

        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "data" / "v1" / "cars").mkdir(parents=True)
            (root / "curation").mkdir()
            (root / "data" / "v1" / "sources.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "sources": [
                            {
                                "source_id": "example.real",
                                "source_type": "manufacturer",
                            },
                            {
                                "source_id": live_source,
                                "source_type": "in-game-observation",
                            },
                        ],
                    }
                ),
                encoding="utf-8",
            )
            observed_through = "SimHub guided verification observation prior-drive"
            (root / "curation" / "ams2-approved-public-test-car.json").write_text(
                json.dumps({"observed_through": observed_through}),
                encoding="utf-8",
            )
            entry = {
                "record_id": "public-test-car",
                "control_overrides": {},
                "simulator_overrides": simulator["overrides"],
            }

            _same_simulator_disposition(
                root,
                {"classification": "curated-identity-comparison"},
                staged,
                entry,
                existing,
            )

            correction = entry["correct_existing_simulator"]
            self.assertEqual(live_source, correction["supersedes_source_ref"])
            self.assertEqual(
                observed_through, correction["supersedes_observed_through"]
            )
            self.assertEqual(
                [
                    "/overrides/authentic_controls/transmission/downshift/"
                    "manual_blip"
                ],
                correction["corrected_behavior_paths"],
            )
            self.assertNotIn("compatible_implementation", entry)

    def sync_test_case_for_root(self, root: Path, cases: Path) -> Path:
        raw = (json.dumps(observation(), indent=2) + "\n").encode("utf-8")
        sync_submissions(
            root,
            repository="example/project",
            cases_directory=cases,
            inbox=cases.parent / "inbox",
            issue_loader=lambda _repo, _label: [issue()],
            attachment_fetcher=lambda _: raw,
        )
        return cases / "issue-17"

    def sync_test_case(self, temp: Path) -> Path:
        return self.sync_test_case_for_root(ROOT, temp / "cases")

    def prepare_promotable_case(
        self, repository: Path
    ) -> tuple[Path, Path, dict]:
        shutil.copytree(ROOT / "data", repository / "data")
        shutil.copytree(ROOT / "curation", repository / "curation")
        shutil.copytree(ROOT / "schema", repository / "schema")
        cases = repository / "build" / "review-cases"
        case_dir = self.sync_test_case_for_root(repository, cases)
        generate_research_briefs(repository, cases, {17})
        result_path = repository / "completed-research.json"
        result_path.write_text(
            json.dumps(
                completed_research_result("github-example-project-17"),
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        import_research_result(repository, cases, 17, result_path)
        proposal = prepare_review_proposal(repository, cases, 17)
        return cases, case_dir, proposal

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
            self.assertEqual("not-published", queue[0]["publication_status"])
            self.assertEqual("identity-research", queue[0]["display_state"])
            self.assertEqual(
                ["generate-research-brief", "import-research"],
                queue[0]["allowed_actions"],
            )

            case["github_feedback"] = {"status": "published"}
            (case_dir / "case.json").write_text(
                json.dumps(case, indent=2) + "\n", encoding="utf-8"
            )
            published = list_review_cases(cases_dir)[0]
            self.assertEqual("published", published["display_state"])
            self.assertEqual([], published["allowed_actions"])

    def test_issue_edit_keeps_the_original_attachment_classification(self) -> None:
        raw = (json.dumps(observation(), indent=2) + "\n").encode("utf-8")
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            cases_dir = temp / "cases"
            inbox = temp / "inbox"
            original_issue = issue()
            sync_submissions(
                ROOT,
                repository="example/project",
                cases_directory=cases_dir,
                inbox=inbox,
                issue_loader=lambda _repo, _label: [original_issue],
                attachment_fetcher=lambda _: raw,
            )

            edited_issue = issue()
            edited_issue["updatedAt"] = "2026-08-24T13:00:00Z"
            edited_issue["body"] = edited_issue["body"].replace(
                "Cockpit year is uncertain.",
                "Cockpit year is now confirmed.",
            )
            result = sync_submissions(
                ROOT,
                repository="example/project",
                cases_directory=cases_dir,
                inbox=inbox,
                issue_loader=lambda _repo, _label: [edited_issue],
                attachment_fetcher=lambda _: raw,
            )

            self.assertEqual(1, result["processed"])
            case = json.loads(
                (cases_dir / "issue-17" / "case.json").read_text(encoding="utf-8")
            )
            self.assertEqual("new-identity", case["classification"])
            self.assertEqual("identity-research", case["state"])
            self.assertEqual(
                "Cockpit year is now confirmed.",
                case["issue"]["answers"]["uncertainty"],
            )
            receipt = json.loads(
                (cases_dir / "issue-17" / "receipt.json").read_text(encoding="utf-8")
            )
            self.assertEqual("new-identity", receipt["status"])
            self.assertEqual(1, len(list(inbox.glob("*.receipt.json"))))

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

    def test_research_brief_packages_boundaries_leads_and_a_result_template(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            generated = generate_research_briefs(
                ROOT,
                temp / "cases",
                {17},
            )
            self.assertEqual(1, len(generated))
            brief = (case_dir / "research-brief.md").read_text(encoding="utf-8")
            self.assertIn("Identity first, simulator behavior second", brief)
            self.assertIn("not-established", brief)
            self.assertIn("do not edit `data/v1`", brief.lower())
            self.assertIn("Public Test Car", brief)
            self.assertIn(
                "/authentic_controls/transmission/upshift/clutch",
                brief,
            )
            self.assertIn(
                "Every source object must include all schema-required fields",
                brief,
            )
            self.assertIn(
                "include an established or `not-established` claim for every path",
                brief,
            )
            self.assertIn("## Required control claim paths", brief)
            self.assertIn("## Other permitted claim paths", brief)
            self.assertIn(
                "do not add `degrees_of_rotation` or `diameter_mm`",
                brief,
            )
            self.assertIn(
                "use JSON `null`, not the string `\"unknown\"`",
                brief,
            )
            self.assertIn(
                "Those registered values are canonical",
                brief,
            )
            template = json.loads(
                (case_dir / "research-result.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual("github-example-project-17", template["case_id"])
            schema = json.loads(
                (
                    ROOT
                    / "schema"
                    / "v1"
                    / "submission-research-result.schema.json"
                ).read_text(encoding="utf-8")
            )
            source_types = schema["properties"]["sources"]["items"]["properties"][
                "source_type"
            ]["enum"]
            self.assertIn("in-game-observation", source_types)
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("brief-ready", case["research"]["status"])
            self.assertEqual("research-brief.md", case["artifacts"]["research_brief"])
            self.assertIn(
                "import-research",
                list_review_cases(temp / "cases")[0]["allowed_actions"],
            )

    def test_refresh_discovers_a_completed_result_in_the_case_folder(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            generate_research_briefs(ROOT, temp / "cases", {17})
            (case_dir / "research-result.json").write_text(
                json.dumps(research_result("github-example-project-17"), indent=2) + "\n",
                encoding="utf-8",
            )

            discovered = discover_research_results(ROOT, temp / "cases")

            self.assertEqual(1, discovered["found"])
            self.assertEqual(1, len(discovered["imported"]))
            self.assertEqual([], discovered["errors"])
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("complete", case["research"]["status"])
            self.assertEqual("final-review", case["state"])
            self.assertEqual(
                "research-result.json",
                case["artifacts"]["research_result"],
            )

            unchanged = discover_research_results(ROOT, temp / "cases")
            self.assertEqual(0, unchanged["found"])

    def test_valid_research_result_moves_only_local_case_to_final_review(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            generate_research_briefs(ROOT, temp / "cases", {17})
            result_path = temp / "completed-research.json"
            result_path.write_text(
                json.dumps(research_result("github-example-project-17"), indent=2) + "\n",
                encoding="utf-8",
            )
            imported = import_research_result(
                ROOT,
                temp / "cases",
                17,
                result_path,
            )
            self.assertEqual("final-review", imported["state"])
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("complete", case["research"]["status"])
            self.assertEqual("final-review", case["state"])
            self.assertTrue((case_dir / "research-result.json").is_file())
            self.assertFalse(
                (ROOT / "data" / "v1" / "cars" / "public-test-car-2021.json").exists()
            )
            with self.assertRaises(ResearchHandoffError):
                import_research_result(ROOT, temp / "cases", 17, result_path)

    def test_research_result_rejects_wrong_case_and_unknown_source_refs(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            bad = research_result("github-example-project-999")
            bad["claims"][0]["source_refs"] = ["missing.source"]
            result_path = temp / "bad-research.json"
            result_path.write_text(json.dumps(bad), encoding="utf-8")
            with self.assertRaisesRegex(
                ResearchHandoffError,
                "expected 'github-example-project-17'",
            ):
                import_research_result(ROOT, temp / "cases", 17, result_path)
            self.assertFalse((case_dir / "research-result.json").exists())

    def test_research_result_rejects_an_unknown_claim_path_during_import(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            generate_research_briefs(ROOT, temp / "cases", {17})
            bad = research_result("github-example-project-17")
            bad["claims"][0]["path"] = "/authentic_controls/transmission/not_a_field"
            result_path = temp / "bad-path.json"
            result_path.write_text(json.dumps(bad), encoding="utf-8")

            with self.assertRaisesRegex(ResearchHandoffError, "unknown research field"):
                import_research_result(ROOT, temp / "cases", 17, result_path)
            self.assertFalse((case_dir / "research-result.json").exists())

    def test_numeric_unknown_error_explains_the_valid_research_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            generate_research_briefs(ROOT, temp / "cases", {17})
            bad = research_result("github-example-project-17")
            bad["claims"].append(
                {
                    "path": "/authentic_controls/steering/degrees_of_rotation",
                    "finding": "not-established",
                    "proposed_value": "unknown",
                    "confidence": "low",
                    "source_refs": ["example.public-test-car.2021"],
                    "basis": "The reviewed source does not establish rotation.",
                }
            )
            result_path = temp / "bad-numeric-unknown.json"
            result_path.write_text(json.dumps(bad), encoding="utf-8")

            with self.assertRaisesRegex(
                ResearchHandoffError,
                "numeric fields cannot use the string 'unknown'",
            ):
                import_research_result(ROOT, temp / "cases", 17, result_path)
            self.assertFalse((case_dir / "research-result.json").exists())

    def test_review_proposal_dry_runs_without_changing_curated_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            case_dir = self.sync_test_case(temp)
            generate_research_briefs(ROOT, temp / "cases", {17})
            result_path = temp / "completed-research.json"
            completed = completed_research_result("github-example-project-17")
            result_path.write_text(
                json.dumps(completed, indent=2) + "\n",
                encoding="utf-8",
            )
            import_research_result(ROOT, temp / "cases", 17, result_path)
            proposal = prepare_review_proposal(
                ROOT,
                temp / "cases",
                17,
                dataset_version="9.9.9",
            )
            self.assertEqual("passed", proposal["dry_run"])
            self.assertEqual("manifest-review", proposal["state"])
            manifest = json.loads(
                (case_dir / "review-manifest.proposed.json").read_text(encoding="utf-8")
            )
            self.assertEqual("9.9.9", manifest["dataset_version"])
            self.assertEqual(
                "public-test-car-2021",
                manifest["records"][0]["record_id"],
            )
            self.assertNotIn("archetype", manifest["records"][0])
            notes = manifest["records"][0]["control_notes"]
            self.assertIn("no real-car control values", notes[0])
            self.assertNotIn("X-TRAC 396B023", notes[0])
            self.assertIn(
                "2021 Public Test Car",
                manifest["records"][0]["confidence_notes"],
            )
            sources = json.loads(
                (case_dir / "sources.proposed.json").read_text(encoding="utf-8")
            )
            self.assertIn("Reviewed for", sources["sources"][0]["notes"])
            self.assertNotIn(" Supports ", sources["sources"][0]["notes"])
            self.assertFalse(
                any(
                    override["value"] == "unknown"
                    for override in manifest["records"][0]["simulator_overrides"]
                )
            )
            preview = json.loads(
                (case_dir / "preview-record.json").read_text(encoding="utf-8")
            )
            self.assertNotIn("archetype", preview)
            self.assertTrue((case_dir / "final-review.md").is_file())
            self.assertFalse(
                (ROOT / "data" / "v1" / "cars" / "public-test-car-2021.json").exists()
            )

    def test_exact_curated_comparison_can_prepare_an_audited_correction(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            cases, _, _ = self.prepare_promotable_case(repository)
            promote_review_case(repository, cases, 17, approved=True)
            record_path = (
                repository
                / "data"
                / "v1"
                / "cars"
                / "public-test-car-2021.json"
            )
            curated = json.loads(record_path.read_text(encoding="utf-8"))
            del curated["authentic_controls"]["steering"]["wheel_rim"]["open_top"]
            record_path.write_text(
                json.dumps(curated, indent=2) + "\n",
                encoding="utf-8",
            )
            source_path = repository / "data" / "v1" / "sources.json"
            sources = json.loads(source_path.read_text(encoding="utf-8"))
            real_source = next(
                source
                for source in sources["sources"]
                if source["source_id"] == "example.public-test-car.2021"
            )
            real_source["source_type"] = "official-simulator"
            source_path.write_text(
                json.dumps(sources, indent=2) + "\n",
                encoding="utf-8",
            )

            repeated = observation()
            repeated["observation_id"] = (
                "ams2.public-test-car.20260825t120000000z-efab5678"
            )
            repeated["observed_at"] = "2026-08-25T12:00:00.0000000Z"
            repeated["tests"]["automatic_blip"] = "no"
            raw = (json.dumps(repeated, indent=2) + "\n").encode("utf-8")
            comparison_cases = repository / "build" / "comparison-cases"
            sync_submissions(
                repository,
                repository="example/project",
                cases_directory=comparison_cases,
                inbox=repository / "build" / "comparison-inbox",
                issue_loader=lambda _repo, _label: [issue(18)],
                attachment_fetcher=lambda _: raw,
            )

            comparison_dir = comparison_cases / "issue-18"
            case = json.loads(
                (comparison_dir / "case.json").read_text(encoding="utf-8")
            )
            self.assertEqual("review-needed", case["state"])
            self.assertEqual("curated-identity-comparison", case["classification"])
            self.assertEqual(["prepare-review"], allowed_case_actions(case))

            proposal = prepare_review_proposal(repository, comparison_cases, 18)

            self.assertEqual("passed", proposal["dry_run"])
            self.assertEqual("manifest-review", proposal["state"])
            manifest = json.loads(
                (comparison_dir / "review-manifest.proposed.json").read_text(
                    encoding="utf-8"
                )
            )
            entry = manifest["records"][0]
            self.assertEqual("public-test-car-2021", entry["record_id"])
            self.assertIn(
                "has no independent real-world source",
                entry["confidence_notes"],
            )
            self.assertIn("correct_existing_simulator", entry)
            self.assertNotIn("compatible_implementation", entry)
            self.assertEqual(
                "unknown",
                entry["control_overrides"]["wheel_rim"]["open_top"],
            )
            self.assertTrue(
                any(
                    override["path"]
                    == "/authentic_controls/steering/wheel_rim/open_top"
                    and override["value"] == "not-applicable"
                    for override in entry["simulator_overrides"]
                ),
                entry["simulator_overrides"],
            )
            self.assertIn(
                "/overrides/authentic_controls/transmission/downshift/automatic_blip",
                entry["correct_existing_simulator"]["corrected_behavior_paths"],
            )
            self.assertFalse((comparison_dir / "research-result.json").exists())
            self.assertIn(
                "Correction of the existing simulator entry",
                (comparison_dir / "final-review.md").read_text(encoding="utf-8"),
            )
            index_path = repository / "data" / "v1" / "index.json"
            index = json.loads(index_path.read_text(encoding="utf-8"))
            index["dataset_version"] = proposal["dataset_version"]
            index_path.write_text(
                json.dumps(index, indent=2) + "\n",
                encoding="utf-8",
            )
            with self.assertRaisesRegex(
                ResearchHandoffError,
                "regenerate the proposal",
            ):
                promote_review_case(
                    repository,
                    comparison_cases,
                    18,
                    approved=True,
                )
            case = json.loads(
                (comparison_dir / "case.json").read_text(encoding="utf-8")
            )
            self.assertIn("prepare-review", allowed_case_actions(case))
            refreshed = prepare_review_proposal(repository, comparison_cases, 18)
            self.assertNotEqual(
                proposal["dataset_version"],
                refreshed["dataset_version"],
            )
            generated = generate_driver_summary_proposal(
                repository,
                comparison_cases,
                18,
            )
            self.assertEqual("passed", generated["dry_run"])
            promoted = promote_review_case(
                repository,
                comparison_cases,
                18,
                approved=True,
            )
            self.assertEqual("promoted", promoted["state"])
            promoted_record = json.loads(record_path.read_text(encoding="utf-8"))
            self.assertEqual(
                "not-applicable",
                next(
                    override["value"]
                    for override in promoted_record["simulators"][0]["overrides"]
                    if override["path"]
                    == "/authentic_controls/steering/wheel_rim/open_top"
                ),
            )

    def test_driver_summary_is_generated_after_review_and_dry_run_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            cases, case_dir, _proposal = self.prepare_promotable_case(repository)

            generated = generate_driver_summary_proposal(repository, cases, 17)

            self.assertEqual("passed", generated["dry_run"])
            manifest = json.loads(
                (case_dir / "review-manifest.proposed.json").read_text(
                    encoding="utf-8"
                )
            )
            preview = json.loads(
                (case_dir / "preview-record.json").read_text(encoding="utf-8")
            )
            summary = manifest["records"][0]["driver_summary"]
            self.assertEqual(summary, preview["driver_summary"])
            self.assertIn("not established", summary)
            self.assertTrue((case_dir / "driver-summary.md").is_file())
            self.assertIn(
                summary,
                (case_dir / "final-review.md").read_text(encoding="utf-8"),
            )
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("manifest-review", case["state"])
            self.assertEqual(
                "generated",
                case["review_proposal"]["driver_summary"]["status"],
            )

    def test_driver_summary_edit_is_normalized_saved_and_dry_run_again(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            cases, case_dir, _proposal = self.prepare_promotable_case(repository)

            edited = generate_driver_summary_proposal(
                repository,
                cases,
                17,
                driver_summary="  Use the clutch.\nThen lift for the shift.  ",
            )

            self.assertEqual("passed", edited["dry_run"])
            self.assertEqual("edited", edited["summary_status"])
            self.assertEqual(
                "Use the clutch. Then lift for the shift.", edited["summary"]
            )
            manifest = json.loads(
                (case_dir / "review-manifest.proposed.json").read_text(
                    encoding="utf-8"
                )
            )
            preview = json.loads(
                (case_dir / "preview-record.json").read_text(encoding="utf-8")
            )
            self.assertEqual(edited["summary"], manifest["records"][0]["driver_summary"])
            self.assertEqual(edited["summary"], preview["driver_summary"])
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual(
                "edited", case["review_proposal"]["driver_summary"]["status"]
            )

            preserved = generate_driver_summary_proposal(
                repository,
                cases,
                17,
                preserve_existing=True,
            )
            self.assertEqual("preserved", preserved["summary_status"])
            self.assertEqual(edited["summary"], preserved["summary"])

    def test_driver_summary_calls_out_cross_simulator_technique_disagreement(self) -> None:
        record = import_observation(observation())["record"]
        second = json.loads(json.dumps(record["simulators"][0]))
        second["simulator"] = "ac"
        second["overrides"] = [
            {
                "path": "/authentic_controls/transmission/upshift/automatic_cut",
                "value": "no",
                "condition": "Exact AC implementation observed without a cut.",
            }
        ]
        record["simulators"].append(second)

        summary, disagreements = generate_driver_summary(record)

        self.assertIn("upshift cut", disagreements)
        self.assertIn("follow the selected game's USE row", summary)

    def test_review_proposal_accepts_an_established_optional_control_field(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(ROOT / "data", repository / "data")
            shutil.copytree(ROOT / "curation", repository / "curation")
            shutil.copytree(ROOT / "schema", repository / "schema")
            cases = repository / "build" / "review-cases"
            case_dir = self.sync_test_case_for_root(repository, cases)
            generate_research_briefs(repository, cases, {17})
            result = completed_research_result("github-example-project-17")
            first_gear = next(
                claim
                for claim in result["claims"]
                if claim["path"]
                == "/authentic_controls/transmission/first_gear_position"
            )
            first_gear.update(
                {
                    "finding": "established",
                    "proposed_value": "down-left",
                    "confidence": "medium",
                    "basis": "The reviewed gate diagram puts first down and left.",
                }
            )
            result_path = repository / "completed-research.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            import_research_result(repository, cases, 17, result_path)

            proposal = prepare_review_proposal(repository, cases, 17)

            manifest = json.loads(Path(proposal["manifest"]).read_text(encoding="utf-8"))
            self.assertEqual(
                "down-left",
                manifest["records"][0]["control_overrides"]["first_gear_position"],
            )
            preview = json.loads(
                (case_dir / "preview-record.json").read_text(encoding="utf-8")
            )
            self.assertEqual(
                "down-left",
                preview["authentic_controls"]["transmission"]["first_gear_position"],
            )

    def test_a_deleted_issue_retires_its_case_instead_of_haunting_the_queue(self) -> None:
        """Sync only ever added, so a deleted issue stayed in the workbench.

        The case is marked rather than deleted. A short issue list is not proof
        that a contributor withdrew anything - a removed label, a rate limit or
        a filtered sync all look identical from here - and deleting the case
        would take the staged observation with it.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            cases = temp / "cases"
            (cases / "issue-19").mkdir(parents=True)
            (cases / "issue-19" / "case.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "issue": {"number": 19},
                        "state": "identity-research",
                        "classification": "new-identity",
                    }
                ),
                encoding="utf-8",
            )

            result = sync_submissions(
                ROOT,
                cases_directory=cases,
                inbox=temp / "inbox",
                issue_loader=lambda repository, label: [],
                absence_checker=lambda number: number == 19,
            )
            self.assertEqual([19], result["withdrawn"])

            case = json.loads((cases / "issue-19" / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("withdrawn", case["state"])
            self.assertIn("no longer exists", case["withdrawn_reason"])
            self.assertEqual([], allowed_case_actions(case))

    def test_a_sync_narrowed_to_one_issue_retires_nothing(self) -> None:
        # A filtered sync has no opinion about the issues it did not ask for.
        # Reading its silence as absence would retire the whole queue.
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            cases = temp / "cases"
            (cases / "issue-19").mkdir(parents=True)
            (cases / "issue-19" / "case.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "issue": {"number": 19},
                        "state": "identity-research",
                    }
                ),
                encoding="utf-8",
            )

            result = sync_submissions(
                ROOT,
                cases_directory=cases,
                inbox=temp / "inbox",
                issue_numbers={26},
                issue_loader=lambda repository, label: [],
                absence_checker=lambda number: True,
            )
            self.assertEqual([], result["withdrawn"])
            case = json.loads((cases / "issue-19" / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("identity-research", case["state"])

    def test_a_held_case_stops_being_current_once_its_game_is_registered(self) -> None:
        """Registering a simulator has to reach the cases already waiting.

        Nothing about the issue changes when a simulator is registered - same
        body, same attachment, same timestamp - so the sync reported such a case
        unchanged forever and the drive stayed blocked behind a decision that
        had already been taken. Re-running intake is what releases it, and this
        is what lets the sync reach intake at all.
        """
        with tempfile.TemporaryDirectory() as directory:
            case_dir = Path(directory) / "issue-28"
            case_dir.mkdir(parents=True)
            issue = {"updatedAt": "2026-08-26T19:42:00Z"}
            url = "https://github.com/user-attachments/files/1/drive.json"
            case = {
                "schema_version": CASE_SCHEMA_VERSION,
                "state": "blocked-on-simulator",
                "issue": {"number": 28, "updated_at": issue["updatedAt"]},
                "attachment": {"url": url},
                "artifacts": {
                    "issue": "issue.json",
                    "submission": "submission.json",
                    "receipt": "receipt.json",
                    "staged_bundle": "staged.json",
                },
                # Deliberately absent from the summary, as cases written before
                # the field was carried there have it.
                "observation": {"simulator": "other"},
            }
            (case_dir / "case.json").write_text(json.dumps(case), encoding="utf-8")
            for name in ("issue.json", "receipt.json", "staged.json"):
                (case_dir / name).write_text("{}", encoding="utf-8")

            (case_dir / "submission.json").write_text(
                json.dumps({"source_game_name": "RFactor2"}), encoding="utf-8"
            )
            self.assertFalse(
                _case_is_current(case_dir, issue, url),
                "a registered game must reopen the case waiting on it",
            )

            (case_dir / "submission.json").write_text(
                json.dumps({"source_game_name": "LeMansUltimate"}), encoding="utf-8"
            )
            self.assertTrue(
                _case_is_current(case_dir, issue, url),
                "a game still unregistered leaves the case exactly where it was",
            )

    def test_the_brief_asks_for_cockpit_photographs(self) -> None:
        """What the driver operates is a visual fact, so the brief asks to see it.

        The gate and the rim are the two things written sources routinely omit
        and a photograph routinely settles. Four records now disagree across
        simulators about a rim, every one of them on the same vocabulary
        boundary, so the brief carries the decision order and the instruction to
        hedge where the flat is slight rather than pick and be contradicted.
        """
        from as_driven_db.research_handoff import _research_questions

        questions = " ".join(
            _research_questions({"record": {"authentic_controls": {}}})
        ).lower()
        self.assertIn("cockpit or interior photographs", questions)
        self.assertIn("where first gear sits in the gate", questions)
        self.assertIn("molded grips at 9 and 3", questions)
        self.assertIn("fetch the full-resolution original", questions)
        # The distinction the first field report turned up: an agent that
        # cannot see a wheel reports the same not-established as one looking at
        # a genuinely ambiguous wheel, and only the second is a finding.
        self.assertIn("only one of them is a finding", questions)
        self.assertIn(
            "do not report a rim you could not see as a rim that cannot be decided",
            questions,
        )

    def test_a_researched_case_can_still_ask_for_a_new_brief(self) -> None:
        # The brief gains questions over time. A case that completed research
        # before one was added must be able to go round again, without the
        # existing result being discarded to do it.
        for state, forward in (("final-review", "prepare-review"),
                               ("manifest-review", "promote")):
            actions = allowed_case_actions(
                {"state": state, "research": {"status": "complete"}}
            )
            self.assertIn(forward, actions, state)
            self.assertIn("generate-research-brief", actions, state)
            self.assertIn("import-research", actions, state)
            self.assertEqual(forward, actions[0], "the forward action stays first")

        # Not offered where there is nothing to research or the work is done.
        for state in ("promoted", "released", "duplicate", "withdrawn",
                      "blocked-on-simulator"):
            self.assertNotIn(
                "generate-research-brief",
                allowed_case_actions({"state": state}),
                state,
            )

    def test_a_released_drive_is_staged_under_the_registered_simulator(self) -> None:
        """Releasing has to reach the bundle promotion reads, not only the queue.

        The case is filed by intake; the staged bundle is built separately from
        the observation as submitted, which still says `other` because the file
        on disk records what the client knew and is never rewritten. The case
        showed as rfactor2 while its record, source id and approval were all
        staged under `other`, and promotion refused a drive whose game had been
        registered hours earlier.
        """
        from as_driven_db.importers.observation import import_observation
        import tests.test_intake_observation as fixtures

        payload = fixtures.observation("Staged Release Probe")
        payload["observation_id"] = (
            "other.staged-release-probe.20260826t194202971z-890e7e56"
        )
        payload["simulator"] = "other"
        payload["source_game_name"] = "RFactor2"

        held = import_observation(payload)
        self.assertEqual("other", held["simulator"])
        self.assertEqual("RFactor2", held["source_game_name"])
        self.assertTrue(held["source"]["source_id"].startswith("other."))

        # What sync now does with a receipt that released the drive.
        released = import_observation(dict(payload, simulator="rfactor2"))
        self.assertEqual("rfactor2", released["simulator"])
        self.assertEqual("rfactor2", released["record"]["simulators"][0]["simulator"])
        self.assertTrue(released["source"]["source_id"].startswith("rfactor2."))
        self.assertEqual("rfactor2", released["approval"]["simulator"])

    def test_refusing_an_unregistered_drive_names_the_game(self) -> None:
        # The refusal offered to name the game and read a key the bundle has
        # never had, so it called every one of them an unnamed game - including
        # the ones whose draft named them plainly.
        from as_driven_db.importers.observation import import_observation
        from as_driven_db.promote_observation import build_promoted_record
        import tests.test_intake_observation as fixtures

        payload = fixtures.observation("Unregistered Probe")
        payload["observation_id"] = "other.unregistered-probe.20260826t194202971z-890e7e57"
        payload["simulator"] = "other"
        payload["source_game_name"] = "LeMansUltimate"
        bundle = import_observation(payload)

        with self.assertRaises(ValueError) as raised:
            build_promoted_record(
                bundle,
                {"record_id": bundle["record"]["record_id"]},
                approved_at="2026-08-26",
            )
        self.assertIn("LeMansUltimate", str(raised.exception))
        self.assertNotIn("unnamed game", str(raised.exception))

    def test_a_closed_issue_keeps_its_case(self) -> None:
        """Every completed case is a closed issue, and closed is not deleted.

        The issue query asks for open issues carrying the label, so a case that
        has been promoted and published is missing from it by design. Retiring
        on absence retired twelve finished contributions alongside the two
        deleted drives, which is why absence is verified against GitHub rather
        than inferred from the listing.
        """
        with tempfile.TemporaryDirectory() as directory:
            temp = Path(directory)
            cases = temp / "cases"
            (cases / "issue-1").mkdir(parents=True)
            (cases / "issue-1" / "case.json").write_text(
                json.dumps(
                    {
                        "schema_version": "1.0.0",
                        "issue": {"number": 1},
                        "state": "duplicate",
                        "classification": "exact-resubmission",
                        "github_feedback": {"status": "published"},
                    }
                ),
                encoding="utf-8",
            )

            asked: list[int] = []

            def absent(number: int) -> bool:
                asked.append(number)
                return True

            result = sync_submissions(
                ROOT,
                cases_directory=cases,
                inbox=temp / "inbox",
                issue_loader=lambda repository, label: [],
                absence_checker=absent,
            )
            # Finished work is exempt before GitHub is asked at all, so even a
            # checker that calls everything absent leaves it alone.
            self.assertEqual([], result["withdrawn"])
            self.assertEqual([], asked)
            case = json.loads((cases / "issue-1" / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("duplicate", case["state"])

    def test_review_proposal_refuses_a_dogleg_without_its_first_gear_side(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            shutil.copytree(ROOT / "data", repository / "data")
            shutil.copytree(ROOT / "curation", repository / "curation")
            shutil.copytree(ROOT / "schema", repository / "schema")
            cases = repository / "build" / "review-cases"
            case_dir = self.sync_test_case_for_root(repository, cases)
            generate_research_briefs(repository, cases, {17})
            result = completed_research_result("github-example-project-17")
            shift_pattern = next(
                claim
                for claim in result["claims"]
                if claim["path"]
                == "/authentic_controls/transmission/shift_pattern"
            )
            shift_pattern.update(
                {
                    "finding": "established",
                    "proposed_value": "dogleg-h",
                    "confidence": "medium",
                    "basis": "The source establishes a dogleg but not its side.",
                }
            )
            result_path = repository / "completed-research.json"
            result_path.write_text(json.dumps(result), encoding="utf-8")
            import_research_result(repository, cases, 17, result_path)

            with self.assertRaisesRegex(
                ResearchHandoffError,
                "cannot be proposed until research establishes",
            ):
                prepare_review_proposal(repository, cases, 17)

            self.assertFalse((case_dir / "review-manifest.proposed.json").exists())

    def test_explicit_approval_promotes_a_ready_case_and_allocates_a_batch(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            cases, case_dir, proposal = self.prepare_promotable_case(repository)

            with self.assertRaisesRegex(ResearchHandoffError, "--approve"):
                promote_review_case(repository, cases, 17, approved=False)
            self.assertFalse(
                (repository / "data" / "v1" / "cars" / "public-test-car-2021.json").exists()
            )

            promoted = promote_review_case(repository, cases, 17, approved=True)
            self.assertEqual("promoted", promoted["state"])
            self.assertEqual(proposal["dataset_version"], promoted["dataset_version"])
            self.assertTrue(Path(promoted["manifest"]).is_file())
            self.assertTrue(
                (repository / "data" / "v1" / "cars" / "public-test-car-2021.json").is_file()
            )
            self.assertTrue(
                (
                    repository
                    / "curation"
                    / "ams2-approved-public-test-car-2021.json"
                ).is_file()
            )
            registry = json.loads(
                (repository / "data" / "v1" / "sources.json").read_text(encoding="utf-8")
            )
            self.assertIn(
                "example.public-test-car.2021",
                {source["source_id"] for source in registry["sources"]},
            )
            case = json.loads((case_dir / "case.json").read_text(encoding="utf-8"))
            self.assertEqual("promoted", case["state"])
            with self.assertRaisesRegex(ResearchHandoffError, "not 'manifest-review'"):
                promote_review_case(repository, cases, 17, approved=True)
            self.assertFalse(
                (ROOT / "data" / "v1" / "cars" / "public-test-car-2021.json").exists()
            )

    def test_promotion_refuses_release_and_source_drift_before_writing(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            cases, _, proposal = self.prepare_promotable_case(repository)
            index_path = repository / "data" / "v1" / "index.json"
            original_index = json.loads(index_path.read_text(encoding="utf-8"))
            advanced_index = dict(original_index, dataset_version=proposal["dataset_version"])
            index_path.write_text(
                json.dumps(advanced_index, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ResearchHandoffError, "regenerate the proposal"):
                promote_review_case(repository, cases, 17, approved=True)
            self.assertFalse(
                (repository / "data" / "v1" / "cars" / "public-test-car-2021.json").exists()
            )

            index_path.write_text(
                json.dumps(original_index, indent=2) + "\n", encoding="utf-8"
            )
            sources_path = repository / "data" / "v1" / "sources.json"
            sources = json.loads(sources_path.read_text(encoding="utf-8"))
            conflicting = json.loads(
                (
                    repository
                    / "build"
                    / "review-cases"
                    / "issue-17"
                    / "sources.proposed.json"
                ).read_text(encoding="utf-8")
            )["sources"][0]
            conflicting = dict(conflicting, title="Conflicting registered title")
            sources["sources"].append(conflicting)
            sources_path.write_text(
                json.dumps(sources, indent=2) + "\n", encoding="utf-8"
            )
            with self.assertRaisesRegex(ResearchHandoffError, "differs from the registered"):
                promote_review_case(repository, cases, 17, approved=True)
            self.assertFalse(
                (repository / "data" / "v1" / "cars" / "public-test-car-2021.json").exists()
            )

    def test_review_proposal_reuses_matching_registered_sources(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repository = Path(directory) / "repository"
            cases, case_dir, _ = self.prepare_promotable_case(repository)
            source_proposal_path = case_dir / "sources.proposed.json"
            candidate = json.loads(
                source_proposal_path.read_text(encoding="utf-8")
            )["sources"][0]
            registry_path = repository / "data" / "v1" / "sources.json"
            registry = json.loads(registry_path.read_text(encoding="utf-8"))
            registry["sources"].append(candidate)
            registry_path.write_text(
                json.dumps(registry, indent=2) + "\n", encoding="utf-8"
            )

            prepare_review_proposal(repository, cases, 17)
            refreshed = json.loads(source_proposal_path.read_text(encoding="utf-8"))
            self.assertEqual([], refreshed["sources"])
            summary = (case_dir / "final-review.md").read_text(encoding="utf-8")
            self.assertIn("already registered", summary)


if __name__ == "__main__":
    unittest.main()

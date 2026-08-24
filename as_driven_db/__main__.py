from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit_boundaries import audit_evidence_boundaries
from .importers.ams2 import import_ams2_csv
from .importers.iracing import import_iracing_html
from .importers.observation import import_observation
from .intake_observation import IntakeError, intake_observation
from .promote import promote_approved_ams2
from .promote_observation import promote_observations
from .research_handoff import (
    ResearchHandoffError,
    generate_research_briefs,
    import_research_result,
)
from .review_proposal import prepare_review_proposal
from .review_promotion import promote_review_case
from .review_feedback import ReviewFeedbackError, publish_review_result
from .release_finalize import ReleaseFinalizeError, finalize_release
from .maintainer_workbench import (
    WorkbenchApplication,
    WorkbenchError,
    run_workbench,
)
from .review_submissions import (
    DEFAULT_LABEL,
    DEFAULT_REPOSITORY,
    SubmissionSyncError,
    list_review_cases,
    sync_submissions,
)
from .simhub import (
    audit_ams2_identities,
    review_unmatched_ams2_observations,
    write_alias_review_csv,
    write_unmatched_review_csv,
)
from .site import build_site
from .validate import validate_repository
from .schema_validation import validate_instance


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="as-driven-db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate the curated repository")
    validate.add_argument("--root", type=Path, default=Path.cwd())

    site = subparsers.add_parser(
        "build-site",
        help="render the curated database as one self-contained HTML page",
    )
    site.add_argument("--root", type=Path, default=Path.cwd())
    site.add_argument(
        "--output", type=Path, default=Path("dist") / "site" / "index.html"
    )

    boundaries = subparsers.add_parser(
        "audit-boundaries",
        help="report authentic-control claims supported only by simulator evidence",
    )
    boundaries.add_argument("--root", type=Path, default=Path.cwd())
    boundaries.add_argument("--output", type=Path)

    observation = subparsers.add_parser(
        "validate-observation",
        help="validate a staged guided-verification observation",
    )
    observation.add_argument("input", type=Path)
    observation.add_argument("--root", type=Path, default=Path.cwd())

    observation_import = subparsers.add_parser(
        "import-observation",
        help="stage a curated-record candidate from a guided-verification observation",
    )
    observation_import.add_argument("input", type=Path)
    observation_import.add_argument("--output", type=Path, required=True)
    observation_import.add_argument("--root", type=Path, default=Path.cwd())
    observation_import.add_argument(
        "--skip-validate",
        action="store_true",
        help="do not validate the input against the observation schema first",
    )

    observation_intake = subparsers.add_parser(
        "intake-observation",
        help="validate and classify one untrusted public observation draft",
    )
    observation_intake.add_argument("input", type=Path)
    observation_intake.add_argument("--root", type=Path, default=Path.cwd())
    observation_intake.add_argument(
        "--inbox", type=Path, default=Path("build") / "observation-intake"
    )

    submissions = subparsers.add_parser(
        "review-submissions",
        help="synchronize and inspect public observation review cases",
    )
    submission_actions = submissions.add_subparsers(
        dest="submission_action", required=True
    )
    submission_sync = submission_actions.add_parser(
        "sync",
        help="download GitHub observation issues, intake them, and stage review cases",
    )
    submission_sync.add_argument("--root", type=Path, default=Path.cwd())
    submission_sync.add_argument("--repo", default=DEFAULT_REPOSITORY)
    submission_sync.add_argument("--label", default=DEFAULT_LABEL)
    submission_sync.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    submission_sync.add_argument(
        "--inbox", type=Path, default=Path("build") / "observation-intake"
    )
    submission_sync.add_argument(
        "--issue",
        type=int,
        action="append",
        help="process only this issue number; may be repeated",
    )
    submission_sync.add_argument(
        "--json", action="store_true", help="print the synchronization result as JSON"
    )
    submission_queue = submission_actions.add_parser(
        "queue", help="list durable local review cases"
    )
    submission_queue.add_argument("--root", type=Path, default=Path.cwd())
    submission_queue.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    submission_queue.add_argument(
        "--json", action="store_true", help="print the queue as JSON"
    )
    research_brief = submission_actions.add_parser(
        "research-brief",
        help="generate case-specific AI/human research briefs and result templates",
    )
    research_brief.add_argument("--root", type=Path, default=Path.cwd())
    research_brief.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    research_brief.add_argument(
        "--issue",
        type=int,
        action="append",
        help="generate a brief for this issue; may be repeated (default: all pending)",
    )
    research_brief.add_argument(
        "--json", action="store_true", help="print generated brief metadata as JSON"
    )
    research_import = submission_actions.add_parser(
        "import-research",
        help="validate and attach one structured research result to a review case",
    )
    research_import.add_argument("issue", type=int)
    research_import.add_argument("input", type=Path)
    research_import.add_argument("--root", type=Path, default=Path.cwd())
    research_import.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    research_import.add_argument(
        "--replace",
        action="store_true",
        help="replace an existing local research result after explicit re-review",
    )
    research_import.add_argument(
        "--json", action="store_true", help="print the import result as JSON"
    )
    review_prepare = submission_actions.add_parser(
        "prepare-review",
        help="generate and dry-run a curation manifest and source proposal",
    )
    review_prepare.add_argument("issue", type=int)
    review_prepare.add_argument("--root", type=Path, default=Path.cwd())
    review_prepare.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    review_prepare.add_argument(
        "--dataset-version",
        help="proposed release version (default: increment the current patch version)",
    )
    review_prepare.add_argument(
        "--json", action="store_true", help="print proposal metadata as JSON"
    )
    review_promote = submission_actions.add_parser(
        "promote",
        help="promote one explicitly approved final-review proposal",
    )
    review_promote.add_argument("issue", type=int)
    review_promote.add_argument("--root", type=Path, default=Path.cwd())
    review_promote.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    review_promote.add_argument(
        "--approve",
        action="store_true",
        help="confirm that the maintainer reviewed and approves the generated proposal",
    )
    review_promote.add_argument(
        "--json", action="store_true", help="print promotion metadata as JSON"
    )
    review_publish = submission_actions.add_parser(
        "publish-result",
        help="preview or explicitly publish final feedback and close a GitHub issue",
    )
    review_publish.add_argument("issue", type=int)
    review_publish.add_argument("--root", type=Path, default=Path.cwd())
    review_publish.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    review_publish.add_argument(
        "--approve",
        action="store_true",
        help="publish the shown comment and close the issue after readiness checks",
    )
    review_publish.add_argument(
        "--json", action="store_true", help="print feedback metadata as JSON"
    )
    release_finalize = submission_actions.add_parser(
        "finalize-release",
        help="regenerate release outputs, refresh status references, and validate",
    )
    release_finalize.add_argument("--root", type=Path, default=Path.cwd())
    release_finalize.add_argument(
        "--test",
        action="store_true",
        help="also run the complete Python unit test suite",
    )
    release_finalize.add_argument(
        "--json", action="store_true", help="print finalization metadata as JSON"
    )
    workbench = submission_actions.add_parser(
        "workbench",
        help="run the local contribution review interface",
    )
    workbench.add_argument("--root", type=Path, default=Path.cwd())
    workbench.add_argument("--repo", default=DEFAULT_REPOSITORY)
    workbench.add_argument("--label", default=DEFAULT_LABEL)
    workbench.add_argument(
        "--cases-dir", type=Path, default=Path("build") / "review-cases"
    )
    workbench.add_argument(
        "--inbox", type=Path, default=Path("build") / "observation-intake"
    )
    workbench.add_argument("--host", default="127.0.0.1")
    workbench.add_argument("--port", type=int, default=8765)
    workbench.add_argument(
        "--no-open",
        action="store_true",
        help="print the local URL without opening the default browser",
    )

    ams2 = subparsers.add_parser("import-ams2", help="stage candidates from an AMS2 CSV export")
    ams2.add_argument("input", type=Path)
    ams2.add_argument("--output", type=Path, required=True)
    ams2.add_argument("--verified-game-version", default="1.5.5.2")
    ams2.add_argument("--source-id", default="ams2.coanda-sheet.v1.0.34")

    iracing = subparsers.add_parser("import-iracing", help="stage candidates from saved iRacing HTML")
    iracing.add_argument("input", type=Path)
    iracing.add_argument("--output", type=Path, required=True)
    iracing.add_argument("--source-id", default="iracing.support.transmission.2026-06-22")

    simhub = subparsers.add_parser(
        "audit-simhub-ams2",
        help="compare AMS2 candidates with SimHub-observed car identities",
    )
    simhub.add_argument("--candidates", type=Path, required=True)
    simhub.add_argument("--cars-dir", type=Path, required=True)
    simhub.add_argument("--output", type=Path, required=True)
    simhub.add_argument("--simhub-version", default="unknown")
    simhub.add_argument("--review-csv", type=Path)

    unmatched = subparsers.add_parser(
        "review-unmatched-ams2",
        help="correlate plugin unmatched-identity JSONL with staged AMS2 candidates",
    )
    unmatched.add_argument("--log", type=Path, required=True)
    unmatched.add_argument("--candidates", type=Path, required=True)
    unmatched.add_argument("--output", type=Path, required=True)
    unmatched.add_argument("--review-csv", type=Path)
    unmatched.add_argument("--data-dir", type=Path, default=Path("data/v1"))

    promote = subparsers.add_parser(
        "promote-ams2",
        help="promote explicitly approved AMS2 candidates into curated records",
    )
    promote.add_argument("--candidates", type=Path, required=True)
    promote.add_argument("--audit", type=Path, required=True)
    promote.add_argument("--approvals", type=Path, required=True)
    promote.add_argument("--data-dir", type=Path, default=Path("data/v1"))

    promote_observation = subparsers.add_parser(
        "promote-observation",
        help="promote reviewed guided-verification bundles into curated records",
    )
    promote_observation.add_argument("review", type=Path)
    promote_observation.add_argument("--root", type=Path, default=Path.cwd())
    promote_observation.add_argument("--data-dir", type=Path, default=Path("data/v1"))
    promote_observation.add_argument("--curation-dir", type=Path, default=Path("curation"))

    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)

    if args.command == "validate":
        errors = validate_repository(args.root.resolve())
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            print(f"Validation failed with {len(errors)} error(s).")
            return 1
        print("Validation passed.")
        return 0

    if args.command == "build-site":
        page = build_site(args.root.resolve())
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(page, encoding="utf-8")
        print(f"Wrote {len(page):,} bytes to {args.output}")
        return 0

    if args.command == "audit-boundaries":
        payload = audit_evidence_boundaries(args.root.resolve())
        if args.output:
            _write_json(args.output, payload)
            print(f"Wrote evidence-boundary audit to {args.output}")
        stats = payload["stats"]
        print(
            f"Audited {stats['records']} records: "
            f"{stats['simulator_only_authentic_claims']} simulator-only authentic "
            f"claim(s) across {stats['affected_records']} record(s)."
        )
        return 0

    if args.command == "validate-observation":
        try:
            payload = json.loads(args.input.read_text(encoding="utf-8-sig"))
            schema_path = (
                args.root.resolve()
                / "schema"
                / "v1"
                / "verification-observation.schema.json"
            )
            schema = json.loads(schema_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exception:
            print(f"ERROR: Could not read observation or schema: {exception}")
            return 1
        errors = validate_instance(payload, schema, str(args.input))
        if errors:
            for error in errors:
                print(f"ERROR: {error}")
            print(f"Observation validation failed with {len(errors)} error(s).")
            return 1
        print("Observation validation passed.")
        return 0

    if args.command == "import-observation":
        try:
            observation = json.loads(args.input.read_text(encoding="utf-8-sig"))
        except (OSError, json.JSONDecodeError) as exception:
            print(f"ERROR: Could not read observation: {exception}")
            return 1
        if not args.skip_validate:
            schema_path = (
                args.root.resolve()
                / "schema"
                / "v1"
                / "verification-observation.schema.json"
            )
            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exception:
                print(f"ERROR: Could not read observation schema: {exception}")
                return 1
            schema_errors = validate_instance(observation, schema, str(args.input))
            if schema_errors:
                for error in schema_errors:
                    print(f"ERROR: {error}")
                print(f"Observation validation failed with {len(schema_errors)} error(s).")
                return 1
        bundle = import_observation(observation)
        _write_json(args.output, bundle)
        print(
            f"Staged record candidate {bundle['record']['record_id']} from "
            f"observation {bundle['observation_id']} to {args.output}"
        )
        for note in bundle["review_notes"]:
            print(f"REVIEW: {note}")
        return 0

    if args.command == "intake-observation":
        try:
            receipt = intake_observation(
                args.root.resolve(), args.input, args.inbox
            )
        except IntakeError as exception:
            print(f"ERROR: {exception}")
            return 1
        print(json.dumps(receipt, indent=2, ensure_ascii=False))
        return 0

    if args.command == "review-submissions":
        root = args.root.resolve()
        cases_dir = None
        if hasattr(args, "cases_dir"):
            cases_dir = (
                args.cases_dir.resolve()
                if args.cases_dir.is_absolute()
                else (root / args.cases_dir).resolve()
            )
        if args.submission_action == "finalize-release":
            try:
                result = finalize_release(root, run_tests=args.test)
            except (ReleaseFinalizeError, OSError, KeyError, ValueError) as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(
                    f"Finalized dataset {result['dataset_version']}: "
                    f"{result['records']} records and "
                    f"{result['simulator_views']} reviewed simulator views."
                )
                for path in result["generated"]:
                    print(f"  Generated {path}")
                for path in result["changed_documentation"]:
                    print(f"  Updated {path}")
                print("  Validation passed.")
                print(
                    "  Tests passed."
                    if result["tests"] == "passed"
                    else "  Tests not run; pass --test to run the full suite."
                )
            return 0

        if args.submission_action == "workbench":
            try:
                run_workbench(
                    WorkbenchApplication(
                        root,
                        repository=args.repo,
                        label=args.label,
                        cases_directory=args.cases_dir,
                        inbox=args.inbox,
                    ),
                    host=args.host,
                    port=args.port,
                    open_browser=not args.no_open,
                )
            except (WorkbenchError, OSError, ValueError) as exception:
                print(f"ERROR: {exception}")
                return 1
            return 0

        assert cases_dir is not None
        if args.submission_action == "sync":
            try:
                result = sync_submissions(
                    root,
                    repository=args.repo,
                    label=args.label,
                    cases_directory=args.cases_dir,
                    inbox=args.inbox,
                    issue_numbers=set(args.issue) if args.issue else None,
                )
            except SubmissionSyncError as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(
                    f"Found {result['issues_found']} issue(s): "
                    f"{result['processed']} processed, {result['skipped']} unchanged, "
                    f"{result['error']} error(s)."
                )
                for item in result["results"]:
                    detail = item["error"] or item["classification"] or "unclassified"
                    print(
                        f"  #{item['issue']} {item['outcome']}: {item['state']} "
                        f"({detail})"
                    )
                print(f"Review cases: {result['cases_directory']}")
            return 1 if result["error"] else 0

        if args.submission_action == "research-brief":
            try:
                briefs = generate_research_briefs(
                    root,
                    cases_dir,
                    set(args.issue) if args.issue else None,
                )
            except ResearchHandoffError as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(briefs, indent=2, ensure_ascii=False))
            else:
                for brief in briefs:
                    print(
                        f"#{brief['issue']}: wrote research brief with "
                        f"{brief['related_records']} related record lead(s)"
                    )
                    print(f"  {brief['brief']}")
                    print(f"  {brief['template']}")
                if not briefs:
                    print("No research-pending cases found.")
            return 0

        if args.submission_action == "import-research":
            try:
                result = import_research_result(
                    root,
                    cases_dir,
                    args.issue,
                    args.input,
                    replace=args.replace,
                )
            except ResearchHandoffError as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(
                    f"Imported {result['research_status']} research for issue "
                    f"#{result['issue']}; case state is {result['state']}."
                )
                print(f"  {result['result']}")
                print("No curated data was changed; final maintainer review is still required.")
            return 0

        if args.submission_action == "prepare-review":
            try:
                result = prepare_review_proposal(
                    root,
                    cases_dir,
                    args.issue,
                    dataset_version=args.dataset_version,
                )
            except (ResearchHandoffError, ValueError, FileExistsError, KeyError) as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(
                    f"Prepared issue #{result['issue']} for final manifest review "
                    f"as dataset {result['dataset_version']}; dry-run {result['dry_run']}."
                )
                print(f"  Summary: {result['summary']}")
                print(f"  Manifest: {result['manifest']}")
                print(f"  Sources: {result['sources']}")
                print(f"  Preview record: {result['preview_record']}")
                print("No curated data was changed.")
            return 0

        if args.submission_action == "promote":
            try:
                result = promote_review_case(
                    root,
                    cases_dir,
                    args.issue,
                    approved=args.approve,
                )
            except (ResearchHandoffError, ValueError, FileExistsError, KeyError) as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                print(
                    f"Promoted issue #{result['issue']} as "
                    f"{result['record_id']} in dataset {result['dataset_version']}."
                )
                print(f"  Manifest: {result['manifest']}")
                print(f"  Registered {len(result['sources_added'])} candidate source(s).")
                for path in result["written"]:
                    print(f"  {path}")
                print(
                    "Release finalization is still required. After the release batch, run:\n"
                    "  python -m as_driven_db review-submissions "
                    "finalize-release --test"
                )
            return 0

        if args.submission_action == "publish-result":
            try:
                result = publish_review_result(
                    root,
                    cases_dir,
                    args.issue,
                    approved=args.approve,
                )
            except (ReviewFeedbackError, OSError, KeyError, ValueError) as exception:
                print(f"ERROR: {exception}")
                return 1
            if args.json:
                print(json.dumps(result, indent=2, ensure_ascii=False))
            else:
                action = "Published" if result["status"] == "published" else "Preview"
                print(
                    f"{action} for issue #{result['issue']} "
                    f"({result['case_state']}; close as {result['close_reason']}):"
                )
                print()
                print(result["comment"])
                if result["blockers"]:
                    print("\nPublication blockers:")
                    for blocker in result["blockers"]:
                        print(f"  - {blocker}")
                if result["status"] == "preview":
                    print(
                        "\nNo GitHub changes were made. After committing, pushing, and "
                        "reviewing this text, rerun with --approve."
                    )
            return 0

        cases = list_review_cases(cases_dir)
        if args.json:
            print(json.dumps(cases, indent=2, ensure_ascii=False))
            return 0
        if not cases:
            print(f"No review cases in {cases_dir}. Run `review-submissions sync` first.")
            return 0
        print("ISSUE  STATE                RESEARCH       CLASSIFICATION                SIM   CAR")
        for case in cases:
            issue = f"#{case['issue']}"
            state = str(case["display_state"] or "unknown")[:20]
            research = str(case["research"] or "-")[:14]
            classification = str(case["classification"] or "-")[:29]
            simulator = str(case["simulator"] or "-").upper()[:5]
            car = case["telemetry_name"] or case["title"] or "-"
            print(
                f"{issue:<6} {state:<20} {research:<14} "
                f"{classification:<29} {simulator:<5} {car}"
            )
            if case["error"]:
                print(f"       ERROR: {case['error']}")
        print(f"\n{len(cases)} review case(s) in {cases_dir}")
        return 0

    if args.command == "import-ams2":
        payload = import_ams2_csv(
            args.input,
            source_id=args.source_id,
            verified_game_version=args.verified_game_version,
        )
        _write_json(args.output, payload)
        print(f"Wrote {len(payload['candidates'])} AMS2 candidate(s) to {args.output}")
        return 0

    if args.command == "import-iracing":
        payload = import_iracing_html(args.input, source_id=args.source_id)
        _write_json(args.output, payload)
        print(f"Wrote {len(payload['candidates'])} iRacing candidate(s) to {args.output}")
        return 0

    if args.command == "audit-simhub-ams2":
        candidates = json.loads(args.candidates.read_text(encoding="utf-8-sig"))
        payload = audit_ams2_identities(
            candidates,
            args.cars_dir,
            simhub_version=args.simhub_version,
        )
        _write_json(args.output, payload)
        if args.review_csv:
            write_alias_review_csv(payload, args.review_csv)
        stats = payload["stats"]
        print(
            "Wrote SimHub audit with "
            f"{stats['observed_simhub_identities']} observed identities and "
            f"{stats['candidate_rows_with_exact_match']} exact candidate matches "
            f"to {args.output}"
        )
        if args.review_csv:
            print(f"Wrote alias review queue to {args.review_csv}")
        return 0

    if args.command == "review-unmatched-ams2":
        candidates = json.loads(args.candidates.read_text(encoding="utf-8-sig"))
        payload = review_unmatched_ams2_observations(
            candidates,
            args.log,
            curated_data_directory=args.data_dir,
        )
        _write_json(args.output, payload)
        if args.review_csv:
            write_unmatched_review_csv(payload, args.review_csv)
        stats = payload["stats"]
        print(
            "Wrote unmatched AMS2 review with "
            f"{stats['unique_raw_identities']} unique raw identity/identities "
            f"to {args.output}"
        )
        if args.review_csv:
            print(f"Wrote unmatched review queue to {args.review_csv}")
        return 0

    if args.command == "promote-ams2":
        candidates = json.loads(args.candidates.read_text(encoding="utf-8-sig"))
        audit = json.loads(args.audit.read_text(encoding="utf-8-sig"))
        approvals = json.loads(args.approvals.read_text(encoding="utf-8-sig"))
        outputs = promote_approved_ams2(
            candidates,
            audit,
            approvals,
            args.data_dir,
        )
        print(f"Promoted {len(outputs)} AMS2 record(s) into {args.data_dir / 'cars'}")
        return 0

    if args.command == "promote-observation":
        review = json.loads(args.review.read_text(encoding="utf-8-sig"))
        try:
            written = promote_observations(
                review,
                root=args.root.resolve(),
                data_directory=args.data_dir,
                curation_directory=args.curation_dir,
            )
        except (ValueError, FileExistsError, KeyError) as exception:
            print(f"ERROR: {exception}")
            return 1
        records = [path for path in written if path.parent.name == "cars"]
        print(
            f"Promoted {len(records)} record(s) as dataset "
            f"{review['dataset_version']}:"
        )
        for path in written:
            print(f"  {path}")
        print("Run validate and regenerate the coverage manifest next.")
        return 0

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

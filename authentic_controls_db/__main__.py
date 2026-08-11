from __future__ import annotations

import argparse
import json
from pathlib import Path

from .audit_boundaries import audit_evidence_boundaries
from .importers.ams2 import import_ams2_csv
from .importers.iracing import import_iracing_html
from .promote import promote_approved_ams2
from .simhub import (
    audit_ams2_identities,
    review_unmatched_ams2_observations,
    write_alias_review_csv,
    write_unmatched_review_csv,
)
from .validate import validate_repository
from .schema_validation import validate_instance


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="authentic-controls-db")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate = subparsers.add_parser("validate", help="validate the curated repository")
    validate.add_argument("--root", type=Path, default=Path.cwd())

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

    return 2


if __name__ == "__main__":
    raise SystemExit(main())

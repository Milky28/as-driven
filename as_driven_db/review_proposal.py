from __future__ import annotations

import copy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .site import simulator_label
from .promote_observation import promote_observations
from .research_handoff import (
    ResearchHandoffError,
    _read_json,
    _write_json,
    validate_research_result,
)
from .schema_validation import validate_instance


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _next_patch(version: str) -> str:
    try:
        major, minor, patch = (int(token) for token in version.split("."))
    except (ValueError, TypeError) as exception:
        raise ResearchHandoffError(f"cannot increment dataset version {version!r}") from exception
    return f"{major}.{minor}.{patch + 1}"


def _proposal_date(result: dict[str, Any]) -> str:
    dates = [date.today()]
    for source in result.get("sources", []):
        retrieved = source.get("retrieved_at")
        if retrieved:
            dates.append(date.fromisoformat(retrieved))
    return max(dates).isoformat()


def _set_pointer(document: dict[str, Any], pointer: str, value: Any) -> None:
    tokens = [token.replace("~1", "/").replace("~0", "~") for token in pointer.split("/")[1:]]
    current: Any = document
    for token in tokens[:-1]:
        if not isinstance(current, dict) or token not in current:
            raise ResearchHandoffError(f"research claim points to unknown field {pointer!r}")
        current = current[token]
    if not tokens or not isinstance(current, dict):
        raise ResearchHandoffError(f"research claim points to unknown field {pointer!r}")
    current[tokens[-1]] = copy.deepcopy(value)


def _flatten(document: Any, prefix: str = "") -> dict[str, Any]:
    values: dict[str, Any] = {}
    if isinstance(document, dict):
        for key, value in document.items():
            child = f"{prefix}/{key}"
            values.update(_flatten(value, child))
    else:
        values[prefix] = document
    return values


def _candidate_source(source: dict[str, Any]) -> dict[str, Any]:
    locators = []
    for locator in source.get("locators", []):
        detail = locator["locator"]
        if locator.get("quote"):
            detail += f": “{locator['quote']}”"
        # A locator may establish a value or document that a reviewed source is
        # silent about a narrower technique. The claim object carries that
        # verdict; calling every locator "support" overstates the latter case.
        detail += " Reviewed for " + ", ".join(locator.get("supports", [])) + "."
        locators.append(detail)
    notes = " ".join(
        part
        for part in (
            f"Exact scope: {source['exact_scope']}",
            " ".join(locators),
            source.get("notes") or "",
        )
        if part
    )
    candidate = {
        "source_id": source["source_id"],
        "title": source["title"],
        "publisher": source["publisher"],
        "url": source["url"],
        "source_type": source["source_type"],
        "retrieved_at": source["retrieved_at"],
        "reuse_status": source["reuse_status"],
        "notes": notes,
    }
    for key in ("author", "archive_url", "published_or_updated_at"):
        if source.get(key) is not None:
            candidate[key] = source[key]
    return candidate


def _require_schema(
    root: Path, payload: dict[str, Any], schema_name: str, label: str
) -> None:
    schema = _read_json(root / "schema" / "v1" / schema_name, f"{label} schema")
    errors = validate_instance(payload, schema, label)
    if errors:
        raise ResearchHandoffError("; ".join(errors))


def _real_controls(
    staged_controls: dict[str, Any], result: dict[str, Any]
) -> dict[str, Any]:
    controls = copy.deepcopy(staged_controls)
    for claim in result["claims"]:
        path = str(claim["path"])
        if not path.startswith("/authentic_controls/"):
            continue
        _set_pointer(controls, path.removeprefix("/authentic_controls"), claim["proposed_value"])
    wheel_claims = [
        claim
        for claim in result["claims"]
        if str(claim["path"]).startswith("/authentic_controls/steering/wheel_rim/")
    ]
    if wheel_claims and all(claim["finding"] == "not-established" for claim in wheel_claims):
        wheel = controls["steering"]["wheel_rim"]
        wheel["source_label"] = "real-car-research-not-established"
        wheel["notes"] = "Exact real-car wheel details were not established by the reviewed sources."
    return controls


def _require_complete_control_review(
    staged_controls: dict[str, Any], result: dict[str, Any]
) -> None:
    material_paths = {
        path
        for path in _flatten(staged_controls, "/authentic_controls")
        if not path.endswith("/notes")
        and not path.endswith("/source_label")
        and path != "/authentic_controls/notes"
    }
    reviewed_paths = {
        str(claim["path"])
        for claim in result["claims"]
        if str(claim["path"]).startswith("/authentic_controls/")
    }
    missing = sorted(material_paths - reviewed_paths)
    if missing:
        raise ResearchHandoffError(
            "complete research result does not address every material real-car "
            f"control field; add established or not-established claims for {missing!r}"
        )


def _require_representable_controls(real_controls: dict[str, Any]) -> None:
    transmission = real_controls["transmission"]
    if (
        transmission.get("shift_pattern") == "dogleg-h"
        and transmission.get("first_gear_position") not in {"down-left", "down-right"}
    ):
        raise ResearchHandoffError(
            "a dogleg shift pattern cannot be proposed until research establishes "
            "whether first gear is down-left or down-right; keep shift_pattern "
            "unknown when the side is not established"
        )


def _control_overrides(
    staged_controls: dict[str, Any], real_controls: dict[str, Any]
) -> dict[str, Any]:
    overrides: dict[str, Any] = {}
    staged_transmission = staged_controls["transmission"]
    real_transmission = real_controls["transmission"]
    for key, value in real_transmission.items():
        if key not in staged_transmission:
            if value is not None and value != "unknown":
                overrides[key] = value
        elif value != staged_transmission[key]:
            overrides[key] = value
    staged_wheel = staged_controls["steering"]["wheel_rim"]
    real_wheel = real_controls["steering"]["wheel_rim"]
    wheel_changes = {
        key: value
        for key, value in real_wheel.items()
        if key in staged_wheel and value != staged_wheel[key]
    }
    if wheel_changes:
        overrides["wheel_rim"] = wheel_changes
    return overrides


def _simulator_overrides(
    staged_controls: dict[str, Any],
    real_controls: dict[str, Any],
    staged: dict[str, Any],
) -> list[dict[str, Any]]:
    staged_values = _flatten(staged_controls, "/authentic_controls")
    real_values = _flatten(real_controls, "/authentic_controls")
    source_id = staged["source"]["source_id"]
    version = staged["record"]["simulators"][0]["verified_game_version"]
    observation_id = staged["observation_id"]
    ignored = {"/authentic_controls/notes"}
    overrides: list[dict[str, Any]] = []
    # Some guided tests establish simulator behavior without establishing the
    # authentic real-car answer. The two-stage manual-blip test is the first:
    # a simulator can refuse the coast downshift and accept the repeated blipped
    # downshift, but that does not reveal whether the real gearbox required or
    # merely benefited from rev matching. The importer records such facts as
    # simulator overrides, and final review must carry them independently of the
    # staged authentic layer.
    for override in staged["record"]["simulators"][0].get("overrides", []):
        path = override["path"]
        if real_values.get(path) != override.get("value"):
            overrides.append(copy.deepcopy(override))
    existing = {
        (override["path"], json.dumps(override.get("value"), sort_keys=True))
        for override in overrides
    }
    for path in sorted(staged_values.keys() & real_values.keys()):
        if path in ignored or staged_values[path] == real_values[path]:
            continue
        if path.endswith("/source_label") or path.endswith("/notes"):
            continue
        if staged_values[path] in {None, "unknown"}:
            # An observation that did not establish a construction or behavior
            # cannot contradict a real-car source that did establish it.
            continue
        key = (path, json.dumps(staged_values[path], sort_keys=True))
        if key in existing:
            continue
        overrides.append(
            {
                "path": path,
                "value": staged_values[path],
                "condition": (
                    f"The guided observation {observation_id} directly recorded this "
                    f"behavior or cockpit value in the simulator version {version}; "
                    "the reviewed real-car sources did not establish the same value."
                ),
                "confidence": {
                    "level": "verified",
                    "basis": "Exact value preserved from the validated guided-drive observation.",
                },
                "source_refs": [source_id],
            }
        )
    return overrides


def _specification_basis(result: dict[str, Any]) -> str:
    established = [
        claim["basis"]
        for claim in result["claims"]
        if claim["finding"] == "established"
        and str(claim["path"]).startswith("/authentic_controls/")
    ]
    unknown_paths = [
        claim["path"]
        for claim in result["claims"]
        if claim["finding"] == "not-established"
        and str(claim["path"]).startswith("/authentic_controls/")
    ]
    basis = " ".join(dict.fromkeys(established))
    if unknown_paths:
        basis += (
            " The reviewed sources did not establish the remaining technique and "
            "wheel fields, which stay unknown in the real-car baseline: "
            + ", ".join(unknown_paths)
            + "."
        )
    return basis.strip()


def _identity_scope_label(identity: dict[str, Any]) -> str:
    year = identity.get("year") or {}
    return str(year.get("label") or year.get("from") or identity["display_name"])


def _established_controls_note(result: dict[str, Any]) -> str:
    labels = {
        "/authentic_controls/transmission/forward_gears": "forward gears",
        "/authentic_controls/transmission/gearbox_type": "gearbox construction",
        "/authentic_controls/transmission/shift_actuation": "shift actuation",
        "/authentic_controls/transmission/shift_pattern": "shift pattern",
        "/authentic_controls/transmission/standing_start_clutch": "standing-start clutch use",
        "/authentic_controls/steering/wheel_rim/shape": "wheel-rim shape",
        "/authentic_controls/steering/wheel_rim/integrated_display": "integrated wheel display",
        "/authentic_controls/steering/wheel_rim/shift_lights": "wheel shift lights",
        "/authentic_controls/steering/wheel_rim/open_top": "conventional rim open-top section",
    }
    established: list[str] = []
    for claim in result["claims"]:
        path = str(claim["path"])
        if claim["finding"] != "established" or not path.startswith(
            "/authentic_controls/"
        ):
            continue
        label = labels.get(path, path.removeprefix("/authentic_controls/").replace("/", " "))
        value = claim.get("proposed_value")
        rendered = str(value).replace("-", " ") if not isinstance(value, (dict, list)) else json.dumps(value, ensure_ascii=False)
        established.append(f"{label}: {rendered}")
    if not established:
        return "The reviewed exact-scope sources establish no real-car control values."
    return "The reviewed exact-scope sources establish " + "; ".join(established) + "."


def sourced_control_paths(result: dict[str, Any]) -> list[str]:
    """Real-car control paths the reviewed sources actually established.

    The note beside this says the same thing in prose, and prose is not
    something the promoter can attribute a claim with. Without the list it
    credited every technique value to the guided drive, including the ones a
    manufacturer manual had settled - so a record could state that its real car
    blips on downshifts while citing a drive that observed the opposite.
    """
    return sorted(
        str(claim["path"])
        for claim in result["claims"]
        if claim.get("finding") == "established"
        and str(claim["path"]).startswith("/authentic_controls/")
        and claim.get("proposed_value") not in (None, "unknown")
    )


def _unestablished_baseline_note(result: dict[str, Any]) -> str | None:
    """Name what the sources left open, rather than asserting they left it all.

    This sentence used to be a constant, printed under a line listing the very
    fields it denied. Where the sources reached everything it is omitted; where
    they reached nothing it reads as it always did.
    """
    families = {
        "launch technique": ("/authentic_controls/transmission/standing_start_clutch",),
        "running-shift technique": (
            "/authentic_controls/transmission/upshift/clutch",
            "/authentic_controls/transmission/downshift/clutch",
            "/authentic_controls/transmission/upshift/throttle_lift",
        ),
        "cut and blip behavior": (
            "/authentic_controls/transmission/upshift/automatic_cut",
            "/authentic_controls/transmission/downshift/automatic_blip",
            "/authentic_controls/transmission/downshift/manual_blip",
        ),
        "selector pattern": ("/authentic_controls/transmission/shift_pattern",),
        "wheel topology": (
            "/authentic_controls/steering/wheel_rim/shape",
            "/authentic_controls/steering/wheel_rim/open_top",
        ),
    }
    established = set(sourced_control_paths(result))
    open_families = [
        name for name, paths in families.items()
        if not any(path in established for path in paths)
    ]
    if not open_families:
        return None
    listed = ", ".join(open_families[:-1])
    listed = f"{listed} or {open_families[-1]}" if listed else open_families[-1]
    return (
        f"The reviewed real-car sources do not establish {listed}; those baseline "
        "fields remain unknown."
    )


def _proposal_summary(
    case: dict[str, Any],
    manifest: dict[str, Any],
    sources: list[dict[str, Any]],
    preview_record: dict[str, Any],
) -> str:
    entry = manifest["records"][0]
    transmission = preview_record["authentic_controls"]["transmission"]
    wheel = preview_record["authentic_controls"]["steering"]["wheel_rim"]
    return f"""# Final review proposal: issue #{case['issue']['number']}

No curated files have been changed. This proposal was dry-run through the real promotion path with candidate sources registered only in a temporary data directory.

## Identity

- Record: `{entry['record_id']}`
- Display name: {preview_record['identity']['display_name']}
- Class: {preview_record['identity']['class']}
- Confidence: {entry['confidence']}
- Proposed dataset: {manifest['dataset_version']}

## Real-car baseline

```json
{json.dumps({'transmission': transmission, 'wheel_rim': wheel}, indent=2, ensure_ascii=False)}
```

## Exact simulator departures from that baseline

```json
{json.dumps(preview_record['simulators'][0]['overrides'], indent=2, ensure_ascii=False)}
```

## Reviewed sources

{chr(10).join(f"- `{source['source_id']}` - {source['title']} ({source['registration']})" for source in sources)}

Review the proposed manifest, source wording, unknown fields, and simulator overrides before copying anything into `data/v1` or `curation`.
"""


def prepare_review_proposal(
    root: Path,
    cases_directory: Path,
    issue_number: int,
    dataset_version: str | None = None,
) -> dict[str, Any]:
    root = root.resolve()
    case_directory = cases_directory / f"issue-{issue_number}"
    case = _read_json(case_directory / "case.json", "review case")
    if (
        case.get("state") not in {"final-review", "manifest-review"}
        or case.get("research", {}).get("status") != "complete"
    ):
        raise ResearchHandoffError(
            f"issue #{issue_number} needs a complete imported research result before review preparation"
        )
    staged = _read_json(case_directory / case["artifacts"]["staged_bundle"], "staged bundle")
    result = _read_json(case_directory / case["artifacts"]["research_result"], "research result")
    result_errors = validate_research_result(
        root,
        case,
        result,
        "research result",
    )
    if result_errors:
        raise ResearchHandoffError(
            "research result validation failed:\n" + "\n".join(result_errors)
        )
    identity = result["identity"]
    if identity["record_action"] not in {"create-new", "use-existing"}:
        raise ResearchHandoffError("research result has no reviewable record action")

    index = _read_json(root / "data" / "v1" / "index.json", "dataset index")
    proposed_version = dataset_version or _next_patch(index["dataset_version"])
    staged_controls = staged["record"]["authentic_controls"]
    _require_complete_control_review(staged_controls, result)
    real_controls = _real_controls(staged_controls, result)
    _require_representable_controls(real_controls)
    overrides = _control_overrides(staged_controls, real_controls)
    simulator_overrides = _simulator_overrides(staged_controls, real_controls, staged)
    research_sources = [
        source
        for source in result["sources"]
        if source["source_type"] != "in-game-observation"
    ]
    source_refs = [source["source_id"] for source in research_sources]
    if not source_refs:
        raise ResearchHandoffError("research result has no candidate real-world sources")
    registered_sources = _read_json(
        root / "data" / "v1" / "sources.json", "registered source registry"
    )
    registered_by_id = {
        source["source_id"]: source for source in registered_sources["sources"]
    }
    candidate_sources: list[dict[str, Any]] = []
    reviewed_sources: list[dict[str, Any]] = []
    canonical_fields = ("title", "publisher", "url", "source_type")
    for research_source in research_sources:
        candidate = _candidate_source(research_source)
        existing = registered_by_id.get(candidate["source_id"])
        if existing is not None:
            differences = [
                field
                for field in canonical_fields
                if existing.get(field) != candidate.get(field)
            ]
            if differences:
                raise ResearchHandoffError(
                    f"research source {candidate['source_id']!r} conflicts with its "
                    f"registered {', '.join(differences)} metadata"
                )
            registration = "already registered"
        else:
            candidate_sources.append(candidate)
            registration = "new candidate"
        reviewed_sources.append(
            {
                "source_id": candidate["source_id"],
                "title": candidate["title"],
                "registration": registration,
            }
        )

    bundle_path = case_directory / case["artifacts"]["staged_bundle"]
    try:
        bundle_reference = bundle_path.relative_to(root).as_posix()
    except ValueError:
        # Tests and alternate workbenches may keep ignored cases outside the
        # repository. A checked-in final manifest should always use the normal
        # relative build path.
        bundle_reference = bundle_path.as_posix()
    manifest_entry = {
        "record_id": identity["record_id"],
        "bundle": bundle_reference,
        "display_name": identity["display_name"],
        "class": identity["class"],
        "manufacturer": identity["manufacturer"],
        "model": identity["model"],
        "year": identity["year"],
        "real_world_identity_notes": identity["real_world_identity_notes"],
        "real_world_source_refs": source_refs,
        "confidence": identity["confidence"],
        "confidence_basis": identity["basis"],
        "identity_basis": identity["basis"],
        "specification_basis": _specification_basis(result),
        "control_overrides": overrides,
        "simulator_overrides": simulator_overrides,
        "confidence_notes": (
            f"The exact {_identity_scope_label(identity)} identity and established "
            "control fields come from the candidate authoritative sources. Fields "
            "absent from those sources remain unknown in the real-car baseline; the "
            "exact simulator values remain simulator-specific guided observations."
        ),
        "sourced_control_paths": sourced_control_paths(result),
        "control_notes": [
            _established_controls_note(result),
            *([note] if (note := _unestablished_baseline_note(result)) else []),
            # Name the simulator the drive was actually made in. This said AMS2
            # for every submission, so Assetto Corsa records carried an AMS2
            # attribution beside an Assetto Corsa build id.
            (
                f"{simulator_label(staged['record']['simulators'][0]['simulator'])} "
                f"{staged['record']['simulators'][0]['verified_game_version']} behavior and "
                "cockpit values were directly observed and are preserved as simulator "
                "overrides where the real baseline is unknown."
            ),
        ],
        "scope_notes": "New season-specific identity reviewed from one public guided-drive submission and independent exact-year sources.",
        "live_source_url": case["issue"]["url"],
        "live_source_notes": staged["source"]["notes"],
    }
    staged_record_id = staged["record"]["record_id"]
    if (
        identity["record_action"] == "create-new"
        and identity["record_id"] != staged_record_id
    ):
        manifest_entry["create_new_record"] = {
            "staged_record_id": staged_record_id,
            "basis": identity["basis"],
        }
    manifest = {
        "schema_version": "1.0.0",
        "dataset_version": proposed_version,
        "approved_at": _proposal_date(result),
        "records": [manifest_entry],
    }
    sources_proposal = {"schema_version": "1.0.0", "sources": candidate_sources}
    _require_schema(
        root,
        sources_proposal,
        "source-record.schema.json",
        "candidate source proposal",
    )

    manifest_path = case_directory / "review-manifest.proposed.json"
    sources_path = case_directory / "sources.proposed.json"
    _write_json(manifest_path, manifest)
    _write_json(sources_path, sources_proposal)

    with tempfile.TemporaryDirectory(prefix="as-driven-review-") as temporary:
        temp = Path(temporary)
        temp_data = temp / "data" / "v1"
        temp_curation = temp / "curation"
        shutil.copytree(root / "data" / "v1", temp_data)
        shutil.copytree(root / "curation", temp_curation)
        registry_path = temp_data / "sources.json"
        registry = _read_json(registry_path, "temporary source registry")
        known = {source["source_id"] for source in registry["sources"]}
        registry["sources"].extend(
            source for source in candidate_sources if source["source_id"] not in known
        )
        _write_json(registry_path, registry)
        written = promote_observations(
            manifest,
            root=root,
            data_directory=temp_data,
            curation_directory=temp_curation,
        )
        previews = {
            path.name: _read_json(path, "dry-run promotion output")
            for path in written
            if path.suffix == ".json"
        }
        record_name = f"{identity['record_id']}.json"
        approval_name = f"{staged['simulator']}-approved-{identity['record_id']}.json"
        preview_record = previews[record_name]
        preview_approval = previews[approval_name]
        live_source_id = staged["source"]["source_id"]
        promoted_sources = _read_json(temp_data / "sources.json", "dry-run source registry")
        preview_live_source = next(
            source
            for source in promoted_sources["sources"]
            if source["source_id"] == live_source_id
        )

    _require_schema(root, preview_record, "car-record.schema.json", "preview record")
    _require_schema(
        root,
        preview_approval,
        "curation-approval.schema.json",
        "preview approval",
    )
    _require_schema(
        root,
        {"schema_version": "1.0.0", "sources": [preview_live_source]},
        "source-record.schema.json",
        "preview live source",
    )

    preview_record_path = case_directory / "preview-record.json"
    preview_approval_path = case_directory / "preview-approval.json"
    preview_live_source_path = case_directory / "preview-live-source.json"
    summary_path = case_directory / "final-review.md"
    _write_json(preview_record_path, preview_record)
    _write_json(preview_approval_path, preview_approval)
    _write_json(preview_live_source_path, preview_live_source)
    summary_path.write_text(
        _proposal_summary(case, manifest, reviewed_sources, preview_record),
        encoding="utf-8",
    )

    case["state"] = "manifest-review"
    case["artifacts"].update(
        {
            "review_manifest_proposal": manifest_path.name,
            "source_proposal": sources_path.name,
            "preview_record": preview_record_path.name,
            "preview_approval": preview_approval_path.name,
            "preview_live_source": preview_live_source_path.name,
            "final_review": summary_path.name,
        }
    )
    case["review_proposal"] = {
        "status": "ready",
        "dataset_version": proposed_version,
        "prepared_at": _now(),
        "dry_run": "passed",
    }
    case["updated_at"] = _now()
    _write_json(case_directory / "case.json", case)
    return {
        "issue": issue_number,
        "state": case["state"],
        "dataset_version": proposed_version,
        "manifest": str(manifest_path),
        "sources": str(sources_path),
        "summary": str(summary_path),
        "preview_record": str(preview_record_path),
        "dry_run": "passed",
    }

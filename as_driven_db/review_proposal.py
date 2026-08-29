from __future__ import annotations

import copy
from datetime import date, datetime, timezone
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any

from .site import simulator_label
from .promote_observation import _behavior_changes, promote_observations
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


def _ordinary_punctuation(value: str) -> str:
    """Keep generated tracked source copy within the repository text policy."""
    return " ".join(value.replace("\u2014", " - ").split())


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
        "title": _ordinary_punctuation(source["title"]),
        "publisher": _ordinary_punctuation(source["publisher"]),
        "url": source["url"],
        "source_type": source["source_type"],
        "retrieved_at": source["retrieved_at"],
        "reuse_status": source["reuse_status"],
        "notes": _ordinary_punctuation(notes),
    }
    for key in ("author", "archive_url", "published_or_updated_at"):
        if source.get(key) is not None:
            candidate[key] = (
                _ordinary_punctuation(source[key])
                if key == "author"
                else source[key]
            )
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
    for key, staged_value in staged_wheel.items():
        if key in {"notes", "source_label"} or key in real_wheel:
            continue
        if staged_value is not None and staged_value != "unknown":
            # A cockpit observation establishes the simulator, not the real
            # car. When the curated baseline deliberately leaves a wheel field
            # absent, retract the staged authentic value while preserving it as
            # a simulator override below.
            wheel_changes[key] = "unknown"
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
    for path in sorted(staged_values):
        if path in ignored or staged_values[path] == real_values.get(path):
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
    simulator_id: str | None = None,
) -> str:
    entry = manifest["records"][0]
    transmission = preview_record["authentic_controls"]["transmission"]
    wheel = preview_record["authentic_controls"]["steering"]["wheel_rim"]
    same_simulator_review = entry.get("correct_existing_simulator") or entry.get(
        "compatible_implementation"
    )
    same_simulator_section = ""
    driver_summary = entry.get("driver_summary")
    driver_summary_section = ""
    if driver_summary:
        driver_summary_section = f"""
## Driver summary

> {driver_summary}

This is record-wide prose shown for every simulator. Confirm that it remains
accurate beside each simulator's effective USE rows.
"""
    if same_simulator_review:
        disposition = (
            "Correction of the existing simulator entry"
            if entry.get("correct_existing_simulator")
            else "Compatible repeat implementation"
        )
        same_simulator_section = f"""
## Existing simulator entry

- Disposition: {disposition}
- Basis: {same_simulator_review['basis']}
"""
        if entry.get("correct_existing_simulator"):
            same_simulator_section += (
                "- Enumerated behavior changes: "
                + ", ".join(
                    f"`{path}`"
                    for path in same_simulator_review["corrected_behavior_paths"]
                )
                + "\n"
            )
    simulator_entry = next(
        (
            candidate
            for candidate in preview_record["simulators"]
            if candidate.get("simulator") == simulator_id
        ),
        preview_record["simulators"][0],
    )
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
{json.dumps(simulator_entry['overrides'], indent=2, ensure_ascii=False)}
```
{same_simulator_section}
{driver_summary_section}

## Reviewed sources

{chr(10).join(f"- `{source['source_id']}` - {source['title']} ({source['registration']})" for source in sources)}

Review the proposed manifest, source wording, unknown fields, and simulator overrides before copying anything into `data/v1` or `curation`.
"""


_OPTIONAL_CONTROL_OVERRIDE_PATHS = {
    "/authentic_controls/transmission/first_gear_position",
    "/authentic_controls/steering/degrees_of_rotation",
    "/authentic_controls/steering/wheel_rim/diameter_mm",
    "/authentic_controls/steering/wheel_rim/integrated_display",
    "/authentic_controls/steering/wheel_rim/shift_lights",
    "/authentic_controls/steering/wheel_rim/open_top",
}


def _apply_control_overrides(
    controls: dict[str, Any], overrides: list[dict[str, Any]]
) -> dict[str, Any]:
    effective = copy.deepcopy(controls)
    prefix = "/authentic_controls/"
    for override in overrides:
        path = override.get("path", "")
        if not path.startswith(prefix):
            continue
        tokens = [token for token in path[len(prefix):].split("/") if token]
        node: Any = effective
        for token in tokens[:-1]:
            if not isinstance(node, dict) or token not in node:
                raise ResearchHandoffError(
                    f"simulator override points to unknown control field {path!r}"
                )
            node = node[token]
        if not tokens or not isinstance(node, dict):
            raise ResearchHandoffError(
                f"simulator override points to unknown control field {path!r}"
            )
        if tokens[-1] not in node and path not in _OPTIONAL_CONTROL_OVERRIDE_PATHS:
            raise ResearchHandoffError(
                f"simulator override points to unknown control field {path!r}"
            )
        node[tokens[-1]] = copy.deepcopy(override["value"])
    return effective


_SUMMARY_TECHNIQUE_PATHS = {
    "/transmission/standing_start_clutch": "launch clutch",
    "/transmission/upshift/clutch": "upshift clutch",
    "/transmission/upshift/throttle_lift": "upshift lift",
    "/transmission/upshift/automatic_cut": "upshift cut",
    "/transmission/downshift/clutch": "downshift clutch",
    "/transmission/downshift/manual_blip": "manual downshift blip",
    "/transmission/downshift/automatic_blip": "automatic downshift blip",
}


def _control_value(controls: dict[str, Any], path: str) -> Any:
    value: Any = controls
    for token in (part for part in path.split("/") if part):
        if not isinstance(value, dict) or token not in value:
            return None
        value = value[token]
    return value


def _simulator_technique_disagreements(record: dict[str, Any]) -> list[str]:
    controls = record["authentic_controls"]
    effective = [
        _apply_control_overrides(controls, entry.get("overrides") or [])
        for entry in record.get("simulators", [])
    ]
    if len(effective) < 2:
        return []
    return [
        label
        for path, label in _SUMMARY_TECHNIQUE_PATHS.items()
        if len({_control_value(view, path) for view in effective}) > 1
    ]


def generate_driver_summary(record: dict[str, Any]) -> tuple[str, list[str]]:
    """Draft conservative record-wide driver prose from reviewed controls.

    The summary deliberately does not infer gearbox construction or repeat
    identity prose. It turns only curated control values into practical advice,
    and sends simulator disagreements back to the per-game USE row.
    """
    transmission = record["authentic_controls"]["transmission"]
    gears = transmission.get("forward_gears")
    actuation = transmission.get("shift_actuation")
    mechanism = {
        "h-pattern": "H-pattern",
        "sequential-stick": "lever sequential",
        "sequential-paddles": "paddle sequential",
        "automatic-lever": "automatic",
        "direct-selection": "direct-selection transmission",
    }.get(actuation, "transmission")
    if gears:
        mechanism = f"{gears}-speed {mechanism}"

    launch = transmission["standing_start_clutch"]
    if launch == "required":
        launch_sentence = "Use the clutch to pull away."
    elif launch == "not-required":
        launch_sentence = "It pulls away without a clutch."
    elif launch == "anti-stall-available":
        launch_sentence = "Anti-stall can handle the launch."
    elif launch == "not-applicable":
        launch_sentence = "No launch clutch is needed."
    else:
        launch_sentence = "Launch clutch use is not established, so use it to be safe."

    upshift = transmission["upshift"]
    lift = upshift["throttle_lift"]
    up_clutch = upshift["clutch"]
    cut = upshift["automatic_cut"]
    if lift == "required":
        up_sentence = "Lift for every upshift"
    elif lift == "partial":
        up_sentence = "Use a partial lift for every upshift"
    elif lift == "not-required" and cut == "yes":
        up_sentence = "Stay flat on the upshift because the car cuts for you"
    elif lift == "not-required":
        up_sentence = "Stay flat on the upshift"
    elif lift == "not-applicable":
        up_sentence = "No throttle lift is needed on the upshift"
    else:
        up_sentence = "Upshift lift is not established, so lift to be safe"
    if up_clutch == "required":
        up_sentence += " and use the clutch"
    elif up_clutch == "optional":
        up_sentence += "; the clutch is optional once moving"
    elif up_clutch == "unknown":
        up_sentence += "; running clutch use is not established"
    up_sentence += "."

    downshift = transmission["downshift"]
    manual_blip = downshift["manual_blip"]
    auto_blip = downshift["automatic_blip"]
    down_clutch = downshift["clutch"]
    if auto_blip == "yes":
        down_sentence = "The car blips its own downshifts"
    elif manual_blip == "required":
        down_sentence = "Blip every downshift yourself"
    elif manual_blip == "optional":
        down_sentence = "A downshift blip is optional, but can help settle the car"
    elif manual_blip in {"not-required", "not-applicable"}:
        down_sentence = "No downshift blip is needed"
    else:
        down_sentence = (
            "Whether the gearbox needs a downshift blip is not established, "
            "so blip to be safe"
        )
    if down_clutch == "required":
        down_sentence += " and use the clutch"
    elif down_clutch == "optional":
        down_sentence += "; the clutch is optional"
    elif down_clutch == "unknown":
        down_sentence += "; downshift clutch use is not established"
    down_sentence += "."

    disagreements = _simulator_technique_disagreements(record)
    mechanism_sentence = mechanism if gears else mechanism[0].upper() + mechanism[1:]
    summary = f"{mechanism_sentence}. {launch_sentence} {up_sentence} {down_sentence}"
    if disagreements:
        listed = ", ".join(disagreements)
        summary += (
            f" Simulator implementations differ on {listed}; follow the selected "
            "game's USE row for those items."
        )
    return summary, disagreements


def _dry_run_review_proposal(
    root: Path,
    staged: dict[str, Any],
    manifest: dict[str, Any],
    candidate_sources: list[dict[str, Any]],
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    entry = manifest["records"][0]
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
        registered_before_promotion = {
            source["source_id"] for source in registry["sources"]
        }
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
        record_name = f"{entry['record_id']}.json"
        approval_name = f"{staged['simulator']}-approved-{entry['record_id']}.json"
        preview_record = previews[record_name]
        preview_approval = previews[approval_name]
        promoted_sources = _read_json(
            temp_data / "sources.json", "dry-run source registry"
        )
        new_live_sources = [
            source
            for source in promoted_sources["sources"]
            if source["source_id"] not in registered_before_promotion
            and source["source_type"] == "in-game-observation"
        ]
        if len(new_live_sources) != 1:
            raise ResearchHandoffError(
                "dry-run promotion did not register exactly one new live observation "
                f"source; found {[source['source_id'] for source in new_live_sources]!r}"
            )
        preview_live_source = new_live_sources[0]

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
    return preview_record, preview_approval, preview_live_source


def _reviewed_sources(
    root: Path,
    manifest: dict[str, Any],
    candidate_sources: list[dict[str, Any]],
) -> list[dict[str, str]]:
    registry = _read_json(
        root / "data" / "v1" / "sources.json", "registered source registry"
    )
    registered = {source["source_id"]: source for source in registry["sources"]}
    candidates = {source["source_id"]: source for source in candidate_sources}
    reviewed = []
    for source_id in manifest["records"][0]["real_world_source_refs"]:
        source = candidates.get(source_id) or registered.get(source_id)
        if source is None:
            raise ResearchHandoffError(
                f"review manifest references unknown real-world source {source_id!r}"
            )
        reviewed.append(
            {
                "source_id": source_id,
                "title": source["title"],
                "registration": (
                    "new candidate" if source_id in candidates else "already registered"
                ),
            }
        )
    return reviewed


def _bundle_reference(root: Path, bundle_path: Path) -> str:
    try:
        # Windows runners may expose the temporary directory through an 8.3
        # alias while Path.resolve() expands the repository root. Resolve both
        # sides before computing the portable repository-relative reference.
        return bundle_path.resolve().relative_to(root).as_posix()
    except ValueError:
        # Tests and alternate workbenches may keep ignored cases outside the
        # repository. A checked-in final manifest should always use the normal
        # relative build path.
        return bundle_path.as_posix()


def _write_review_proposal(
    root: Path,
    case_directory: Path,
    case: dict[str, Any],
    staged: dict[str, Any],
    manifest: dict[str, Any],
    sources_proposal: dict[str, Any],
    reviewed_sources: list[dict[str, Any]],
) -> dict[str, Any]:
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

    preview_record, preview_approval, preview_live_source = _dry_run_review_proposal(
        root,
        staged,
        manifest,
        sources_proposal["sources"],
    )
    preview_record_path = case_directory / "preview-record.json"
    preview_approval_path = case_directory / "preview-approval.json"
    preview_live_source_path = case_directory / "preview-live-source.json"
    summary_path = case_directory / "final-review.md"
    _write_json(preview_record_path, preview_record)
    _write_json(preview_approval_path, preview_approval)
    _write_json(preview_live_source_path, preview_live_source)
    simulator_id = staged["record"]["simulators"][0]["simulator"]
    summary_path.write_text(
        _proposal_summary(
            case,
            manifest,
            reviewed_sources,
            preview_record,
            simulator_id,
        ),
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
        "dataset_version": manifest["dataset_version"],
        "prepared_at": _now(),
        "dry_run": "passed",
    }
    case["updated_at"] = _now()
    _write_json(case_directory / "case.json", case)
    return {
        "issue": case["issue"]["number"],
        "state": case["state"],
        "dataset_version": manifest["dataset_version"],
        "manifest": str(manifest_path),
        "sources": str(sources_path),
        "summary": str(summary_path),
        "preview_record": str(preview_record_path),
        "dry_run": "passed",
    }


def _existing_record(root: Path, record_id: str) -> dict[str, Any] | None:
    path = root / "data" / "v1" / "cars" / f"{record_id}.json"
    return _read_json(path, "curated record") if path.is_file() else None


def _same_simulator_disposition(
    root: Path,
    case: dict[str, Any],
    staged: dict[str, Any],
    manifest_entry: dict[str, Any],
    existing_record: dict[str, Any] | None,
) -> None:
    """Make a repeat drive an explicit compatible observation or correction."""
    if existing_record is None:
        return
    simulator_id = staged["record"]["simulators"][0]["simulator"]
    current_entries = [
        entry
        for entry in existing_record.get("simulators", [])
        if entry.get("simulator") == simulator_id
    ]
    if not current_entries:
        return
    if len(current_entries) != 1:
        raise ResearchHandoffError(
            f"record {manifest_entry['record_id']!r} has {len(current_entries)} "
            f"curated {simulator_id} entries; a repeat-drive proposal cannot choose "
            "which one to review"
        )
    if case.get("classification") != "curated-identity-comparison":
        raise ResearchHandoffError(
            f"record {manifest_entry['record_id']!r} already has a {simulator_id} "
            "entry, but this case is not routed as a curated identity comparison"
        )

    replacement = copy.deepcopy(staged["record"]["simulators"][0])
    replacement["overrides"] = copy.deepcopy(
        manifest_entry.get("simulator_overrides") or []
    )
    shift_actuation = (manifest_entry.get("control_overrides") or {}).get(
        "shift_actuation"
    )
    if shift_actuation:
        replacement["behavior"]["shift_type"] = shift_actuation
    changes = _behavior_changes(current_entries[0], replacement)
    observation_id = staged.get("observation_id", "the repeat guided drive")

    if not changes:
        manifest_entry["compatible_implementation"] = {
            "basis": (
                f"Repeat guided drive {observation_id} independently reproduced "
                f"the curated {simulator_id.upper()} behavior and effective overrides "
                "without a material difference."
            )
        }
        return

    approval_path = (
        root
        / "curation"
        / f"{simulator_id}-approved-{manifest_entry['record_id']}.json"
    )
    if not approval_path.is_file():
        raise ResearchHandoffError(
            f"the repeat {simulator_id} drive needs a correction, but its curated "
            f"approval is missing: {approval_path}"
        )
    approval = _read_json(approval_path, "curated simulator approval")
    source_registry = _read_json(
        root / "data" / "v1" / "sources.json", "registered source registry"
    )
    source_types = {
        source["source_id"]: source["source_type"]
        for source in source_registry["sources"]
    }
    live_refs = [
        ref
        for ref in current_entries[0].get("source_refs", [])
        if source_types.get(ref) == "in-game-observation"
    ]
    prior_history = approval.get("correction_history") or []
    latest_replacement = (
        prior_history[-1].get("replacement_source_ref") if prior_history else None
    )
    if latest_replacement in live_refs:
        superseded_source = latest_replacement
    elif len(live_refs) == 1:
        superseded_source = live_refs[0]
    else:
        raise ResearchHandoffError(
            f"the curated {simulator_id} entry has {len(live_refs)} live observation "
            "sources; final review must identify which one the correction supersedes"
        )

    change_summary = "; ".join(
        f"{change['path']} from {change['from']!r} to {change['to']!r}"
        for change in changes
    )
    review_notes = " ".join(str(note) for note in staged.get("review_notes", []))
    basis = (
        f"Repeat guided drive {observation_id} materially changed the reviewed "
        f"{simulator_id.upper()} result: {change_summary}."
    )
    if review_notes:
        basis += f" {review_notes}"
    manifest_entry["correct_existing_simulator"] = {
        "basis": basis,
        "supersedes_source_ref": superseded_source,
        "supersedes_observed_through": approval["observed_through"],
        "corrected_behavior_paths": [change["path"] for change in changes],
    }


def _prepare_curated_comparison(
    root: Path,
    cases_directory: Path,
    issue_number: int,
    dataset_version: str | None,
) -> dict[str, Any]:
    """Prepare an exact-match comparison without re-researching its identity."""
    case_directory = cases_directory / f"issue-{issue_number}"
    case = _read_json(case_directory / "case.json", "review case")
    if (
        case.get("state") not in {"review-needed", "manifest-review"}
        or case.get("classification") != "curated-identity-comparison"
        or (case.get("research") or {}).get("status") != "not-required"
    ):
        raise ResearchHandoffError(
            f"issue #{issue_number} is not an exact curated-identity comparison"
        )
    receipt = _read_json(
        case_directory / case["artifacts"]["receipt"], "intake receipt"
    )
    matched_ids = sorted(
        {
            str(match["record_id"])
            for match in receipt.get("curated_matches", [])
            if isinstance(match, dict) and match.get("record_id")
        }
    )
    if len(matched_ids) != 1:
        raise ResearchHandoffError(
            f"issue #{issue_number} matched {len(matched_ids)} curated records; "
            "a maintainer must resolve the identity before comparison review"
        )
    record_id = matched_ids[0]
    existing_record = _existing_record(root, record_id)
    if existing_record is None:
        raise ResearchHandoffError(
            f"issue #{issue_number} matched missing curated record {record_id!r}"
        )
    staged = _read_json(
        case_directory / case["artifacts"]["staged_bundle"], "staged bundle"
    )
    simulator_id = staged["record"]["simulators"][0]["simulator"]
    if not any(
        entry.get("simulator") == simulator_id
        for entry in existing_record.get("simulators", [])
    ):
        raise ResearchHandoffError(
            f"issue #{issue_number} exactly matched {record_id!r}, but that record "
            f"has no existing {simulator_id} entry to compare or correct"
        )

    registry = _read_json(
        root / "data" / "v1" / "sources.json", "registered source registry"
    )
    sources_by_id = {source["source_id"]: source for source in registry["sources"]}
    registered_refs: list[str] = []
    independent_refs: list[str] = []
    for claim in existing_record.get("provenance", {}).get("claims", []):
        for source_id in claim.get("source_refs", []):
            source = sources_by_id.get(source_id)
            if source is None:
                continue
            if source_id not in registered_refs:
                registered_refs.append(source_id)
            if (
                source.get("source_type")
                not in {"in-game-observation", "official-simulator"}
                and source_id not in independent_refs
            ):
                independent_refs.append(source_id)
    if not registered_refs:
        raise ResearchHandoffError(
            f"curated record {record_id!r} has no registered provenance source "
            "to anchor a correction review"
        )
    # Some deliberately simulator-native or legacy records have no independent
    # real-car source because no exact real-world chassis is assigned. A repeat
    # drive may still correct that simulator entry: retain the record's audited
    # source set without presenting it as new real-car evidence. The correction
    # gate below prevents the incoming authentic layer from filling or changing
    # any baseline value.
    baseline_refs = independent_refs or registered_refs
    legacy_baseline = not independent_refs
    reviewed_sources = [
        {
            "source_id": source_id,
            "title": sources_by_id[source_id]["title"],
            "registration": "already registered",
        }
        for source_id in baseline_refs
    ]

    claims = existing_record["provenance"]["claims"]
    identity_claim = next(
        (claim for claim in claims if "/identity" in claim.get("paths", [])),
        claims[0],
    )
    specification_claim = next(
        (
            claim
            for claim in claims
            if any(
                path.endswith("/forward_gears")
                or path.endswith("/gearbox_type")
                for path in claim.get("paths", [])
            )
        ),
        identity_claim,
    )
    sourced_paths = sorted(
        {
            path
            for claim in claims
            if any(ref in baseline_refs for ref in claim.get("source_refs", []))
            for path in claim.get("paths", [])
            if str(path).startswith("/authentic_controls/")
        }
    )
    index = _read_json(root / "data" / "v1" / "index.json", "dataset index")
    proposed_version = dataset_version or _next_patch(index["dataset_version"])
    identity = existing_record["identity"]
    staged_controls = staged["record"]["authentic_controls"]
    real_controls = existing_record["authentic_controls"]
    confidence = str(identity_claim.get("confidence") or "high")
    observation_id = staged.get("observation_id", "the guided drive")
    simulator_name = simulator_label(simulator_id)
    manifest_entry: dict[str, Any] = {
        "record_id": record_id,
        "bundle": _bundle_reference(
            root,
            case_directory / case["artifacts"]["staged_bundle"],
        ),
        "display_name": identity["display_name"],
        "class": identity["class"],
        "manufacturer": identity["manufacturer"],
        "model": identity["model"],
        "year": copy.deepcopy(identity["year"]),
        "real_world_identity_notes": identity["real_world_identity_notes"],
        "real_world_source_refs": baseline_refs,
        "confidence": confidence,
        "confidence_basis": (
            f"The exact {simulator_name} identity already belongs to curated record "
            f"{record_id}; {observation_id} is reviewed only as new simulator "
            "implementation evidence."
        ),
        "identity_basis": str(identity_claim.get("basis") or "Curated identity retained."),
        "specification_basis": str(
            specification_claim.get("basis") or "Curated control baseline retained."
        ),
        "control_overrides": _control_overrides(staged_controls, real_controls),
        "simulator_overrides": _simulator_overrides(
            staged_controls,
            real_controls,
            staged,
        ),
        "confidence_notes": (
            f"Identity and authentic controls are retained from curated record "
            f"{record_id}. Only the exact {simulator_name} behavior observed in "
            f"{observation_id} is under comparison review."
            + (
                " The existing record has no independent real-world source; its "
                "registered legacy provenance is retained without treating this "
                "drive as new authentic-control evidence."
                if legacy_baseline
                else ""
            )
        ),
        "sourced_control_paths": sourced_paths,
        "control_notes": copy.deepcopy(real_controls.get("notes") or []),
        "scope_notes": (
            "Exact simulator identity matched an existing curated entry; this review "
            "classifies the new guided drive as compatible evidence or an audited "
            "simulator correction without reopening real-car identity research."
        ),
        "live_source_url": case["issue"]["url"],
        "live_source_notes": staged["source"]["notes"],
    }
    if identity.get("variant"):
        manifest_entry["variant"] = identity["variant"]
    if existing_record.get("driver_summary"):
        manifest_entry["driver_summary"] = existing_record["driver_summary"]
    _same_simulator_disposition(
        root,
        case,
        staged,
        manifest_entry,
        existing_record,
    )
    manifest = {
        "schema_version": "1.0.0",
        "dataset_version": proposed_version,
        "approved_at": date.today().isoformat(),
        "records": [manifest_entry],
    }
    sources_proposal = {"schema_version": "1.0.0", "sources": []}
    return _write_review_proposal(
        root,
        case_directory,
        case,
        staged,
        manifest,
        sources_proposal,
        reviewed_sources,
    )


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
        case.get("state") in {"review-needed", "manifest-review"}
        and case.get("classification") == "curated-identity-comparison"
    ):
        return _prepare_curated_comparison(
            root,
            cases_directory,
            issue_number,
            dataset_version,
        )
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
    existing_record = _existing_record(root, identity["record_id"])
    # An existing record owns the real-car baseline. Compare the new simulator
    # drive with that baseline, not with a less-informed research draft, or the
    # proposal manufactures redundant overrides for values already curated.
    simulator_baseline = (
        existing_record["authentic_controls"]
        if identity["record_action"] == "use-existing" and existing_record is not None
        else real_controls
    )
    simulator_overrides = _simulator_overrides(
        staged_controls, simulator_baseline, staged
    )
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
    bundle_reference = _bundle_reference(root, bundle_path)
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
    _same_simulator_disposition(
        root,
        case,
        staged,
        manifest_entry,
        existing_record,
    )
    if existing_record and existing_record.get("driver_summary"):
        # Adding or correcting a simulator must not erase reviewed record-wide
        # prose merely because the maintainer did not ask to regenerate it.
        manifest_entry["driver_summary"] = existing_record["driver_summary"]
    manifest = {
        "schema_version": "1.0.0",
        "dataset_version": proposed_version,
        "approved_at": _proposal_date(result),
        "records": [manifest_entry],
    }
    sources_proposal = {"schema_version": "1.0.0", "sources": candidate_sources}
    return _write_review_proposal(
        root,
        case_directory,
        case,
        staged,
        manifest,
        sources_proposal,
        reviewed_sources,
    )


def generate_driver_summary_proposal(
    root: Path,
    cases_directory: Path,
    issue_number: int,
) -> dict[str, Any]:
    """Generate and dry-run a record-wide summary inside a review proposal."""
    root = root.resolve()
    case_directory = cases_directory / f"issue-{issue_number}"
    case = _read_json(case_directory / "case.json", "review case")
    if case.get("state") != "manifest-review":
        raise ResearchHandoffError(
            f"issue #{issue_number} must be in manifest review before drafting a driver summary"
        )
    if (case.get("review_proposal") or {}).get("dry_run") != "passed":
        raise ResearchHandoffError(
            f"issue #{issue_number} has no passed promotion dry run to summarize"
        )

    artifacts = case.get("artifacts") or {}
    required = (
        "staged_bundle",
        "review_manifest_proposal",
        "source_proposal",
        "preview_record",
    )
    missing = [name for name in required if not artifacts.get(name)]
    if missing:
        raise ResearchHandoffError(
            f"issue #{issue_number} is missing review artifacts: {', '.join(missing)}"
        )
    staged = _read_json(
        case_directory / artifacts["staged_bundle"], "staged bundle"
    )
    manifest_path = case_directory / artifacts["review_manifest_proposal"]
    manifest = _read_json(manifest_path, "review manifest proposal")
    sources_proposal = _read_json(
        case_directory / artifacts["source_proposal"], "source proposal"
    )
    current_preview = _read_json(
        case_directory / artifacts["preview_record"], "preview record"
    )

    summary, disagreements = generate_driver_summary(current_preview)
    manifest["records"][0]["driver_summary"] = summary
    candidate_sources = sources_proposal.get("sources") or []
    preview_record, preview_approval, preview_live_source = _dry_run_review_proposal(
        root,
        staged,
        manifest,
        candidate_sources,
    )

    _write_json(manifest_path, manifest)
    _write_json(case_directory / artifacts["preview_record"], preview_record)
    _write_json(case_directory / artifacts["preview_approval"], preview_approval)
    _write_json(case_directory / artifacts["preview_live_source"], preview_live_source)
    reviewed_sources = _reviewed_sources(root, manifest, candidate_sources)
    (case_directory / artifacts["final_review"]).write_text(
        _proposal_summary(case, manifest, reviewed_sources, preview_record),
        encoding="utf-8",
    )

    disagreement_note = (
        "- Simulator disagreements handled: " + ", ".join(disagreements)
        if disagreements
        else "- Simulator disagreements handled: none in the driver-technique fields"
    )
    summary_artifact_path = case_directory / "driver-summary.md"
    summary_artifact_path.write_text(
        f"""# Generated driver summary: issue #{issue_number}

## Draft

> {summary}

## Accuracy boundary

- Derived from the reviewed authentic control baseline in the passed promotion preview
{disagreement_note}
- Unknown values stay explicit and produce conservative driver advice
- No gearbox construction, identity detail, or historical fact is inferred

This text is now in the proposed manifest and the regenerated preview record. Review it in context before approving promotion.
""",
        encoding="utf-8",
    )
    case["artifacts"]["driver_summary"] = summary_artifact_path.name
    proposal = case.setdefault("review_proposal", {})
    proposal["driver_summary"] = {
        "status": "generated",
        "generated_at": _now(),
        "simulator_disagreements": disagreements,
    }
    proposal["dry_run"] = "passed"
    case["updated_at"] = _now()
    _write_json(case_directory / "case.json", case)
    return {
        "issue": issue_number,
        "state": case["state"],
        "summary": summary,
        "artifact": str(summary_artifact_path),
        "preview_record": str(case_directory / artifacts["preview_record"]),
        "dry_run": "passed",
    }

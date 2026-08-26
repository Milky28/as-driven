from __future__ import annotations

from datetime import date, datetime, timezone
import json
from pathlib import Path
import re
from typing import Any

from .schema_validation import validate_instance


RESEARCH_SCHEMA_VERSION = "1.0.0"
MAX_RESEARCH_RESULT_BYTES = 512 * 1024


class ResearchHandoffError(ValueError):
    pass


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _case_path(cases_directory: Path, issue_number: int) -> Path:
    return cases_directory / f"issue-{issue_number}" / "case.json"


def _read_json(path: Path, label: str) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exception:
        raise ResearchHandoffError(f"could not read {label} {path}: {exception}") from exception
    if not isinstance(payload, dict):
        raise ResearchHandoffError(f"{label} {path} is not a JSON object")
    return payload


def _load_case(cases_directory: Path, issue_number: int) -> tuple[Path, dict[str, Any]]:
    path = _case_path(cases_directory, issue_number)
    if not path.is_file():
        raise ResearchHandoffError(
            f"review case for issue #{issue_number} does not exist; run review-submissions sync"
        )
    case = _read_json(path, "review case")
    if case.get("state") == "intake-error":
        raise ResearchHandoffError(
            f"issue #{issue_number} has an intake error that must be resolved first"
        )
    return path.parent, case


def _family_key(value: str) -> str:
    without_year = re.sub(r"\b(?:19|20)\d{2}\b", " ", value.lower())
    return " ".join(re.findall(r"[a-z0-9]+", without_year))


def _record_source_refs(record: dict[str, Any]) -> list[str]:
    refs: set[str] = set()
    for claim in record.get("provenance", {}).get("claims", []):
        refs.update(str(value) for value in claim.get("source_refs", []))
    return sorted(refs)


def related_record_leads(
    root: Path,
    case: dict[str, Any],
    receipt: dict[str, Any],
) -> dict[str, Any]:
    data_dir = root / "data" / "v1"
    index = _read_json(data_dir / "index.json", "dataset index")
    sources_registry = _read_json(data_dir / "sources.json", "source registry")
    source_by_id = {
        source["source_id"]: source
        for source in sources_registry.get("sources", [])
        if isinstance(source, dict) and source.get("source_id")
    }
    telemetry_name = str(
        case.get("observation", {}).get("identity", {}).get("telemetry_name") or ""
    )
    family = _family_key(telemetry_name)
    exact_ids = {
        str(match["record_id"])
        for match in receipt.get("curated_matches", [])
        if isinstance(match, dict) and match.get("record_id")
    }
    # Records the submission may be a second simulator's view of. Suggested by
    # intake, never matched, and listed so the research can settle them.
    candidate_ids = {
        str(match["record_id"])
        for match in receipt.get("curated_candidates", [])
        if isinstance(match, dict) and match.get("record_id")
    } - exact_ids

    records: list[dict[str, Any]] = []
    refs: set[str] = set()
    for relative in index.get("records", []):
        record = _read_json(data_dir / relative, "curated record")
        display_name = str(record.get("identity", {}).get("display_name") or "")
        is_exact = record.get("record_id") in exact_ids
        is_candidate = record.get("record_id") in candidate_ids
        is_family = bool(family) and _family_key(display_name) == family
        if not is_exact and not is_candidate and not is_family:
            continue
        source_refs = _record_source_refs(record)
        refs.update(source_refs)
        records.append(
            {
                "record_id": record.get("record_id"),
                "display_name": display_name,
                "year": record.get("identity", {}).get("year"),
                "class": record.get("identity", {}).get("class"),
                "real_world_identity_notes": record.get("identity", {}).get(
                    "real_world_identity_notes"
                ),
                "source_refs": source_refs,
                "relationship": (
                    "exact-curated-identity" if is_exact
                    else "candidate-same-car-another-simulator" if is_candidate
                    else "same-name-with-year-removed"
                ),
            }
        )
    sources = [
        {
            "source_id": ref,
            "title": source_by_id[ref].get("title"),
            "publisher": source_by_id[ref].get("publisher"),
            "url": source_by_id[ref].get("url"),
            "source_type": source_by_id[ref].get("source_type"),
        }
        for ref in sorted(refs)
        if ref in source_by_id
        and source_by_id[ref].get("source_type") != "in-game-observation"
    ]
    return {"records": records[:12], "sources": sources[:40]}


def _result_template(case: dict[str, Any]) -> dict[str, Any]:
    return {
        "$schema": "../../../schema/v1/submission-research-result.schema.json",
        "schema_version": RESEARCH_SCHEMA_VERSION,
        "case_id": case["case_id"],
        "research_status": "partial",
        "researched_at": _now(),
        "researcher": {
            "name": "REPLACE-WITH-RESEARCHER",
            "kind": "ai-assisted",
            "model": None,
        },
        "identity": {
            "status": "unresolved",
            "record_action": "undetermined",
            "record_id": None,
            "display_name": None,
            "manufacturer": None,
            "model": None,
            "year": None,
            "class": None,
            "real_world_identity_notes": None,
            "confidence": "unknown",
            "basis": "Research not completed.",
            "confusion_risks": [],
        },
        "sources": [],
        "claims": [],
        "open_questions": ["Complete the identity and authentic-controls research."],
        "notes": "Replace this template with the structured research result.",
    }


def _research_questions(staged: dict[str, Any]) -> list[str]:
    record = staged.get("record", {})
    transmission = record.get("authentic_controls", {}).get("transmission", {})
    wheel = (
        record.get("authentic_controls", {})
        .get("steering", {})
        .get("wheel_rim", {})
    )
    return [
        "Establish the exact real car: manufacturer, model, year/generation, racing specification, and class. Distinguish similarly named adjacent versions.",
        "Decide whether this belongs to an existing simulator-independent record or needs a new real-car record id. Treat the simulator name only as a research lead.",
        f"Find real-car evidence for forward gears, gearbox construction, actuation, and pattern. The simulator observation staged: {json.dumps({key: transmission.get(key) for key in ('forward_gears', 'gearbox_type', 'shift_actuation', 'shift_pattern')}, ensure_ascii=False)}.",
        "Look for cockpit or interior photographs of the exact car. What the driver operates is a visual fact that written sources routinely omit: whether the shifter is a lever or paddles, and where first gear sits in the gate. A photograph showing the gate settles a dogleg, which prose describing the gearbox usually will not. Say what is visible in the image and no more, and never read a gate off a knob engraving alone unless the engraving is legible.",
        "Establish whether a physical clutch control exists and what the driver uses for standing starts, running upshifts, and running downshifts. Do not infer pedal presence or launch technique merely from gearbox construction.",
        "Establish throttle-lift, automatic cut, manual blip, and automatic blip behavior where authoritative evidence actually states it. Simulator behavior is comparison evidence, not the real-car baseline.",
        f"Establish the physical wheel-rim shape, integrated display, shift lights, and open-top construction. The observed simulator cockpit staged: {json.dumps(wheel, ensure_ascii=False)}.",
        "The rim is decided from a photograph of it, not from the car's class, and in this order: does it have molded grips at 9 and 3 with a control face between them, so the hands stay put (gt-formula), or is it a continuous band gripped anywhere - and then is that band a circle (round) or flattened top or bottom (d-shaped)? A 1967 single-seater with a plain wooden rim is round. Where the flat is slight enough that either answer is defensible, say so and return not-established rather than choosing: that ambiguity is a known and recurring one, and a hedged answer recorded honestly is worth more than a confident one that four simulators will disagree with.",
        "For every field not present in the reviewed sources, return a not-established claim instead of converting absence into no.",
    ]


def _material_control_paths(staged: dict[str, Any]) -> list[str]:
    controls = staged.get("record", {}).get("authentic_controls", {})

    def visit(value: Any, prefix: str) -> list[str]:
        if isinstance(value, dict):
            paths: list[str] = []
            for key, child in value.items():
                paths.extend(visit(child, f"{prefix}/{key}"))
            return paths
        return [prefix]

    return sorted(
        path
        for path in visit(controls, "/authentic_controls")
        if not path.endswith("/notes")
        and not path.endswith("/source_label")
        and path != "/authentic_controls/notes"
    )


def _brief_markdown(
    case: dict[str, Any],
    staged: dict[str, Any],
    leads: dict[str, Any],
    claim_paths: list[str],
) -> str:
    issue = case["issue"]
    observation = case["observation"]
    questions = "\n".join(f"{index}. {question}" for index, question in enumerate(_research_questions(staged), 1))
    return f"""# Research brief: issue #{issue['number']}

Research the real-world identity and authentic controls for this simulator observation. The result is a proposal for maintainer review, never a promotion decision.

## Non-negotiable boundaries

- Identity first, simulator behavior second. A telemetry or mod name does not prove which real car it depicts.
- Confirm every source describes the exact year, generation, specification, and configuration under review; call out nearby cars that can be confused with it.
- Prefer manufacturer, homologation, governing-body, team technical, or exact official documentation. Label secondary and community evidence honestly.
- Quote verbatim only as much as needed, and include printed page/PDF page, section, figure, timestamp, or another precise locator when one exists.
- Say `not-established` when a reviewed source is silent. Absence is not evidence of `no`.
- Keep real-car claims separate from the exact simulator version and implementation observed.
- A photograph is a source like any other. Register it with its origin and date, describe what is visible rather than what it suggests, and prefer a manufacturer or team image of the exact specification over a period shot of a sister car.
- Do not edit `data/v1`, `curation`, source registries, or the staged bundle. Write only the structured research result requested below.

## Case

```json
{json.dumps({"case_id": case['case_id'], "classification": case['classification'], "issue": issue, "attachment": case['attachment'], "observation": observation}, indent=2, ensure_ascii=False)}
```

## Mechanically staged observation

This is simulator evidence. `REVIEW-REQUIRED` and `unknown` values are intentional research gaps.

```json
{json.dumps({"record_id_lead": staged.get('record', {}).get('record_id'), "identity": staged.get('record', {}).get('identity'), "authentic_controls": staged.get('record', {}).get('authentic_controls'), "simulator": staged.get('record', {}).get('simulators', [None])[0]}, indent=2, ensure_ascii=False)}
```

## Related curated-record leads

These are deterministic research leads only: exact curated identity matches or display names equal after removing a four-digit year. They are not mappings and must be accepted or rejected from independent identity evidence.

```json
{json.dumps(leads, indent=2, ensure_ascii=False)}
```

## Questions

{questions}

## Required control claim paths

If `research_status` is `complete`, include an established or `not-established` claim for every path below. These are the material fields present in the staged observation.

```json
{json.dumps(_material_control_paths(staged), indent=2, ensure_ascii=False)}
```

## Other permitted claim paths

Use only the exact JSON pointers below for `claims[].path`. Do not infer a path from the staged observation's nesting or invent a shorthand. Paths not listed in the required section are optional. Include an optional path only when the research establishes or conflicts with it. Omit an optional numeric field when it is not established.

```json
{json.dumps(claim_paths, indent=2, ensure_ascii=False)}
```

`proposed_value` must use the target field's JSON type. For a required numeric field that permits no established value, use JSON `null`, not the string `"unknown"`. Use `"unknown"` only for an enum that explicitly allows that value. In particular, do not add `degrees_of_rotation` or `diameter_mm` merely to report that they were not established when those paths are absent from the required list.

## Required output

Return one JSON object conforming to `schema/v1/submission-research-result.schema.json`. Start from `research-result.template.json` in this case directory and save the completed object as `research-result.json` in the same directory. The maintainer workbench discovers that file when its local queue is refreshed.

Every established, conflicting, or negative field-level finding belongs in `claims`. `source_refs` must name candidate sources declared in `sources`. Every source object must include all schema-required fields, including `retrieved_at`. For a negative result, list the exact sources reviewed and explain what they cover without claiming their silence proves a negative. Use `research_status: complete` only when the evidence is adequate for final maintainer review; use `partial` or `blocked` otherwise.

When reusing a `source_id` from the related curated-record leads, copy its `title`, `publisher`, `url`, and `source_type` exactly. Those registered values are canonical, including punctuation, accents, and capitalization.
"""


def generate_research_brief(
    root: Path,
    cases_directory: Path,
    issue_number: int,
) -> dict[str, Any]:
    root = root.resolve()
    case_directory, case = _load_case(cases_directory, issue_number)
    staged_path = case_directory / case["artifacts"]["staged_bundle"]
    staged = _read_json(staged_path, "staged bundle")
    receipt = _read_json(case_directory / case["artifacts"]["receipt"], "intake receipt")
    leads = related_record_leads(root, case, receipt)
    research_schema = _read_json(
        root / "schema" / "v1" / "submission-research-result.schema.json",
        "research-result schema",
    )
    claim_paths = sorted(_research_claim_schemas(root, research_schema))

    brief_path = case_directory / "research-brief.md"
    template_path = case_directory / "research-result.template.json"
    brief_path.write_text(
        _brief_markdown(case, staged, leads, claim_paths),
        encoding="utf-8",
    )
    _write_json(template_path, _result_template(case))
    case.setdefault("artifacts", {})["research_brief"] = brief_path.name
    case["artifacts"]["research_result_template"] = template_path.name
    case.setdefault("research", {})["required"] = True
    if case["research"].get("status") not in {"complete", "partial", "blocked"}:
        case["research"]["status"] = "brief-ready"
    case["research"]["brief_generated_at"] = _now()
    case["updated_at"] = _now()
    _write_json(case_directory / "case.json", case)
    return {
        "issue": issue_number,
        "case_id": case["case_id"],
        "brief": str(brief_path),
        "template": str(template_path),
        "related_records": len(leads["records"]),
    }


def generate_research_briefs(
    root: Path,
    cases_directory: Path,
    issue_numbers: set[int] | None = None,
) -> list[dict[str, Any]]:
    available: list[int] = []
    if cases_directory.exists():
        for path in cases_directory.glob("issue-*/case.json"):
            try:
                number = int(path.parent.name.removeprefix("issue-"))
                case = _read_json(path, "review case")
            except (ValueError, ResearchHandoffError):
                continue
            if issue_numbers is not None and number not in issue_numbers:
                continue
            if issue_numbers is None and not case.get("research", {}).get("required"):
                continue
            if issue_numbers is None and case.get("research", {}).get("status") == "complete":
                continue
            if case.get("state") == "intake-error":
                continue
            available.append(number)
    if issue_numbers is not None:
        missing = sorted(issue_numbers - set(available))
        if missing:
            raise ResearchHandoffError(
                "no research-pending review case for issue(s): "
                + ", ".join(f"#{number}" for number in missing)
            )
    return [
        generate_research_brief(root, cases_directory, number)
        for number in sorted(available)
    ]


def _resolve_schema_node(schema: dict[str, Any], node: dict[str, Any]) -> dict[str, Any]:
    while isinstance(node.get("$ref"), str) and node["$ref"].startswith("#/"):
        current: Any = schema
        for token in node["$ref"][2:].split("/"):
            current = current[token.replace("~1", "/").replace("~0", "~")]
        node = current
    return node


def _leaf_schema_paths(
    schema: dict[str, Any],
    node: dict[str, Any],
    prefix: str,
) -> dict[str, dict[str, Any]]:
    node = _resolve_schema_node(schema, node)
    properties = node.get("properties")
    if not isinstance(properties, dict):
        return {prefix: node}
    paths: dict[str, dict[str, Any]] = {}
    for key, child in properties.items():
        if not isinstance(child, dict):
            continue
        paths.update(
            _leaf_schema_paths(
                schema,
                child,
                f"{prefix}/{key}",
            )
        )
    return paths


def _research_claim_schemas(
    root: Path,
    research_schema: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    car_schema = _read_json(
        root / "schema" / "v1" / "car-record.schema.json",
        "car-record schema",
    )
    controls_node = car_schema["properties"]["authentic_controls"]
    claims = _leaf_schema_paths(
        car_schema,
        controls_node,
        "/authentic_controls",
    )
    claims = {
        path: node
        for path, node in claims.items()
        if not path.endswith("/notes") and not path.endswith("/source_label")
    }
    identity_node = _resolve_schema_node(
        research_schema,
        research_schema["properties"]["identity"],
    )
    identity_fields = {
        "record_action",
        "record_id",
        "display_name",
        "manufacturer",
        "model",
        "year",
        "class",
        "real_world_identity_notes",
    }
    for key in identity_fields:
        claims[f"/identity/{key}"] = _resolve_schema_node(
            research_schema,
            identity_node["properties"][key],
        )
    return claims


def validate_research_result(
    root: Path,
    case: dict[str, Any],
    result: dict[str, Any],
    label: str,
) -> list[str]:
    schema = _read_json(
        root / "schema" / "v1" / "submission-research-result.schema.json",
        "research-result schema",
    )
    errors = validate_instance(result, schema, label)
    claim_schemas = _research_claim_schemas(root, schema)
    if result.get("case_id") != case.get("case_id"):
        errors.append(
            f"{label}.case_id: expected {case.get('case_id')!r} for this review case"
        )
    sources = result.get("sources")
    source_ids: list[str] = []
    if isinstance(sources, list):
        source_ids = [
            source.get("source_id")
            for source in sources
            if isinstance(source, dict) and isinstance(source.get("source_id"), str)
        ]
        if len(source_ids) != len(set(source_ids)):
            errors.append(f"{label}.sources: source_id values must be unique")
    known_sources = set(source_ids)
    claims = result.get("claims")
    identity_claim_paths: set[str] = set()
    if isinstance(claims, list):
        for index, claim in enumerate(claims):
            if not isinstance(claim, dict):
                continue
            path = str(claim.get("path") or "")
            claim_schema = claim_schemas.get(path)
            if claim_schema is None:
                errors.append(
                    f"{label}.claims[{index}].path: unknown research field {path!r}"
                )
            elif path.startswith("/authentic_controls/") and "proposed_value" in claim:
                proposed_value = claim["proposed_value"]
                claim_types = claim_schema.get("type")
                numeric_types = (
                    {claim_types}
                    if isinstance(claim_types, str)
                    else set(claim_types or [])
                )
                if (
                    claim.get("finding") == "not-established"
                    and proposed_value == "unknown"
                    and numeric_types.intersection({"integer", "number"})
                ):
                    errors.append(
                        f"{label}.claims[{index}].proposed_value: numeric fields cannot use "
                        "the string 'unknown'; use null when the field permits it, or omit "
                        "an optional not-established claim"
                    )
                else:
                    errors.extend(
                        validate_instance(
                            proposed_value,
                            claim_schema,
                            f"{label}.claims[{index}].proposed_value",
                        )
                    )
            refs = claim.get("source_refs")
            if isinstance(refs, list):
                unknown = sorted(set(refs) - known_sources)
                if unknown:
                    errors.append(
                        f"{label}.claims[{index}].source_refs: unknown candidate source(s) {unknown!r}"
                    )
                if not refs:
                    errors.append(
                        f"{label}.claims[{index}].source_refs: findings need at least one reviewed source"
                    )
            if path.startswith("/identity/"):
                identity_claim_paths.add(path)

    identity = result.get("identity")
    status = result.get("research_status")
    if isinstance(identity, dict):
        identity_status = identity.get("status")
        action = identity.get("record_action")
        record_id = identity.get("record_id")
        if action == "undetermined" and record_id is not None:
            errors.append(f"{label}.identity.record_id: must be null when action is undetermined")
        record_path = root / "data" / "v1" / "cars" / f"{record_id}.json" if record_id else None
        if action == "use-existing" and (record_path is None or not record_path.is_file()):
            errors.append(
                f"{label}.identity.record_id: use-existing requires a curated record that exists"
            )
        if action == "create-new" and record_path is not None and record_path.exists():
            errors.append(
                f"{label}.identity.record_id: create-new conflicts with an existing curated record"
            )
        if identity_status == "established":
            for key in ("record_id", "display_name", "manufacturer", "model", "year"):
                if identity.get(key) is None or identity.get(key) == "":
                    errors.append(
                        f"{label}.identity.{key}: established identity requires a value"
                    )
            year = identity.get("year")
            if isinstance(year, dict) and not any(
                year.get(key) is not None and year.get(key) != ""
                for key in ("from", "to", "label")
            ):
                errors.append(
                    f"{label}.identity.year: established identity needs a meaningful year or label"
                )
            if not str(identity.get("basis") or "").strip():
                errors.append(
                    f"{label}.identity.basis: established identity requires a falsifiable basis"
                )
            if action == "undetermined":
                errors.append(
                    f"{label}.identity.record_action: established identity needs a record action"
                )
            required_identity_claims = {
                "/identity/manufacturer",
                "/identity/model",
                "/identity/year",
            }
            missing_identity_claims = sorted(
                required_identity_claims - identity_claim_paths
            )
            if missing_identity_claims:
                errors.append(
                    f"{label}.claims: established identity needs sourced claims for "
                    f"{missing_identity_claims!r}"
                )
        if status == "complete" and identity_status not in {"established", "conflicting"}:
            errors.append(
                f"{label}.research_status: complete research needs established or explicitly conflicting identity"
            )
    return errors


def import_research_result(
    root: Path,
    cases_directory: Path,
    issue_number: int,
    input_path: Path,
    replace: bool = False,
) -> dict[str, Any]:
    root = root.resolve()
    case_directory, case = _load_case(cases_directory, issue_number)
    try:
        raw = input_path.read_bytes()
    except OSError as exception:
        raise ResearchHandoffError(f"could not read research result: {exception}") from exception
    if len(raw) > MAX_RESEARCH_RESULT_BYTES:
        raise ResearchHandoffError(
            f"research result is {len(raw):,} bytes; maximum is {MAX_RESEARCH_RESULT_BYTES:,}"
        )
    try:
        result = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exception:
        raise ResearchHandoffError(f"could not parse research result: {exception}") from exception
    if not isinstance(result, dict):
        raise ResearchHandoffError("research result is not a JSON object")
    errors = validate_research_result(root, case, result, str(input_path))
    if errors:
        raise ResearchHandoffError("research result validation failed:\n" + "\n".join(errors))

    destination = case_directory / "research-result.json"
    input_is_destination = input_path.resolve() == destination.resolve()
    already_registered = isinstance(
        case.get("artifacts", {}).get("research_result"), str
    )
    if destination.exists() and not replace and not (
        input_is_destination and not already_registered
    ):
        raise ResearchHandoffError(
            f"research result already exists for issue #{issue_number}; pass --replace to supersede local working state"
        )
    if not input_is_destination:
        destination.write_bytes(raw)
    research_status = result["research_status"]
    state_by_status = {
        "complete": "final-review",
        "partial": "identity-research",
        "blocked": "research-blocked",
    }
    previous_state = case.get("state")
    case["state"] = state_by_status[research_status]
    case.setdefault("artifacts", {})["research_result"] = destination.name
    case.setdefault("research", {})["required"] = True
    case["research"].update(
        {
            "status": research_status,
            "imported_at": _now(),
            "researched_at": result["researched_at"],
            "researcher": result["researcher"],
            "previous_state": previous_state,
        }
    )
    case["updated_at"] = _now()
    _write_json(case_directory / "case.json", case)
    return {
        "issue": issue_number,
        "case_id": case["case_id"],
        "research_status": research_status,
        "state": case["state"],
        "result": str(destination),
    }


def discover_research_results(
    root: Path,
    cases_directory: Path,
) -> dict[str, Any]:
    """Validate and register completed result files written into case folders."""

    imported: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []
    if not cases_directory.exists():
        return {"found": 0, "imported": imported, "errors": errors}
    found = 0
    for case_path in sorted(cases_directory.glob("issue-*/case.json")):
        try:
            issue_number = int(case_path.parent.name.removeprefix("issue-"))
            case = _read_json(case_path, "review case")
        except (ValueError, ResearchHandoffError):
            continue
        if isinstance(case.get("artifacts", {}).get("research_result"), str):
            continue
        candidate = case_path.parent / "research-result.json"
        if not candidate.is_file():
            continue
        found += 1
        try:
            imported.append(
                import_research_result(
                    root,
                    cases_directory,
                    issue_number,
                    candidate,
                )
            )
        except ResearchHandoffError as exception:
            errors.append({"issue": issue_number, "error": str(exception)})
    return {"found": found, "imported": imported, "errors": errors}

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


SHEET_SOURCE = "ams2.coanda-sheet.v1.0.34"
FORUM_SOURCE = "ams2.reiza-forum.extended-car-info"
SIMHUB_SOURCE = "simhub.local-ams2-identities.9.11.22"


def _shift_action(
    *,
    clutch: str = "unknown",
    throttle_lift: str = "unknown",
    automatic_cut: str = "not-applicable",
    manual_blip: str = "not-applicable",
    automatic_blip: str = "not-applicable",
) -> dict[str, str]:
    return {
        "clutch": clutch,
        "throttle_lift": throttle_lift,
        "automatic_cut": automatic_cut,
        "manual_blip": manual_blip,
        "automatic_blip": automatic_blip,
    }


def build_ams2_record(
    candidate: dict[str, Any],
    approval: dict[str, Any],
    *,
    approved_at: str,
    verified_at: str,
) -> dict[str, Any]:
    identity_candidate = candidate["identity"]
    if candidate["source_row"] != approval["source_row"]:
        raise ValueError("approval source_row does not match candidate")
    if identity_candidate["display_name"] != approval["source_display_name"]:
        raise ValueError("approval source_display_name does not match candidate")

    controls = candidate["authentic_controls_candidate"]
    transmission_candidate = controls["transmission"]
    behavior = candidate["simulator_candidate"]["behavior"]
    auto_blip = behavior["auto_blip"]
    shift_cut = behavior["shift_cut"]
    identity: dict[str, Any] = {
        "display_name": approval["source_display_name"],
        "manufacturer": approval["manufacturer"],
        "model": approval["model"],
        "year": identity_candidate["year"],
        "class": identity_candidate["class"],
        "real_world_identity_notes": approval["identity_notes"],
    }
    if approval.get("variant"):
        identity["variant"] = approval["variant"]

    simulator_identities = [
        {"kind": "telemetry-name", "value": approval["telemetry_name"]}
    ]
    if approval["telemetry_name"] != approval["source_display_name"]:
        simulator_identities.append(
            {"kind": "display-name", "value": approval["source_display_name"]}
        )

    steering = dict(controls["steering"])
    steering["wheel_rim"] = dict(steering["wheel_rim"])
    steering["wheel_rim"]["notes"] = (
        "Raw sheet rim code retained; normalization is conservative."
    )

    record = {
        "$schema": "../../../schema/v1/car-record.schema.json",
        "schema_version": "1.0.0",
        "record_id": approval["record_id"],
        "identity": identity,
        "authentic_controls": {
            "transmission": {
                "forward_gears": transmission_candidate["forward_gears"],
                "gearbox_type": transmission_candidate["gearbox_type"],
                "shift_actuation": transmission_candidate["shift_actuation"],
                "shift_pattern": transmission_candidate["shift_pattern"],
                "upshift": _shift_action(
                    throttle_lift="unknown",
                    automatic_cut=shift_cut,
                ),
                "downshift": _shift_action(
                    throttle_lift="not-applicable",
                    automatic_cut="not-applicable",
                    manual_blip=(
                        "not-required" if auto_blip == "yes" else "unknown"
                    ),
                    automatic_blip=auto_blip,
                ),
                "standing_start_clutch": "unknown",
            },
            "steering": steering,
            "notes": [
                "Clutch and throttle technique remain unknown where the source only documents shift type, auto-blip, and shift cut.",
                f"Source chassis manufacturer: {identity_candidate['chassis_manufacturer']}.",
            ],
        },
        "simulators": [
            {
                "simulator": "ams2",
                "identities": simulator_identities,
                "behavior": behavior,
                "overrides": [],
                "verified_game_version": candidate["simulator_candidate"][
                    "verified_game_version"
                ],
                "verified_at": verified_at,
                "source_refs": [SHEET_SOURCE, FORUM_SOURCE, SIMHUB_SOURCE],
                "confidence": {
                    "level": "medium",
                    "basis": "Control data comes from the versioned community sheet; the telemetry alias is an exact, reviewed SimHub observation.",
                },
            }
        ],
        "provenance": {
            "claims": [
                {
                    "paths": [
                        "/identity",
                        "/authentic_controls",
                        "/simulators/0/behavior",
                    ],
                    "source_refs": [SHEET_SOURCE],
                    "confidence": "medium",
                    "basis": f"Conservative promotion of AMS2 sheet row {candidate['source_row']} with unsupported technique left unknown.",
                },
                {
                    "paths": ["/simulators/0/identities/0"],
                    "source_refs": [SIMHUB_SOURCE],
                    "confidence": "verified",
                    "basis": "Approved exact alias from the SimHub identity audit.",
                },
            ]
        },
        "updated_at": approved_at,
    }
    return record


def promote_approved_ams2(
    candidate_payload: dict[str, Any],
    audit_payload: dict[str, Any],
    approval_payload: dict[str, Any],
    data_directory: Path,
) -> list[Path]:
    candidates_by_row = {
        candidate["source_row"]: candidate
        for candidate in candidate_payload["candidates"]
    }
    suggested_pairs = {
        (item["source_row"], item["display_name"], item["telemetry_name"])
        for item in audit_payload["alias_suggestions"]
    }
    approved_at = approval_payload["approved_at"]
    verified_at = approval_payload["verified_at"]
    records = approval_payload["records"]

    cars_directory = data_directory / "cars"
    index_path = data_directory / "index.json"
    index = json.loads(index_path.read_text(encoding="utf-8"))
    new_paths: list[Path] = []
    generated: list[tuple[Path, dict[str, Any]]] = []
    for approval in records:
        pair = (
            approval["source_row"],
            approval["source_display_name"],
            approval["telemetry_name"],
        )
        if pair not in suggested_pairs:
            raise ValueError(f"approval is not backed by an alias suggestion: {pair}")
        candidate = candidates_by_row.get(approval["source_row"])
        if candidate is None:
            raise ValueError(f"candidate row not found: {approval['source_row']}")
        record = build_ams2_record(
            candidate,
            approval,
            approved_at=approved_at,
            verified_at=verified_at,
        )
        output = cars_directory / f"{approval['record_id']}.json"
        if output.exists():
            raise FileExistsError(f"refusing to overwrite curated record: {output}")
        generated.append((output, record))

    for output, record in generated:
        output.write_text(
            json.dumps(record, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        new_paths.append(output)
        relative = output.relative_to(data_directory).as_posix()
        index["records"].append(relative)

    index["records"] = sorted(set(index["records"]))
    index["dataset_version"] = approval_payload["dataset_version"]
    index["released_at"] = approved_at
    index_path.write_text(
        json.dumps(index, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    return new_paths

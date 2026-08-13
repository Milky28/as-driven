"""Stage a curated-record candidate from a guided-verification observation.

The SimHub plugin's "Contribute car data" guided drive writes a
`verification-observation` draft (schema/v1/verification-observation.schema.json).
That draft is staging evidence, not a curated record: the reviewer still has to
express it as a car record, cite a registered source, and write a curation
approval (see docs/verification-observations.md).

This importer does the mechanical, error-prone half of that reviewer step. It
maps an observation draft into:

* a staged car record (simulator behavior + the authentic-control fields the
  drive supports, everything else left ``unknown``);
* a `sources.json` evidence-entry stub for the live session;
* a `curation/` approval stub whose ``approved_controls`` are derived from the
  record with the exact mapping ``validate`` cross-checks, so a filled-in
  promotion validates cleanly.

It never writes into ``data/v1`` or ``curation`` and never invents real-world
identity or hardware: manufacturer, model, year, and real-world notes are left
as explicit ``REVIEW-REQUIRED`` placeholders for the human reviewer.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

REVIEW = "REVIEW-REQUIRED"

# A guided drive observes the *simulator*. Its clutch/move-off results are only
# comparable when the tester disabled automatic clutch and automatic shifting;
# docs/verification-observations.md is explicit that an unknown assist state
# makes those results non-comparable. When the profile is not clean, the
# affected authentic fields degrade to ``unknown`` instead of asserting a value.
def _assists_clean(assists: dict[str, Any]) -> bool:
    return (
        assists.get("automatic_clutch") == "disabled"
        and assists.get("automatic_shifting") == "disabled"
    )


def _state(value: str | None) -> str:
    # observedState (yes/no/unknown/not-tested) -> record state (yes/no/unknown).
    return value if value in {"yes", "no"} else "unknown"


def _clutch_from_clutchless(value: str | None) -> str:
    if value == "yes":
        return "not-required"
    if value == "no":
        return "required"
    return "unknown"


def _standing_start_clutch(move_off: str | None) -> str:
    if move_off == "yes":
        return "not-required"
    if move_off == "no":
        return "required"
    return "unknown"


# The observation records only the primary actuation mechanism. Derive gearbox
# and pattern only where the mechanism makes them unambiguous; H-pattern stays
# ``unknown`` because standard/dogleg layout and synchro/dog construction are
# not established by a guided drive.
_ACTUATION_DERIVATION = {
    "sequential-paddles": ("sequential", "sequential"),
    "sequential-stick": ("sequential", "sequential"),
    "automatic-lever": ("automatic", "automatic-gate"),
    "direct-selection": ("direct-drive", "direct"),
    "h-pattern": ("unknown", "unknown"),
    "unknown": ("unknown", "unknown"),
}


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().casefold()).strip("-")
    return slug or "unknown"


def derive_approved_controls(record: dict[str, Any]) -> dict[str, Any]:
    """Summarize a curated record the way ``validate`` cross-checks approvals.

    Mirrors ``_validate_car_approval`` so a generated approval agrees with its
    record. ``running_shift_clutch`` is omitted when the upshift and downshift
    clutch requirements differ, because one value cannot summarize them.
    """
    transmission = record["authentic_controls"]["transmission"]
    behavior = record["simulators"][0]["behavior"]
    wheel = behavior["wheel_rim_type"]
    controls: dict[str, Any] = {
        "forward_gears": transmission["forward_gears"],
        "shift_actuation": transmission["shift_actuation"],
        "shift_pattern": transmission["shift_pattern"],
        "standing_start_clutch": transmission["standing_start_clutch"],
        "throttle_lift": transmission["upshift"]["throttle_lift"],
        "automatic_cut": behavior["shift_cut"],
        "automatic_blip": behavior["auto_blip"],
        "manual_blip": transmission["downshift"]["manual_blip"],
        "wheel_rim_shape": wheel["normalized"],
    }
    for approval_name, behavior_name in (
        ("wheel_integrated_display", "integrated_display"),
        ("wheel_shift_lights", "shift_lights"),
        ("wheel_open_top", "open_top"),
    ):
        if behavior_name in wheel:
            controls[approval_name] = wheel[behavior_name]
    upshift_clutch = transmission["upshift"]["clutch"]
    if upshift_clutch == transmission["downshift"]["clutch"]:
        controls["running_shift_clutch"] = upshift_clutch
    return controls


def import_observation(
    observation: dict[str, Any], *, imported_at: str | None = None
) -> dict[str, Any]:
    """Map a guided-verification observation into a staged promotion bundle."""
    imported_at = imported_at or date.today().isoformat()

    simulator = observation["simulator"]
    game_version = observation["game_version"]
    identity = observation["identity"]
    telemetry_name = identity["telemetry_name"]
    telemetry_class = identity["telemetry_class"]
    assists = observation.get("assists", {})
    tests = observation["tests"]
    cockpit = observation["cockpit"]
    observed_at = observation["observed_at"]
    verified_at = observed_at[:10]  # date portion of the ISO date-time
    observation_id = observation["observation_id"]
    observer = observation.get("observer", "unknown")

    slug = _slug(telemetry_name)
    record_id = f"{simulator}.{slug}"
    source_id = f"{simulator}.local-live-{slug}-controls.{game_version}"

    clean = _assists_clean(assists)
    review_notes: list[str] = []
    if not clean:
        review_notes.append(
            "Automatic clutch/shifting were not both confirmed disabled; move-off "
            "and clutchless-shift results are treated as unknown per the evidence "
            "boundary. Re-drive with a clean assist profile to establish them."
        )

    actuation = cockpit["primary_shift_actuation"]
    gearbox_type, shift_pattern = _ACTUATION_DERIVATION.get(
        actuation, ("unknown", "unknown")
    )
    # A gate pattern seen in the cockpit beats one derived from the mechanism.
    # Deriving can only ever say "sequential" or "unknown"; it cannot tell a
    # dogleg layout from a standard H, and that difference moves first gear.
    observed_pattern = cockpit.get("shift_pattern")
    if observed_pattern and observed_pattern != "unknown":
        shift_pattern = observed_pattern
        if observed_pattern in {"standard-h", "dogleg-h"} and actuation == "h-pattern":
            review_notes.append(
                f"Gate pattern {observed_pattern} was read from the cockpit. Confirm it "
                "against a real-world source before treating it as a real-car claim."
            )
    if actuation == "unknown":
        review_notes.append(
            "Primary shift actuation was left unknown; shift_actuation, gearbox_type, "
            "and shift_pattern need cockpit-mechanism review."
        )

    standing_start_clutch = (
        _standing_start_clutch(tests.get("move_off_without_physical_clutch"))
        if clean
        else "unknown"
    )
    up_clutch = _clutch_from_clutchless(tests.get("clutchless_upshift")) if clean else "unknown"
    down_clutch = _clutch_from_clutchless(tests.get("clutchless_downshift")) if clean else "unknown"
    cut_state = _state(tests.get("automatic_cut"))
    blip_state = _state(tests.get("automatic_blip"))

    rim = cockpit["wheel_rim"]
    rim_shape = rim.get("shape", "unknown")
    rim_display = _state(rim.get("integrated_display"))
    rim_lights = _state(rim.get("shift_lights"))
    rim_open_top = _state(rim.get("open_top"))
    rim_source_label = "live-cockpit-observation"

    upshift = {
        "clutch": up_clutch,
        "throttle_lift": "unknown",
        "automatic_cut": cut_state,
        "manual_blip": "not-applicable",
        "automatic_blip": "not-applicable",
    }
    downshift = {
        "clutch": down_clutch,
        "throttle_lift": "not-applicable",
        "automatic_cut": "not-applicable",
        "manual_blip": "not-required" if blip_state == "yes" else "unknown",
        "automatic_blip": blip_state,
    }

    behavior_wheel = {
        "normalized": rim_shape,
        "integrated_display": rim_display,
        "shift_lights": rim_lights,
        "open_top": rim_open_top,
        "source_label": rim_source_label,
    }
    behavior = {
        "shift_type": actuation,
        "auto_blip": blip_state,
        "shift_cut": cut_state,
        "wheel_rim_type": behavior_wheel,
        "notes": [
            f"Observed live in {simulator.upper()} {game_version} via guided "
            f"verification observation {observation_id} by {observer}.",
        ],
    }

    record = {
        "$schema": "../../../schema/v1/car-record.schema.json",
        "schema_version": "1.0.0",
        "record_id": record_id,
        "identity": {
            "display_name": telemetry_name,
            "manufacturer": REVIEW,
            "model": REVIEW,
            "year": {"label": REVIEW},
            "class": telemetry_class,
            "real_world_identity_notes": (
                "Real-world identity (manufacturer, model, year) and any real-car "
                "hardware claims require independent evidence; the guided drive "
                "establishes simulator behavior only."
            ),
        },
        "authentic_controls": {
            "transmission": {
                "forward_gears": tests.get("forward_gears"),
                "gearbox_type": gearbox_type,
                "shift_actuation": actuation,
                "shift_pattern": shift_pattern,
                "upshift": upshift,
                "downshift": downshift,
                "standing_start_clutch": standing_start_clutch,
            },
            "steering": {
                "wheel_rim": {
                    "shape": rim_shape,
                    "integrated_display": rim_display,
                    "shift_lights": rim_lights,
                    "open_top": rim_open_top,
                    "source_label": rim_source_label,
                    "notes": rim.get("notes", "Observed from the cockpit during the guided drive."),
                }
            },
            "notes": [
                "Staged from a guided-verification observation; simulator behavior "
                "is observed, authentic real-car technique is asserted only where "
                "the drive supports it and is otherwise left unknown.",
            ],
        },
        "simulators": [
            {
                "simulator": simulator,
                "identities": [
                    {"kind": "telemetry-name", "value": telemetry_name},
                    {"kind": "class-id", "value": telemetry_class},
                ],
                "behavior": behavior,
                "overrides": [],
                "verified_game_version": game_version,
                "verified_at": verified_at,
                "source_refs": [source_id],
                "confidence": {
                    "level": "medium",
                    "basis": (
                        f"Single guided-verification drive ({observation_id}); "
                        "simulator behavior observed live, reviewer confirmation "
                        "and real-world evidence still required."
                    ),
                },
            }
        ],
        "provenance": {
            "claims": [
                {
                    "paths": ["/simulators/0/behavior", "/authentic_controls/transmission", "/authentic_controls/steering"],
                    "source_refs": [source_id],
                    "confidence": "medium",
                    "basis": (
                        f"Conservative promotion of guided-verification observation "
                        f"{observation_id}; unsupported technique left unknown."
                    ),
                },
                {
                    "paths": ["/identity/manufacturer", "/identity/model", "/identity/year"],
                    "source_refs": [source_id],
                    "confidence": "unknown",
                    "basis": "REVIEW-REQUIRED: real-world identity fields need independent evidence.",
                },
            ]
        },
        "notes": [
            "STAGED CANDIDATE from a guided-verification observation. Not curated, "
            "not indexed. Fill the REVIEW-REQUIRED identity fields, register the "
            "source, and promote via the approval before it enters data/v1.",
        ],
        "updated_at": imported_at,
    }

    # Derive approved_controls from the record with the SAME mapping validate.py
    # uses (see _validate_car_approval), so a filled-in promotion validates.
    approved_controls = derive_approved_controls(record)
    if "running_shift_clutch" not in approved_controls:
        review_notes.append(
            "Upshift and downshift clutch requirements differ, so the approval "
            "omits running_shift_clutch. Confirm the clutch modeling before promotion."
        )

    source = {
        "source_id": source_id,
        "title": f"Live {simulator.upper()} {telemetry_name} guided-verification drive",
        "publisher": f"Local {simulator.upper()} observation",
        "url": REVIEW,
        "archive_url": None,
        "source_type": "in-game-observation",
        "published_or_updated_at": None,
        "retrieved_at": verified_at,
        "reuse_status": "facts-only-review",
        "notes": (
            f"Guided-verification observation {observation_id} by {observer}; "
            f"{simulator.upper()} {game_version}. Summarize the confirmed move-off, "
            "gear count, cut/blip, and cockpit rim before registering."
        ),
    }

    approval = {
        "schema_version": "1.0.0",
        "dataset_version": "0.0.0",  # REVIEW: set to the next dataset version at promotion.
        "approved_at": imported_at,
        "record_id": record_id,
        "telemetry_name": telemetry_name,
        "telemetry_class": telemetry_class,
        "observed_game_version": game_version,
        "observed_through": f"SimHub guided verification observation {observation_id}",
        "approved_controls": approved_controls,
        "confidence_notes": (
            "REVIEW-REQUIRED: confirm the derived controls against the observation "
            "and the curated record before approving."
        ),
        "scope_notes": "Single exact identity staged from one guided-verification drive.",
    }

    return {
        "importer": "guided-verification-observation",
        "importer_version": "0.1.0",
        "simulator": simulator,
        "observation_id": observation_id,
        "imported_at": imported_at,
        "review_required": True,
        "review_notes": review_notes,
        "record": record,
        "source": source,
        "approval": approval,
    }

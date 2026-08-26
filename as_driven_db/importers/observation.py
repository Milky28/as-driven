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


# The observation records only the primary actuation mechanism. A drive sees how
# the driver asks for a gear; it does not see how the gearbox is built, and the
# two are separate fields for that reason.
#
# Paddles used to derive `sequential`, which is a construction claim made from an
# actuation. The dataset says why that is wrong: of its paddle-shifted cars, 71
# are sequential but 17 are semi-automatic, 9 are dual-clutch and 2 are dog
# boxes. The first AC EVO drive of the Cayman GT4 Clubsport MR asserted
# `sequential` over a PDK that Porsche's own launch material calls a six-speed
# dual-clutch, and it was caught only because the record already held the right
# answer and the merge refused. On a new car it would have been curated.
#
# So the two sequentials now derive the gate they genuinely show and leave the
# construction alone, which is what H-pattern already did. `automatic-lever` and
# `direct-selection` keep theirs: those name the transmission, not just the
# control, and a lever marked P-R-N-D is not a way of operating something else.
_ACTUATION_DERIVATION = {
    "sequential-paddles": ("unknown", "sequential"),
    "sequential-stick": ("unknown", "sequential"),
    "automatic-lever": ("automatic", "automatic-gate"),
    "direct-selection": ("direct-drive", "direct"),
    "h-pattern": ("unknown", "unknown"),
    "unknown": ("unknown", "unknown"),
}


def _throttle_lift(tests: dict[str, Any], clean: bool) -> str:
    """Whether the upshift needed the driver to lift.

    The guided drive asks twice: once at sustained full throttle, and if that is
    refused, again after a lift. Which stage succeeded is the answer, and only
    the pair says it - an accepted lifted upshift on its own shows that lifting
    works, not that it was required, which is the same distinction the dataset
    draws between a blip that eases a synchromesh and one a dog box needs.
    """
    if not clean:
        return "unknown"
    first = tests.get("full_throttle_upshift")
    if first == "yes":
        return "not-required"
    if first == "no" and tests.get("clutchless_upshift") == "yes":
        return "required"
    return "unknown"


def _manual_blip(tests: dict[str, Any], automatic_blip: str, clean: bool) -> str:
    """Whether the real car needed the driver to blip.

    A car that blips for itself settles it: the driver does not have to. A car
    that accepts a downshift on a closed throttle settles it too.

    The refusing case deliberately does not become ``required``, and this is the
    one place the two-stage test stops short of an answer. ``required`` is
    reserved for a gearbox that needs the blip to engage, which is a fact about
    construction, and a simulator refusing an unblipped downshift is not that
    fact - it demands the blip on gearboxes established as synchromesh, both
    Formula Vee records and the Diablo among them. Every time the construction
    was later established for a car in this position the authentic value turned
    out to be ``optional`` and the simulator's demand moved to an override. So
    the demand is reported to the reviewer as a note instead of asserted here.
    See docs/data-model.md.
    """
    if automatic_blip == "yes":
        return "not-required"
    if not clean:
        return "unknown"
    if tests.get("coast_downshift") == "yes":
        return "not-required"
    return "unknown"


def _implementation_note(implementation: dict[str, Any] | None) -> str:
    """Name the installed package a drive was taken from, on the source itself.

    A live-observation source is that drive of that package, so this is where the
    fingerprint belongs once the bundle's review notes are gone. Without it a
    promoted record keeps no trace of which copy of a car it was drawn from, which
    is the whole reason the fingerprint is captured before the drive rather than
    when mods are supported.

    It identifies the package and nothing else. Which real car the package depicts
    is the reviewer's judgement, recorded in the record's identity; and a digest
    that differs from another package's is not evidence that the two behave
    differently.
    """
    if not implementation:
        return ""
    fingerprint = implementation.get("fingerprint") or {}
    author = implementation.get("author")
    version = implementation.get("declared_version")
    return (
        " Driven implementation: content id {id!r}{author}{version}, "
        "{scope} {algorithm} {digest}. This identifies the installed package, not "
        "the real car the record describes.".format(
            id=implementation.get("content_id"),
            author=f", by {author}" if author else "",
            version=(
                f", declared version {version}" if version else ", no declared version"
            ),
            scope=fingerprint.get("scope"),
            algorithm=fingerprint.get("algorithm"),
            digest=fingerprint.get("digest"),
        )
    )


def _slug(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.strip().casefold()).strip("-")
    return slug or "unknown"


def derive_approved_controls(
    record: dict[str, Any], simulator: str | None = None
) -> dict[str, Any]:
    """Summarize a curated record the way ``validate`` cross-checks approvals.

    Mirrors ``_validate_car_approval`` so a generated approval agrees with its
    record. ``running_shift_clutch`` is omitted when the upshift and downshift
    clutch requirements differ, because one value cannot summarize them.

    ``simulator`` names the entry being approved. A staged bundle carries one
    entry and does not need it, but a record a second simulator has merged into
    carries several, and validate reads the behavior fields from the entry whose
    approval this is. Taking entry zero there summarised whichever simulator
    happened to be curated first.
    """
    transmission = record["authentic_controls"]["transmission"]
    entries = record["simulators"]
    entry = entries[0]
    if simulator is not None:
        entry = next(
            (item for item in entries if item.get("simulator") == simulator), entries[0]
        )
    behavior = entry["behavior"]
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

    # An approval states what was approved, so a field the drive did not settle
    # is left out rather than approved as "unknown". It matters on a merge: the
    # approval is cross-checked against the curated record, and a second
    # simulator that established less than the first would otherwise assert
    # "unknown" against a value the record already holds and fail validation for
    # having learned nothing rather than for being wrong. The six fields the
    # approval schema requires stay whatever they are.
    required = {
        "forward_gears",
        "shift_actuation",
        "standing_start_clutch",
        "automatic_cut",
        "automatic_blip",
        "wheel_rim_shape",
    }
    return {
        name: value
        for name, value in controls.items()
        if name in required or (value is not None and value != "unknown")
    }


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
    internal_id = identity.get("internal_id", "")
    assists = observation.get("assists", {})
    tests = observation["tests"]
    cockpit = observation["cockpit"]
    observed_at = observation["observed_at"]
    verified_at = observed_at[:10]  # date portion of the ISO date-time
    observation_id = observation["observation_id"]
    observer = observation.get("observer", "unknown")

    slug = _slug(telemetry_name)
    # A record is one real car with an entry per simulator, so its id names the
    # car and not the simulator that happened to cover it first. The source id
    # keeps its simulator prefix: that evidence really does belong to one drive
    # in one game.
    record_id = slug
    source_id = f"{simulator}.local-live-{slug}-controls.{game_version}"

    clean = _assists_clean(assists)
    review_notes: list[str] = []
    # The fingerprint says which installed package was driven. Nothing consumes
    # it yet - the implementation registry does not exist - but it must not be
    # dropped on the floor, because it cannot be recovered from a promoted record
    # afterwards. Surfaced to the reviewer until something reads it.
    implementation = observation.get("implementation")
    if implementation:
        fingerprint = implementation.get("fingerprint") or {}
        review_notes.append(
            "Driven implementation: content id {id!r}, {scope} digest {digest}{version}. "
            "It identifies the package, not the real car this record claims to be: that "
            "mapping is this review's judgement. It is also not evidence that another "
            "package with a different digest behaves differently.".format(
                id=implementation.get("content_id"),
                scope=fingerprint.get("scope"),
                digest=str(fingerprint.get("digest"))[:12] + "...",
                version=(
                    ", declared version %r" % implementation["declared_version"]
                    if implementation.get("declared_version")
                    else ", no declared version"
                ),
            )
        )
    if (clean
            and tests.get("coast_downshift") == "no"
            and tests.get("clutchless_downshift") == "yes"
            and _state(tests.get("automatic_blip")) != "yes"):
        review_notes.append(
            "The simulator refused a clutchless downshift until the driver blipped. That "
            "is a demand the simulator makes, not evidence that the gearbox needs the "
            "blip to engage, so the real-car manual_blip value stays unknown while the "
            "simulator demand is preserved as an override."
        )
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
    if simulator == "acc":
        # ACC does not publish engine torque through SimHub. Older clients could
        # call a brief throttle dip an automatic cut, but that dip may be TC,
        # driver input, or telemetry filtering and cannot identify an
        # ignition-side gearbox cut. Preserve the draft as evidence while
        # degrading this unsupported derived claim during staging.
        if cut_state != "unknown":
            review_notes.append(
                "ACC automatic-cut result was degraded to unknown: ACC publishes no "
                "engine-torque channel through SimHub, and throttle interruption alone "
                "cannot distinguish a gearbox cut from TC, driver input, or telemetry "
                "filtering."
            )
        cut_state = "unknown"

    rim = cockpit["wheel_rim"]
    # Drafts saved before the rim vocabulary was merged still carry the retired
    # values. They named a racing class rather than a rim, and all three
    # described the one control-panel form, so an old draft is migrated on the
    # way in rather than reintroducing a value no curated record may hold.
    RETIRED_RIM_SHAPES = {"gt-style": "gt-formula", "prototype": "gt-formula",
                          "formula": "gt-formula"}
    rim_shape = rim.get("shape", "unknown")
    rim_shape = RETIRED_RIM_SHAPES.get(rim_shape, rim_shape)
    rim_display = _state(rim.get("integrated_display"))
    rim_lights = _state(rim.get("shift_lights"))
    rim_open_top = _state(rim.get("open_top"))
    rim_source_label = "live-cockpit-observation"

    upshift = {
        "clutch": up_clutch,
        "throttle_lift": _throttle_lift(tests, clean),
        "automatic_cut": cut_state,
        "manual_blip": "not-applicable",
        "automatic_blip": "not-applicable",
    }
    downshift = {
        "clutch": down_clutch,
        "throttle_lift": "not-applicable",
        "automatic_cut": "not-applicable",
        "manual_blip": _manual_blip(tests, blip_state, clean),
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
    simulator_overrides: list[dict[str, Any]] = []
    if (clean
            and tests.get("coast_downshift") == "no"
            and tests.get("clutchless_downshift") == "yes"
            and blip_state != "yes"):
        simulator_overrides.append(
            {
                "path": "/authentic_controls/transmission/downshift/manual_blip",
                "value": "required",
                "condition": (
                    f"The guided observation {observation_id} refused the clutchless "
                    "coast downshift and accepted the repeated downshift after the "
                    f"driver manually blipped in simulator version {game_version}. "
                    "This establishes simulator behavior, not the real car's gearbox "
                    "construction or authentic blip requirement."
                ),
                "confidence": {
                    "level": "verified",
                    "basis": "The complete two-stage downshift test was observed live.",
                },
                "source_refs": [source_id],
            }
        )

    record = {
        "$schema": "../../../schema/v1/car-record.schema.json",
        "schema_version": "1.0.0",
        "record_id": record_id,
        "identity": {
            "display_name": telemetry_name,
            "manufacturer": REVIEW,
            "model": REVIEW,
            "year": {"label": REVIEW},
            # The simulator's own class token, a placeholder only: the review
            # manifest must replace it with the real category. Promotion
            # refuses without one, so this never reaches a curated record.
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
                # Not every simulator groups its cars. Assetto Corsa EVO reports
                # no class, which reaches here as the literal string "unknown" -
                # minting a class-id identity from that would put the word into
                # the match index as though a car were called it.
                "identities": (
                    [{"kind": "telemetry-name", "value": telemetry_name}]
                    + (
                        [{"kind": "internal-id", "value": internal_id}]
                        if internal_id
                        else []
                    )
                    + (
                        [{"kind": "class-id", "value": telemetry_class}]
                        if telemetry_class and telemetry_class != "unknown"
                        else []
                    )
                ),
                "behavior": behavior,
                "overrides": simulator_overrides,
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
            + _implementation_note(observation.get("implementation"))
        ),
    }
    if observation.get("implementation"):
        # Structured, not prose. A reviewer rewriting the note cannot lose it,
        # and the implementation registry can read it without parsing English.
        declared = observation["implementation"]
        source["implementation"] = {
            "content_id": declared["content_id"],
            "author": declared.get("author"),
            "declared_version": declared.get("declared_version"),
            "fingerprint": dict(declared["fingerprint"]),
        }

    approval = {
        "schema_version": "1.0.0",
        "dataset_version": "0.0.0",  # REVIEW: set to the next dataset version at promotion.
        "approved_at": imported_at,
        "record_id": record_id,
        # Which simulator's evidence this approves. The record id no longer
        # carries it, and a car may be approved once per simulator.
        "simulator": simulator,
        "telemetry_name": telemetry_name,
        "observed_game_version": game_version,
        "observed_through": f"SimHub guided verification observation {observation_id}",
        "approved_controls": approved_controls,
        "confidence_notes": (
            "REVIEW-REQUIRED: confirm the derived controls against the observation "
            "and the curated record before approving."
        ),
        "scope_notes": "Single exact identity staged from one guided-verification drive.",
    }
    # Only when the simulator actually groups its cars. Assetto Corsa EVO does
    # not, and approving the literal word "unknown" as a class would assert an
    # identity no record carries.
    if telemetry_class and telemetry_class != "unknown":
        approval["telemetry_class"] = telemetry_class

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

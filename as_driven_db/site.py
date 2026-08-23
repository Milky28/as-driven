"""Render the curated database as one self-contained page.

The dataset is the product, and until now the only way to read it was to install
a SimHub plugin or open the JSON. This builds a page anyone can open: every
curated car, what to fit, what to do, how each reviewed simulator relates to the
real car, and - just as plainly - what is not established yet.

The wording mirrors AsDriven.Core.PreflightLabels so the page and the in-sim
card say the same thing. The tone a value carries is the same question the card
asks: is this the driver's job. It has four answers, and `unknown` is not a quiet
`no`; the page gives it its own treatment so a gap in the evidence can never read
as a car that handles it.
"""
from __future__ import annotations

import html
import json
from pathlib import Path
from typing import Any

TONE_DRIVER = "you"
TONE_CAR = "car"
TONE_OPTIONAL = "optional"
TONE_UNKNOWN = "unknown"

TONE_TITLE = {
    TONE_DRIVER: "You do this",
    TONE_CAR: "The car does this",
    TONE_OPTIONAL: "Your choice",
    TONE_UNKNOWN: "Not established by the evidence",
}

ACTUATION = {
    "h-pattern": "H-pattern",
    "sequential-stick": "sequential",
    "sequential-paddles": "paddles",
    "automatic-lever": "automatic",
    "direct-selection": "direct select",
}

RIM = {
    "round": "Round rim",
    "d-shaped": "D-shaped rim",
    "gt-formula": "GT / Formula rim",
    "gt-style": "GT / Formula rim",
    "prototype": "GT / Formula rim",
    "formula": "GT / Formula rim",
    "yoke": "Yoke",
    "other": "Other rim",
}

SIMULATOR_LABELS = {
    "ams2": "AMS2",
    "ac": "Assetto Corsa",
    "acc": "Assetto Corsa Competizione",
    "ac-evo": "Assetto Corsa EVO",
    "ac-rally": "Assetto Corsa Rally",
    "iracing": "iRacing",
}

SIMULATOR_BEHAVIOR_FIELDS = {
    "/shift_type": "shift type",
    "/auto_blip": "automatic blip",
    "/shift_cut": "automatic shift cut",
    "/wheel_rim_type/normalized": "wheel-rim category",
    "/wheel_rim_type/integrated_display": "integrated wheel display",
    "/wheel_rim_type/shift_lights": "wheel shift lights",
    "/wheel_rim_type/open_top": "open-top wheel construction",
    "/wheel_rim_type/source_label": "wheel-rim source label",
}

# Simulator behavior and authentic controls use deliberately separate schemas:
# the former records what a game did, while the latter tells the driver what the
# real car requires. For a cross-simulator comparison these paths are the same
# user-facing question. An explicit simulator `unknown` replaces the authentic
# baseline here, because a gap in one game is not evidence that it agrees.
BEHAVIOR_COMPARISON_PATHS = {
    "/shift_type": "/authentic_controls/transmission/shift_actuation",
    "/auto_blip": "/authentic_controls/transmission/downshift/automatic_blip",
    "/shift_cut": "/authentic_controls/transmission/upshift/automatic_cut",
    "/wheel_rim_type/normalized": "/authentic_controls/steering/wheel_rim/shape",
    "/wheel_rim_type/integrated_display": "/authentic_controls/steering/wheel_rim/integrated_display",
    "/wheel_rim_type/shift_lights": "/authentic_controls/steering/wheel_rim/shift_lights",
    "/wheel_rim_type/open_top": "/authentic_controls/steering/wheel_rim/open_top",
}

COMPARISON_PATHS = (
    "/authentic_controls/transmission/forward_gears",
    "/authentic_controls/transmission/gearbox_type",
    "/authentic_controls/transmission/shift_actuation",
    "/authentic_controls/transmission/shift_pattern",
    "/authentic_controls/transmission/first_gear_position",
    "/authentic_controls/transmission/standing_start_clutch",
    "/authentic_controls/transmission/upshift/clutch",
    "/authentic_controls/transmission/upshift/throttle_lift",
    "/authentic_controls/transmission/upshift/automatic_cut",
    "/authentic_controls/transmission/downshift/clutch",
    "/authentic_controls/transmission/downshift/manual_blip",
    "/authentic_controls/transmission/downshift/automatic_blip",
    "/authentic_controls/steering/wheel_rim/shape",
    "/authentic_controls/steering/wheel_rim/integrated_display",
    "/authentic_controls/steering/wheel_rim/shift_lights",
    "/authentic_controls/steering/wheel_rim/open_top",
)

COMPARISON_LABELS = {
    "/authentic_controls/transmission/forward_gears": "Forward gears",
    "/authentic_controls/transmission/gearbox_type": "Gearbox construction",
    "/authentic_controls/transmission/shift_actuation": "Shifter",
    "/authentic_controls/transmission/shift_pattern": "Gate pattern",
    "/authentic_controls/transmission/first_gear_position": "First gear position",
    "/authentic_controls/transmission/standing_start_clutch": "Pulling away",
    "/authentic_controls/transmission/upshift/clutch": "Clutch on an upshift",
    "/authentic_controls/transmission/upshift/throttle_lift": "Upshift throttle",
    "/authentic_controls/transmission/upshift/automatic_cut": "Automatic shift cut",
    "/authentic_controls/transmission/downshift/clutch": "Clutch on a downshift",
    "/authentic_controls/transmission/downshift/manual_blip": "Manual blip",
    "/authentic_controls/transmission/downshift/automatic_blip": "Automatic blip",
    "/authentic_controls/steering/wheel_rim/shape": "Wheel-rim category",
    "/authentic_controls/steering/wheel_rim/integrated_display": "Integrated wheel display",
    "/authentic_controls/steering/wheel_rim/shift_lights": "Wheel shift lights",
    "/authentic_controls/steering/wheel_rim/open_top": "Open-top wheel",
}


def simulator_label(simulator: str) -> str:
    return SIMULATOR_LABELS.get(simulator, simulator.upper())


def wheel_equipment(integrated_display: str, shift_lights: str) -> str:
    display = {
        "yes": "Display",
        "no": "No display",
        "not-applicable": "Display not applicable",
    }.get(integrated_display, "Display not established")
    lights = {
        "yes": "Shift lights",
        "no": "No shift lights",
        "not-applicable": "Shift lights not applicable",
    }.get(shift_lights, "Lights not established")
    return f"{display} · {lights}"


def shifter(gears: Any, actuation: str) -> str:
    label = ACTUATION.get(actuation)
    if label is None:
        return "Shifter not recorded"
    return f"{gears}-speed {label}" if isinstance(gears, int) and gears > 0 else label


def gate(actuation: str, pattern: str, first_gear: str | None) -> str:
    if pattern == "dogleg-h":
        if first_gear == "down-left":
            return "Dogleg gate, 1st down and left"
        if first_gear == "down-right":
            return "Dogleg gate, 1st down and right"
        return "Dogleg gate, 1st outside the plane"
    if pattern == "standard-h":
        if first_gear == "up-right":
            return "Standard gate, 1st up and right"
        if first_gear == "down-left":
            return "Standard gate, 1st down and left"
        return "Standard gate, 1st up and left"
    if actuation == "sequential-paddles":
        return "Sequential, one gear at a time"
    if actuation == "sequential-stick":
        return "Fore and aft, one gear at a time"
    if pattern == "sequential":
        return "Sequential, one gear at a time"
    if pattern == "automatic-gate":
        return "Automatic gate"
    if pattern == "direct":
        return "Direct selection"
    return "Gate not recorded"


def launch(value: str) -> tuple[str, str]:
    return {
        "required": ("Clutch required", TONE_DRIVER),
        "not-required": ("No clutch needed", TONE_CAR),
        "anti-stall-available": ("Anti-stall fitted", TONE_CAR),
        "not-applicable": ("No clutch fitted", TONE_CAR),
    }.get(value, ("Not established", TONE_UNKNOWN))


def upshift(lift: str, cut: str, clutch: str) -> tuple[str, str]:
    if lift == "required":
        text = "Lift the throttle"
    elif lift == "partial":
        text = "Part lift"
    elif lift == "not-required":
        text = "Stay flat, car cuts" if cut == "yes" else "Stay flat"
    elif lift == "not-applicable":
        text = "Nothing to do"
    else:
        return "Not established", TONE_UNKNOWN
    if clutch == "required":
        return text, TONE_DRIVER
    return text, TONE_DRIVER if lift in {"required", "partial"} else TONE_CAR


def downshift(manual: str, automatic: str, clutch: str) -> tuple[str, str]:
    if manual == "required":
        return "Blip to rev-match", TONE_DRIVER
    if manual == "optional":
        return "Blip optional", TONE_OPTIONAL
    if manual == "not-required":
        text = "Car blips for you" if automatic == "yes" else "No blip needed"
        return text, TONE_DRIVER if clutch == "required" else TONE_CAR
    if manual == "not-applicable":
        return "Nothing to do", TONE_CAR
    return "Not established", TONE_UNKNOWN


def running_clutch(value: str) -> str:
    """Whether the clutch is wanted for a shift already under way."""
    return {
        "required": "Clutch required",
        "optional": "Clutch optional",
        "not-required": "No clutch needed",
        "not-applicable": "No clutch fitted",
    }.get(value, "Clutch not established")


# How to describe each field a simulator is known to override. The renderer is
# given a whole transmission block so it can answer in the page's own words
# rather than echoing a raw enum, and so a field that reads differently
# depending on its neighbours - a blip depends on whether anything blips - still
# reads correctly.
DIFFERENCE_FIELDS = {
    "/forward_gears": (
        "Gears",
        lambda t: shifter(t["forward_gears"], t["shift_actuation"]),
    ),
    "/standing_start_clutch": (
        "Pulling away",
        lambda t: launch(t["standing_start_clutch"])[0],
    ),
    "/upshift/throttle_lift": (
        "Upshift",
        lambda t: upshift(
            t["upshift"]["throttle_lift"], t["upshift"]["automatic_cut"],
            t["upshift"]["clutch"],
        )[0],
    ),
    "/upshift/clutch": ("Clutch on an upshift", lambda t: running_clutch(t["upshift"]["clutch"])),
    "/downshift/manual_blip": (
        "Downshift",
        lambda t: downshift(
            t["downshift"]["manual_blip"], t["downshift"]["automatic_blip"],
            t["downshift"]["clutch"],
        )[0],
    ),
    "/downshift/clutch": (
        "Clutch on a downshift",
        lambda t: running_clutch(t["downshift"]["clutch"]),
    ),
}
TRANSMISSION_PREFIX = "/authentic_controls/transmission"
RUNNING_CLUTCH_PATHS = {
    "/authentic_controls/transmission/upshift/clutch",
    "/authentic_controls/transmission/downshift/clutch",
}


def _control_field_label(path: str) -> str:
    relative = path
    if relative.startswith(TRANSMISSION_PREFIX):
        relative = relative[len(TRANSMISSION_PREFIX):]
    parts = [part.replace("_", " ") for part in relative.split("/") if part]
    if len(parts) > 1 and parts[0] in {"upshift", "downshift"}:
        return f"{parts[0]} {parts[-1]}"
    return parts[-1] if parts else path.strip("/").replace("_", " ")


def _open_control_fields(transmission: dict[str, Any]) -> list[str]:
    paths = {
        path for path, value in _flatten(transmission).items()
        if value == "unknown"
    }
    local_clutch_paths = {path[len(TRANSMISSION_PREFIX):] for path in RUNNING_CLUTCH_PATHS}
    labels = {
        _control_field_label(path)
        for path in paths
        if path not in local_clutch_paths
    }
    if local_clutch_paths.issubset(paths):
        labels.add("running-shift clutch")
    else:
        labels.update(_control_field_label(path) for path in paths & local_clutch_paths)
    return sorted(labels)


def _archetype_deviations(items: list[dict[str, Any]]) -> list[dict[str, str]]:
    by_path = {item.get("path", ""): item for item in items}
    combine_running_clutch = RUNNING_CLUTCH_PATHS.issubset(by_path)
    combined_basis = ""
    if combine_running_clutch:
        bases = {
            by_path[path].get("basis", "")
            .replace("running upshifts", "running shifts")
            .replace("running downshifts", "running shifts")
            for path in RUNNING_CLUTCH_PATHS
        }
        combine_running_clutch = len(bases) == 1
        if combine_running_clutch:
            combined_basis = bases.pop()

    result = []
    running_clutch_written = False
    for item in items:
        path = item.get("path", "")
        if combine_running_clutch and path in RUNNING_CLUTCH_PATHS:
            if not running_clutch_written:
                result.append({"field": "running-shift clutch", "why": combined_basis})
                running_clutch_written = True
            continue
        result.append({"field": _control_field_label(path), "why": item.get("basis", "")})
    return result


def _apply(transmission: dict[str, Any], overrides: list[dict[str, Any]]) -> dict[str, Any]:
    effective = json.loads(json.dumps(transmission))
    for override in overrides:
        path = override.get("path", "")
        if not path.startswith(TRANSMISSION_PREFIX):
            continue
        parts = [part for part in path[len(TRANSMISSION_PREFIX):].split("/") if part]
        node = effective
        for part in parts[:-1]:
            node = node.get(part, {})
        if parts:
            node[parts[-1]] = override["value"]
    return effective


def _apply_controls(
    controls: dict[str, Any], overrides: list[dict[str, Any]]
) -> dict[str, Any]:
    """Return one simulator's effective controls without changing the record."""
    effective = json.loads(json.dumps(controls))
    prefix = "/authentic_controls"
    for override in overrides:
        path = override.get("path", "")
        if not path.startswith(prefix):
            continue
        parts = [part for part in path[len(prefix):].split("/") if part]
        node = effective
        for part in parts[:-1]:
            node = node.get(part, {})
        if parts:
            node[parts[-1]] = override["value"]
    return effective


def _comparison_value(path: str, value: Any) -> str:
    if value in {None, "unknown"}:
        return "Not established"
    if path.endswith("/standing_start_clutch"):
        return launch(str(value))[0]
    if path.endswith("/shift_actuation"):
        return ACTUATION.get(str(value), str(value).replace("-", " ").title())
    if path.endswith("/shape"):
        return RIM.get(str(value), str(value).replace("-", " ").title())
    yes_no = {
        "yes": "Yes",
        "no": "No",
        "required": "Required",
        "not-required": "Not required",
        "optional": "Optional",
        "not-applicable": "Not applicable",
        "partial": "Partial lift",
    }
    return yes_no.get(value, str(value).replace("-", " ").title())


def simulator_disagreements(
    controls: dict[str, Any], entries: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    """Established values on which two reviewed simulator views conflict.

    `unknown` is retained for display but excluded from the decision. One game
    knowing less than another is an evidence gap, not a disagreement.
    """
    views: list[tuple[str, dict[str, Any]]] = []
    for entry in entries:
        effective = _apply_controls(controls, entry.get("overrides") or [])
        flat = {
            f"/authentic_controls{path}": value
            for path, value in _flatten(effective).items()
        }
        behavior = _flatten(entry.get("behavior") or {})
        for behavior_path, control_path in BEHAVIOR_COMPARISON_PATHS.items():
            if behavior_path in behavior:
                flat[control_path] = behavior[behavior_path]
        views.append((simulator_label(entry.get("simulator", "")), flat))

    disagreements = []
    for path in COMPARISON_PATHS:
        values = [flat.get(path, "unknown") for _, flat in views]
        established = {
            json.dumps(value, sort_keys=True)
            for value in values
            if value not in {None, "unknown"}
        }
        if len(established) < 2:
            continue
        disagreements.append(
            {
                "path": path,
                "field": COMPARISON_LABELS[path],
                "values": [
                    {
                        "simulator": label,
                        "value": _comparison_value(path, flat.get(path, "unknown")),
                    }
                    for label, flat in views
                ],
            }
        )
    return disagreements


def differences(transmission: dict[str, Any], overrides: list[dict[str, Any]]) -> list[dict[str, str]]:
    """What the simulator does differently, in the same words as the card.

    An override is the record saying the two layers genuinely disagree, so the
    page shows both rather than silently preferring one. The real car's value is
    what the table above states; this is the departure from it.
    """
    if not overrides:
        return []
    effective = _apply(transmission, overrides)
    out = []
    for override in overrides:
        path = override.get("path", "")
        field = path[len(TRANSMISSION_PREFIX):] if path.startswith(TRANSMISSION_PREFIX) else path
        name, render = DIFFERENCE_FIELDS.get(
            field, (field.strip("/").replace("/", " ").replace("_", " "), None)
        )
        if render is None:
            real, sim = "", str(override["value"])
        else:
            real, sim = render(transmission), render(effective)
        out.append({"name": name, "real": real, "sim": sim, "why": override.get("condition", "")})
    return out


def _simulator_view(
    record_id: str,
    entry: dict[str, Any],
    transmission: dict[str, Any],
) -> dict[str, Any]:
    simulator = entry.get("simulator", "")
    confidence = entry.get("confidence") or {}
    behavior = entry.get("behavior") or {}
    unknown_behavior = sorted(
        SIMULATOR_BEHAVIOR_FIELDS.get(
            path,
            path.rsplit("/", 1)[-1].replace("_", " "),
        )
        for path, value in _flatten(behavior).items()
        if value == "unknown"
    )
    return {
        "id": simulator,
        "label": simulator_label(simulator),
        "anchor": f"{record_id}--{simulator}",
        "differences": differences(transmission, entry.get("overrides") or []),
        "unknown_behavior": unknown_behavior,
        "game_version": entry.get("verified_game_version", ""),
        "verified_at": entry.get("verified_at", ""),
        "confidence": confidence.get("level", ""),
    }


def _car(record: dict[str, Any], archetypes: dict[str, str]) -> dict[str, Any]:
    identity = record["identity"]
    controls = record["authentic_controls"]
    transmission = controls["transmission"]
    rim = controls["steering"]["wheel_rim"]
    launch_text, launch_tone = launch(transmission["standing_start_clutch"])
    up_text, up_tone = upshift(
        transmission["upshift"]["throttle_lift"],
        transmission["upshift"]["automatic_cut"],
        transmission["upshift"]["clutch"],
    )
    down_text, down_tone = downshift(
        transmission["downshift"]["manual_blip"],
        transmission["downshift"]["automatic_blip"],
        transmission["downshift"]["clutch"],
    )
    simulator_entries = record.get("simulators") or []
    simulator_views = [
        _simulator_view(record["record_id"], entry, transmission)
        for entry in simulator_entries
    ]
    cross_simulator_disagreements = simulator_disagreements(
        controls, simulator_entries
    )
    block = record.get("archetype") or {}
    classification = block.get("classification")
    mechanism = archetypes.get(block.get("archetype_id", ""), "")

    open_fields = _open_control_fields(transmission)
    deviations = _archetype_deviations(block.get("deviations", []))
    explained_open_fields = {item["field"] for item in deviations}
    return {
        "id": record["record_id"],
        "name": identity["display_name"],
        "car_class": identity.get("class", ""),
        "year": identity.get("year", {}).get("label", ""),
        "shifter": shifter(transmission["forward_gears"], transmission["shift_actuation"]),
        "gate": gate(
            transmission["shift_actuation"],
            transmission["shift_pattern"],
            transmission.get("first_gear_position"),
        ),
        "launch": [launch_text, launch_tone],
        "up": [up_text, up_tone],
        "down": [down_text, down_tone],
        "rim": RIM.get(rim.get("shape", ""), "Rim not recorded"),
        "wheel_equipment": wheel_equipment(
            rim.get("integrated_display", "unknown"),
            rim.get("shift_lights", "unknown"),
        ),
        "summary": record.get("driver_summary", ""),
        "classification": classification,
        "mechanism": mechanism,
        "deviations": deviations,
        "archetype_basis": block.get("basis", ""),
        "open_fields": open_fields,
        "unexplained_open_fields": [
            field for field in open_fields if field not in explained_open_fields
        ],
        "simulators": simulator_views,
        "has_differences": any(view["differences"] for view in simulator_views),
        "is_multi_sim": len(simulator_views) > 1,
        "simulator_disagreements": cross_simulator_disagreements,
        "has_simulator_disagreements": bool(cross_simulator_disagreements),
        "actuation": transmission["shift_actuation"],
        "start": transmission["standing_start_clutch"],
        "blip": transmission["downshift"]["manual_blip"],
    }


def _flatten(node: Any, prefix: str = "") -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in node.items():
        path = f"{prefix}/{key}"
        if isinstance(value, dict):
            flat.update(_flatten(value, path))
        else:
            flat[path] = value
    return flat


def collect(root: Path) -> dict[str, Any]:
    data = root / "data" / "v1"
    index = json.loads((data / "index.json").read_text(encoding="utf-8"))
    archetypes: dict[str, str] = {}
    archetype_path = data / "archetypes.json"
    if archetype_path.exists():
        for entry in json.loads(archetype_path.read_text(encoding="utf-8"))["archetypes"]:
            archetypes[entry["archetype_id"]] = entry["label"]
    cars = [
        _car(json.loads((data / relative).read_text(encoding="utf-8")), archetypes)
        for relative in index["records"]
    ]
    cars.sort(key=lambda car: (car["name"].lower(), car["car_class"].lower()))
    simulators = {
        view["id"]: view["label"]
        for car in cars
        for view in car["simulators"]
    }
    return {
        "version": index["dataset_version"],
        "released_at": index["released_at"],
        "cars": cars,
        "simulators": [
            {"id": simulator, "label": label}
            for simulator, label in sorted(
                simulators.items(), key=lambda item: item[1].lower()
            )
        ],
    }


def _e(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _cell(value: list[str]) -> str:
    text, tone = value
    return (
        f'<td class="state"><span class="tone tone-{tone}" '
        f'title="{_e(TONE_TITLE[tone])}">{_e(text)}</span></td>'
    )


def _simulator_panel(car: dict[str, Any], simulator: dict[str, Any], selected: bool) -> str:
    content = [
        '<h3 class="sim-panel-title">{car}<span>{simulator}</span></h3>'.format(
            car=_e(car["name"]), simulator=_e(simulator["label"])
        )
    ]
    if simulator["differences"]:
        rows = "".join(
            '<li><span class="field">{name}</span>'
            '<span class="was">{real}</span>'
            '<span class="arrow" aria-hidden="true">→</span>'
            '<span class="now">{sim}</span>'
            '<p class="why">{why}</p></li>'.format(
                name=_e(item["name"]),
                real=_e(item["real"]),
                sim=_e(item["sim"]),
                why=_e(item["why"]),
            )
            for item in simulator["differences"]
        )
        content.append(
            '<div class="block"><h4>{sim} does it differently</h4>'
            '<ul class="differs">{rows}</ul></div>'.format(
                sim=_e(simulator["label"]), rows=rows
            )
        )
    else:
        content.append(
            '<div class="block sim-relationship"><h4>Relationship to the real car</h4>'
            '<p>No reviewed difference from the real car is recorded for this simulator.</p>'
            '</div>'
        )

    if simulator["unknown_behavior"]:
        chips = "".join(
            f'<span class="chip">{_e(field)}</span>'
            for field in simulator["unknown_behavior"]
        )
        content.append(
            '<div class="block"><h4>Simulator behavior not established</h4>'
            f'<div class="chips">{chips}</div></div>'
        )

    provenance = " · ".join(
        part
        for part in (
            simulator["label"],
            simulator["game_version"],
            f'verified {simulator["verified_at"]}' if simulator["verified_at"] else "",
            f'confidence {simulator["confidence"]}' if simulator["confidence"] else "",
        )
        if part
    )
    content.append(f'<p class="provenance">{_e(provenance)}</p>')
    content.append(
        '<a class="permalink" href="#{anchor}" '
        'aria-label="Link to {car} in {sim}">Link to this simulator view</a>'.format(
            anchor=_e(simulator["anchor"]),
            car=_e(car["name"]),
            sim=_e(simulator["label"]),
        )
    )
    hidden = "" if selected else " hidden"
    return (
        '<div class="sim-panel" id="{anchor}-panel" role="tabpanel" '
        'aria-labelledby="{anchor}-tab" data-simulator-panel="{simulator}"{hidden}>'
        '{content}</div>'.format(
            anchor=_e(simulator["anchor"]),
            simulator=_e(simulator["id"]),
            hidden=hidden,
            content="".join(content),
        )
    )


def _row(car: dict[str, Any]) -> str:
    detail = []
    if car["summary"]:
        detail.append(f'<p class="summary">{_e(car["summary"])}</p>')

    if car["mechanism"]:
        heading = "Mechanism" if car["classification"] == "matches" else "Based on"
        detail.append(
            f'<div class="block"><h4>{heading}</h4><p>{_e(car["mechanism"])}</p></div>'
        )
    if car["deviations"]:
        items = "".join(
            f'<li><span class="field">{_e(item["field"])}</span>{_e(item["why"])}</li>'
            for item in car["deviations"]
        )
        detail.append(f'<div class="block"><h4>Departs from it</h4><ul>{items}</ul></div>')
    if car["classification"] in {"undetermined", "no-archetype"} and car["archetype_basis"]:
        heading = (
            "Not yet classified" if car["classification"] == "undetermined" else "Its own mechanism"
        )
        detail.append(
            f'<div class="block"><h4>{heading}</h4><p>{_e(car["archetype_basis"])}</p></div>'
        )
    if car["unexplained_open_fields"]:
        chips = "".join(
            f'<span class="chip">{_e(field)}</span>'
            for field in car["unexplained_open_fields"]
        )
        detail.append(
            '<div class="block"><h4>Not established</h4>'
            f'<div class="chips">{chips}</div></div>'
        )
    if car["simulator_disagreements"]:
        items = "".join(
            '<li><span class="field">{field}</span><span class="comparison-values">'
            '{values}</span></li>'.format(
                field=_e(item["field"]),
                values="".join(
                    '<span><b>{simulator}</b> {value}</span>'.format(
                        simulator=_e(value["simulator"]),
                        value=_e(value["value"]),
                    )
                    for value in item["values"]
                ),
            )
            for item in car["simulator_disagreements"]
        )
        detail.append(
            '<div class="block simulator-comparison"><h4>Simulators disagree</h4>'
            '<p>Only conflicting established values count; unknowns are shown as gaps.</p>'
            f'<ul>{items}</ul></div>'
        )
    tabs = "".join(
        '<a class="sim-tab" id="{anchor}-tab" href="#{anchor}" role="tab" '
        'aria-controls="{anchor}-panel" aria-selected="{selected}" tabindex="{tabindex}" '
        'data-simulator-tab="{simulator}">{label}</a>'.format(
            anchor=_e(simulator["anchor"]),
            simulator=_e(simulator["id"]),
            label=_e(simulator["label"]),
            selected="true" if index == 0 else "false",
            tabindex="0" if index == 0 else "-1",
        )
        for index, simulator in enumerate(car["simulators"])
    )
    panels = "".join(
        _simulator_panel(car, simulator, index == 0)
        for index, simulator in enumerate(car["simulators"])
    )
    detail.append(
        '<section class="simulator-section" aria-label="Simulator views">'
        '<div class="simulator-heading"><h4>Simulator view</h4>'
        '<span>Choose a reviewed simulator; each view has a shareable link.</span></div>'
        '<div class="sim-tabs" role="tablist" aria-label="Reviewed simulators for {car}">'
        '{tabs}</div>{panels}</section>'.format(
            car=_e(car["name"]), tabs=tabs, panels=panels
        )
    )

    search = " ".join(
        [
            car["name"], car["car_class"], car["shifter"], car["gate"], car["year"],
            car["wheel_equipment"],
            *(simulator["label"] for simulator in car["simulators"]),
        ]
    ).lower()
    simulator_ids = " " + " ".join(view["id"] for view in car["simulators"]) + " "
    simulator_count = (
        '<span class="sim-count">{count} simulators</span>'.format(
            count=len(car["simulators"])
        )
        if len(car["simulators"]) > 1
        else ""
    )
    simulator_anchors = "".join(
        '<span class="sim-anchor" id="{anchor}" '
        'data-simulator-anchor-target="{simulator}" aria-hidden="true"></span>'.format(
            anchor=_e(simulator["anchor"]), simulator=_e(simulator["id"])
        )
        for simulator in car["simulators"]
    )
    return (
        f'<tr class="car" id="car-{_e(car["id"])}" data-search="{_e(search)}" '
        f'data-simulators="{_e(simulator_ids)}" data-actuation="{_e(car["actuation"])}" '
        f'data-start="{_e(car["start"])}" data-blip="{_e(car["blip"])}" '
        f'data-multi-sim="{str(car["is_multi_sim"]).lower()}" '
        f'data-sim-disagreement="{str(car["has_simulator_disagreements"]).lower()}" tabindex="0" '
        f'aria-expanded="false" aria-controls="details-{_e(car["id"])}">'
        f'<td class="car-name">{simulator_anchors}'
        f'<span class="name">{_e(car["name"])}</span>'
        f'<span class="meta">{_e(car["car_class"])}</span>'
        + simulator_count
        + (
            '<span class="differs-flag" title="A reviewed simulator does something '
            'differently from the real car">differs from car</span>'
            if car["has_differences"]
            else ""
        )
        + (
            '<span class="disagrees-flag" title="Two reviewed simulators establish '
            'different values">sims disagree</span>'
            if car["has_simulator_disagreements"]
            else ""
        )
        + "</td>"
        f'<td class="spec"><span class="shifter">{_e(car["shifter"])}</span>'
        f'<span class="meta">{_e(car["gate"])}</span></td>'
        f"{_cell(car['launch'])}{_cell(car['up'])}{_cell(car['down'])}"
        f'<td class="rim">{_e(car["rim"])}'
        f'<span class="meta">{_e(car["wheel_equipment"])}</span></td>'
        "</tr>"
        f'<tr class="detail" hidden><td colspan="6"><div class="detail-inner">'
        f'<div id="details-{_e(car["id"])}">{"".join(detail)}</div></div></td></tr>'
    )


def render(payload: dict[str, Any]) -> str:
    cars = payload["cars"]
    clutch_start = sum(1 for car in cars if car["start"] == "required")
    you_blip = sum(1 for car in cars if car["blip"] == "required")
    open_any = sum(1 for car in cars if car["open_fields"])
    disagreeing = sum(1 for car in cars if car["has_simulator_disagreements"])
    simulator_entries = sum(len(car["simulators"]) for car in cars)
    simulator_options = "".join(
        '<option value="{id}">{label}</option>'.format(
            id=_e(simulator["id"]), label=_e(simulator["label"])
        )
        for simulator in payload["simulators"]
    )
    rows = "\n".join(_row(car) for car in cars)
    page = TEMPLATE.format(
        version=_e(payload["version"]),
        released=_e(payload["released_at"]),
        total=len(cars),
        clutch_start=clutch_start,
        you_blip=you_blip,
        open_any=open_any,
        disagreeing=disagreeing,
        simulator_count=len(payload["simulators"]),
        simulator_entries=simulator_entries,
        simulator_options=simulator_options,
        rows=rows,
    )
    # The page owns no <head>, so it cannot declare a charset. Emitting numeric
    # references keeps a name like "Fórmula Inter MG15" or a separator correct
    # whatever encoding the host assumes.
    return page.encode("ascii", "xmlcharrefreplace").decode("ascii")


def build_site(root: Path) -> str:
    return render(collect(root))


TEMPLATE = """<title>As Driven Controls</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Archivo:wght@600;700&family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600&display=swap">
<style>
:root {{
  --bg: #f0f2f5;
  --surface: #ffffff;
  --surface-2: #e3e7ed;
  --ink: #16181d;
  --muted: #3f4652;
  --faint: #535c6a;
  --line: #cbd1da;
  --accent: #c2610a;
  --driver: #a8520a;
  --driver-bg: #fbeedd;
  --car: #2e6b5e;
  --car-bg: #e4efec;
  --optional: #6b5aa6;
  --focus: #1f5fa8;
}}
@media (prefers-color-scheme: dark) {{
  :root:not([data-theme="light"]) {{
    --bg: #0f1115;
    --surface: #171a20;
    --surface-2: #1e222a;
    --ink: #e8eaee;
    --muted: #a2a9b6;
    --faint: #8d95a3;
    --line: #272b33;
    --accent: #f0a03c;
    --driver: #f0a03c;
    --driver-bg: #33240f;
    --car: #5bb39b;
    --car-bg: #122b26;
    --optional: #a893e0;
    --focus: #6fa8e8;
  }}
}}
:root[data-theme="dark"] {{
  --bg: #0f1115;
  --surface: #171a20;
  --surface-2: #1e222a;
  --ink: #e8eaee;
  --muted: #a2a9b6;
  --faint: #8d95a3;
  --line: #272b33;
  --accent: #f0a03c;
  --driver: #f0a03c;
  --driver-bg: #33240f;
  --car: #5bb39b;
  --car-bg: #122b26;
  --optional: #a893e0;
  --focus: #6fa8e8;
}}
* {{ box-sizing: border-box; }}
body {{
  margin: 0;
  background: var(--bg);
  color: var(--ink);
  font-family: "IBM Plex Sans", ui-sans-serif, system-ui, sans-serif;
  font-size: 15px;
  line-height: 1.5;
  -webkit-font-smoothing: antialiased;
}}
.wrap {{ max-width: 1180px; margin: 0 auto; padding: 40px 24px 80px; }}
header {{ display: flex; flex-direction: column; gap: 12px; margin-bottom: 32px; }}
header .provenance {{ margin-top: -4px; }}
.topline {{
  display: flex; flex-wrap: wrap; gap: 16px;
  align-items: baseline; justify-content: space-between;
}}
.theme {{ display: flex; border: 1px solid var(--line); border-radius: 3px; overflow: hidden; }}
.theme button {{
  padding: 6px 11px; margin: 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11.5px; color: var(--muted);
  background: var(--surface); border: 0; cursor: pointer;
}}
.theme button + button {{ border-left: 1px solid var(--line); }}
.theme button:hover {{ color: var(--ink); }}
.theme button[aria-pressed="true"] {{ background: var(--surface-2); color: var(--ink); }}
h1 {{
  font-family: Archivo, ui-sans-serif, system-ui, sans-serif;
  font-weight: 700;
  font-size: clamp(30px, 5vw, 42px);
  letter-spacing: -0.02em;
  margin: 0;
  text-wrap: balance;
}}
.lede {{ margin: 0; max-width: 62ch; color: var(--muted); }}
.stats {{ display: flex; flex-wrap: wrap; gap: 8px 24px; align-items: baseline; padding-top: 6px; }}
.stat {{ display: flex; align-items: baseline; gap: 7px; white-space: nowrap; }}
.stat b {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 18px;
  font-weight: 500;
  font-variant-numeric: tabular-nums;
}}
.stat span {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10px;
  letter-spacing: 0.09em;
  text-transform: uppercase;
  color: var(--faint);
}}
.controls {{
  position: sticky; top: 0; z-index: 5;
  display: flex; flex-wrap: wrap; gap: 10px; align-items: center;
  padding: 14px 0; margin-bottom: 6px;
  background: var(--bg); border-bottom: 1px solid var(--line);
}}
.mode {{
  display: flex; flex: 0 0 auto;
  border: 1px solid var(--line); border-radius: 3px; overflow: hidden;
}}
.mode button {{
  padding: 9px 11px; margin: 0; border: 0;
  color: var(--muted); background: var(--surface); cursor: pointer;
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 12px;
}}
.mode button + button {{ border-left: 1px solid var(--line); }}
.mode button:hover {{ color: var(--ink); }}
.mode button[aria-pressed="true"] {{
  color: var(--ink); background: var(--surface-2); box-shadow: inset 0 -2px 0 var(--accent);
}}
input[type="search"] {{
  flex: 1 1 240px; min-width: 200px;
  padding: 9px 12px;
  font: inherit; color: var(--ink);
  background: var(--surface);
  border: 1px solid var(--line); border-radius: 3px;
}}
input[type="search"]::placeholder {{ color: var(--faint); }}
select {{
  padding: 9px 10px;
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 12.5px;
  color: var(--ink); background: var(--surface);
  border: 1px solid var(--line); border-radius: 3px;
}}
input:focus-visible, select:focus-visible, tr:focus-visible, button:focus-visible {{
  outline: 2px solid var(--focus); outline-offset: 1px;
}}
.count {{
  margin-left: auto;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; color: var(--faint); font-variant-numeric: tabular-nums;
}}
.table-scroll {{ overflow-x: auto; }}
/* A table inherits neither colour nor font in quirks mode, and this page ships
   without a doctype because its host supplies one - so opened as a local file it
   lands in quirks mode and the whole table reverts to the light palette on a dark
   ground. Stating both here is what standards mode would have done anyway, and it
   makes the page readable wherever the file is opened. */
table {{
  width: 100%; border-collapse: collapse; min-width: 880px;
  color: var(--ink); font: inherit;
}}
/* Not sticky. The wide-content wrapper needs overflow-x, which makes it a
   scroll container, and a sticky header inside one anchors to the container
   rather than to the viewport - so it parks itself over the first row and
   stays there. The filter bar sits outside the wrapper and sticks properly. */
thead th {{
  padding: 9px 12px; text-align: left;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px; font-weight: 500;
  letter-spacing: 0.09em; text-transform: uppercase; color: var(--faint);
  background: var(--bg); border-bottom: 1px solid var(--line);
  white-space: nowrap;
}}
tr.car {{ border-bottom: 1px solid var(--line); cursor: pointer; }}
tr.car:hover {{ background: var(--surface); }}
tr.car[aria-expanded="true"] {{
  background: var(--surface);
  box-shadow: inset 3px 0 0 var(--accent);
}}
tr.car td {{ padding: 11px 12px; vertical-align: top; }}
.name {{ display: block; font-weight: 600; }}
.shifter {{ display: block; font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 13px; }}
.meta {{ display: block; font-size: 12.5px; color: var(--faint); margin-top: 2px; }}
.rim {{ font-size: 13px; color: var(--muted); white-space: nowrap; }}
.state {{ white-space: nowrap; }}
.tone {{
  display: inline-block; padding: 3px 9px; border-radius: 2px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; line-height: 1.45;
}}
/* The fill carries the meaning: something is being asked of somebody. Amber is
   asked of the driver, teal is handled by the car, and the two hollow states are
   asked of nobody - which is why neither of them is filled. */
.tone-you {{ background: var(--driver-bg); color: var(--driver); font-weight: 500; }}
.tone-car {{ background: var(--car-bg); color: var(--car); }}
/* Optional is a decided fact, not a demand and not a gap. Its own hue keeps it
   off the amber it used to sit beside, where two warm fills read alike. */
.tone-optional {{
  background: none; color: var(--optional);
  border: 1px solid currentColor; padding: 2px 8px;
}}
/* A gap in the evidence must never read as a state the car handles. Dotted,
   and in the neutral, so it separates from the optional outline too. */
.tone-unknown {{
  background: none; color: var(--faint);
  border: 1px dotted currentColor; padding: 2px 8px;
}}
tr.detail > td {{ padding: 0 10px 14px; border-bottom: 1px solid var(--line); background: var(--bg); }}
.detail-inner {{
  padding: 18px 18px 22px;
  background: var(--surface);
  border: 1px solid var(--line); border-top: 2px solid var(--accent);
  border-radius: 0 0 4px 4px;
  box-shadow: 0 8px 24px rgba(15, 18, 24, 0.08);
}}
.detail-inner > div {{
  display: flex; flex-direction: column; gap: 16px; max-width: 78ch;
}}
.summary {{ margin: 0; font-size: 14.5px; }}
.block {{ display: flex; flex-direction: column; gap: 5px; }}
.block h4 {{
  margin: 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px; font-weight: 500;
  letter-spacing: 0.09em; text-transform: uppercase; color: var(--faint);
}}
.block p {{ margin: 0; color: var(--muted); font-size: 14px; }}
.block ul {{ margin: 0; padding: 0; list-style: none; display: flex; flex-direction: column; gap: 7px; }}
.block li {{ font-size: 14px; color: var(--muted); }}
.field {{
  display: inline-block; margin-right: 8px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; color: var(--accent);
}}
.differs-flag, .disagrees-flag, .sim-count {{
  display: inline-block; margin-top: 5px; padding: 1px 6px;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px; letter-spacing: 0.04em;
  color: var(--accent); border: 1px solid currentColor; border-radius: 2px;
}}
.sim-count {{ color: var(--muted); margin-right: 5px; }}
.disagrees-flag {{ color: var(--optional); margin-left: 5px; }}
.simulator-comparison {{
  padding: 12px; border: 1px solid var(--line); background: var(--surface-2);
}}
.simulator-comparison > p {{ font-size: 12.5px; }}
.simulator-comparison li {{ display: flex; flex-wrap: wrap; gap: 5px 10px; }}
.comparison-values {{ display: flex; flex-wrap: wrap; gap: 5px 14px; }}
.comparison-values span {{ font-size: 13px; color: var(--muted); }}
.comparison-values b {{
  margin-right: 4px; color: var(--ink); font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px; font-weight: 500;
}}
.differs {{ gap: 12px; }}
.differs li {{ display: flex; flex-wrap: wrap; align-items: baseline; gap: 6px; }}
.differs .was {{ color: var(--faint); text-decoration: line-through; }}
.differs .arrow {{ color: var(--faint); }}
.differs .now {{ color: var(--ink); font-weight: 600; }}
.differs .why {{ flex: 1 0 100%; margin: 2px 0 0; font-size: 13.5px; color: var(--muted); }}
.chips {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.chip {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 12px; color: var(--faint);
  border: 1px dotted currentColor; border-radius: 2px; padding: 2px 8px;
}}
.provenance {{
  margin: 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11.5px; color: var(--faint);
}}
.simulator-section {{
  display: flex; flex-direction: column; gap: 12px;
  margin-top: 2px; padding-top: 16px; border-top: 1px solid var(--line);
}}
.simulator-heading {{
  display: flex; flex-wrap: wrap; gap: 5px 12px; align-items: baseline;
}}
.simulator-heading h4 {{
  margin: 0;
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 10.5px; font-weight: 500;
  letter-spacing: 0.09em; text-transform: uppercase; color: var(--faint);
}}
.simulator-heading span {{ font-size: 12.5px; color: var(--faint); }}
.sim-tabs {{ display: flex; flex-wrap: wrap; gap: 6px; }}
.sim-tab {{
  padding: 5px 10px; border: 1px solid var(--line); border-radius: 3px;
  color: var(--muted); background: var(--bg); text-decoration: none;
  font-family: "IBM Plex Mono", ui-monospace, monospace; font-size: 12px;
}}
.sim-tab:hover {{ color: var(--ink); border-color: var(--faint); }}
.sim-tab[aria-selected="true"] {{
  color: var(--ink); background: var(--surface-2); border-color: var(--accent);
}}
.sim-panel {{ display: flex; flex-direction: column; gap: 14px; }}
.sim-panel[hidden] {{ display: none; }}
.sim-anchor {{ display: block; height: 0; overflow: hidden; scroll-margin-top: 76px; }}
.sim-panel-title {{
  display: flex; flex-wrap: wrap; gap: 5px 10px; align-items: baseline;
  margin: 0; font-size: 16px; font-weight: 600;
}}
.sim-panel-title span {{
  font-family: "IBM Plex Mono", ui-monospace, monospace;
  font-size: 11px; font-weight: 500; color: var(--accent);
}}
.permalink {{
  width: fit-content; color: var(--accent); font-size: 12.5px;
  text-underline-offset: 3px;
}}
.empty {{ padding: 40px 12px; color: var(--muted); }}
.legend {{
  display: flex; flex-wrap: wrap; gap: 8px 18px;
  margin: 22px 0 0; padding-top: 18px; border-top: 1px solid var(--line);
  font-size: 13px; color: var(--muted);
}}
.legend .tone {{ margin-right: 7px; }}
footer {{ margin-top: 26px; font-size: 13px; color: var(--faint); max-width: 68ch; }}
@media (prefers-reduced-motion: reduce) {{ * {{ transition: none !important; }} }}
@media (max-width: 720px) {{
  .wrap {{ padding: 28px 14px 60px; }}
  .stats {{ gap: 6px 16px; }}
}}
</style>

<div class="wrap">
<header>
  <div class="topline">
    <h1>As Driven</h1>
    <div class="theme" role="group" aria-label="Colour theme">
      <button type="button" data-theme-set="system" aria-pressed="true">System</button>
      <button type="button" data-theme-set="light" aria-pressed="false">Light</button>
      <button type="button" data-theme-set="dark" aria-pressed="false">Dark</button>
    </div>
  </div>
  <p class="lede">Which physical controls to fit, and how to shift, for an authentic
  drive. {total} cars across {simulator_entries} reviewed simulator views,
  curated from manufacturer and homologation sources and verified in-sim. Where
  the evidence does not settle something, this says so rather than guessing.</p>
  <div class="stats">
    <div class="stat"><b>{total}</b><span>cars</span></div>
    <div class="stat"><b>{simulator_count}</b><span>simulators</span></div>
    <div class="stat"><b>{simulator_entries}</b><span>views</span></div>
    <div class="stat"><b>{clutch_start}</b><span>clutch starts</span></div>
    <div class="stat"><b>{you_blip}</b><span>manual blip</span></div>
    <div class="stat"><b>{open_any}</b><span>open questions</span></div>
    <div class="stat"><b>{disagreeing}</b><span>sims disagree</span></div>
  </div>
  <p class="provenance">Dataset {version}, released {released}.</p>
</header>

<div class="controls">
  <div class="mode" role="group" aria-label="Comparison mode">
    <button type="button" data-mode="all" aria-pressed="true">All</button>
    <button type="button" data-mode="multi" aria-pressed="false">Multi-sim</button>
    <button type="button" data-mode="disagreements" aria-pressed="false">Disagreements</button>
  </div>
  <input type="search" id="q" placeholder="Search a car, class or gearbox" aria-label="Search cars">
  <select id="f-simulator" aria-label="Filter by simulator coverage">
    <option value="">Any simulator</option>
    {simulator_options}
  </select>
  <select id="f-actuation" aria-label="Filter by shifter">
    <option value="">Any shifter</option>
    <option value="h-pattern">H-pattern</option>
    <option value="sequential-stick">Sequential stick</option>
    <option value="sequential-paddles">Paddles</option>
  </select>
  <select id="f-start" aria-label="Filter by pulling away">
    <option value="">Pulling away: any</option>
    <option value="required">Clutch required</option>
    <option value="not-required">No clutch needed</option>
  </select>
  <select id="f-blip" aria-label="Filter by downshift blip">
    <option value="">Downshift: any</option>
    <option value="required">You blip</option>
    <option value="optional">Blip optional</option>
    <option value="not-required">No blip needed</option>
    <option value="unknown">Not established</option>
  </select>
  <span class="count" id="count"></span>
</div>

<div class="table-scroll">
<table>
  <thead><tr>
    <th scope="col">Car</th><th scope="col">Shifter</th>
    <th scope="col">Pulling away</th><th scope="col">Upshift</th>
    <th scope="col">Downshift</th><th scope="col">Wheel</th>
  </tr></thead>
  <tbody id="rows">
{rows}
  </tbody>
</table>
</div>
<p class="empty" id="empty" hidden>No car matches those filters.</p>

<div class="legend">
  <span><span class="tone tone-you">You do this</span></span>
  <span><span class="tone tone-car">The car does this</span></span>
  <span><span class="tone tone-optional">Your choice</span></span>
  <span><span class="tone tone-unknown">Not established</span></span>
</div>

<footer>Select a car for the mechanism it shares with others, where it departs
from that, and what a drive or a source would still have to settle. Every row
describes the real car. Open it to choose a reviewed simulator; differences and
simulator-specific evidence gaps stay inside that view, because they are
separate facts and neither overwrites the real car. Each simulator view has a
stable link that can be shared.</footer>
</div>

<script>
(function () {{
  var q = document.getElementById('q');
  var simulatorFilter = document.getElementById('f-simulator');
  var mode = 'all';
  var modeButtons = Array.prototype.slice.call(
    document.querySelectorAll('[data-mode]'));
  var filters = ['actuation', 'start', 'blip'].map(function (name) {{
    return {{ name: name, node: document.getElementById('f-' + name) }};
  }});
  var rows = Array.prototype.slice.call(document.querySelectorAll('tr.car'));
  var count = document.getElementById('count');
  var empty = document.getElementById('empty');

  function apply() {{
    var text = q.value.trim().toLowerCase();
    var shown = 0;
    rows.forEach(function (row) {{
      var ok = !text || row.dataset.search.indexOf(text) !== -1;
      if (ok && mode === 'multi' && row.dataset.multiSim !== 'true') {{
        ok = false;
      }}
      if (ok && mode === 'disagreements'
          && row.dataset.simDisagreement !== 'true') {{
        ok = false;
      }}
      var wantedSimulator = simulatorFilter.value;
      if (ok && wantedSimulator
          && row.dataset.simulators.indexOf(' ' + wantedSimulator + ' ') === -1) {{
        ok = false;
      }}
      filters.forEach(function (filter) {{
        var want = filter.node.value;
        if (ok && want && row.dataset[filter.name] !== want) {{ ok = false; }}
      }});
      row.hidden = !ok;
      var detail = row.nextElementSibling;
      if (!ok && detail) {{
        setOpen(row, false);
      }} else if (ok && wantedSimulator && detail && !detail.hidden) {{
        selectSimulator(row, wantedSimulator);
      }}
      if (ok) {{ shown++; }}
    }});
    count.textContent = shown === rows.length
      ? rows.length + ' cars'
      : shown + ' of ' + rows.length + ' cars';
    empty.hidden = shown !== 0;
  }}

  function setOpen(row, open) {{
    var detail = row.nextElementSibling;
    if (!detail) {{ return; }}
    detail.hidden = !open;
    row.setAttribute('aria-expanded', open ? 'true' : 'false');
  }}

  function selectSimulator(row, simulator) {{
    var detail = row.nextElementSibling;
    if (!detail) {{ return false; }}
    var tabs = Array.prototype.slice.call(detail.querySelectorAll('[data-simulator-tab]'));
    var panels = Array.prototype.slice.call(detail.querySelectorAll('[data-simulator-panel]'));
    var found = false;
    tabs.forEach(function (tab) {{
      var selected = tab.getAttribute('data-simulator-tab') === simulator;
      tab.setAttribute('aria-selected', selected ? 'true' : 'false');
      tab.setAttribute('tabindex', selected ? '0' : '-1');
      if (selected) {{ found = true; }}
    }});
    panels.forEach(function (panel) {{
      panel.hidden = panel.getAttribute('data-simulator-panel') !== simulator;
    }});
    return found;
  }}

  function toggle(row) {{
    var detail = row.nextElementSibling;
    if (!detail) {{ return; }}
    var open = detail.hidden;
    setOpen(row, open);
    if (open && simulatorFilter.value) {{
      selectSimulator(row, simulatorFilter.value);
    }}
  }}

  rows.forEach(function (row) {{
    row.addEventListener('click', function () {{ toggle(row); }});
    row.addEventListener('keydown', function (event) {{
      if (event.key === 'Enter' || event.key === ' ') {{
        event.preventDefault();
        toggle(row);
      }}
    }});
  }});

  var simulatorTabs = Array.prototype.slice.call(
    document.querySelectorAll('[data-simulator-tab]'));
  simulatorTabs.forEach(function (tab) {{
    tab.addEventListener('click', function () {{
      var detail = tab.closest('tr.detail');
      var row = detail ? detail.previousElementSibling : null;
      if (!row) {{ return; }}
      setOpen(row, true);
      selectSimulator(row, tab.getAttribute('data-simulator-tab'));
    }});
    tab.addEventListener('keydown', function (event) {{
      if (event.key !== 'ArrowLeft' && event.key !== 'ArrowRight') {{ return; }}
      var tabs = Array.prototype.slice.call(
        tab.parentElement.querySelectorAll('[data-simulator-tab]'));
      var direction = event.key === 'ArrowRight' ? 1 : -1;
      var next = tabs[(tabs.indexOf(tab) + direction + tabs.length) % tabs.length];
      event.preventDefault();
      next.focus();
      next.click();
    }});
  }});

  function restoreSimulatorLink(scroll) {{
    if (!window.location.hash) {{ return; }}
    var anchor;
    try {{ anchor = decodeURIComponent(window.location.hash.slice(1)); }}
    catch (error) {{ return; }}
    var link = document.getElementById(anchor);
    if (!link || !link.hasAttribute('data-simulator-anchor-target')) {{ return; }}
    var row = link.closest('tr.car');
    if (!row) {{ return; }}
    var simulator = link.getAttribute('data-simulator-anchor-target');
    if (scroll) {{
      simulatorFilter.value = simulator;
      apply();
    }}
    setOpen(row, true);
    selectSimulator(row, simulator);
    if (scroll) {{
      window.setTimeout(function () {{ row.scrollIntoView({{ block: 'center' }}); }}, 0);
    }}
  }}

  window.addEventListener('hashchange', function () {{ restoreSimulatorLink(false); }});
  // Three states, because that is what the stylesheet answers to: an explicit
  // choice stamps the root element, and following the system stamps nothing.
  // Without the third button a reader who picked one could never hand the
  // decision back to their machine.
  var root = document.documentElement;
  var themeButtons = Array.prototype.slice.call(
    document.querySelectorAll('[data-theme-set]'));

  function setTheme(choice, remember) {{
    if (choice === 'light' || choice === 'dark') {{
      root.setAttribute('data-theme', choice);
    }} else {{
      root.removeAttribute('data-theme');
      choice = 'system';
    }}
    themeButtons.forEach(function (button) {{
      button.setAttribute(
        'aria-pressed', button.getAttribute('data-theme-set') === choice ? 'true' : 'false');
    }});
    if (remember) {{
      try {{ localStorage.setItem('as-driven-theme', choice); }} catch (error) {{}}
    }}
  }}

  themeButtons.forEach(function (button) {{
    button.addEventListener('click', function () {{
      setTheme(button.getAttribute('data-theme-set'), true);
    }});
  }});

  var remembered = null;
  try {{ remembered = localStorage.getItem('as-driven-theme'); }} catch (error) {{}}
  setTheme(remembered || 'system', false);

  modeButtons.forEach(function (button) {{
    button.addEventListener('click', function () {{
      mode = button.getAttribute('data-mode');
      modeButtons.forEach(function (candidate) {{
        candidate.setAttribute(
          'aria-pressed', candidate === button ? 'true' : 'false');
      }});
      apply();
    }});
  }});

  q.addEventListener('input', apply);
  simulatorFilter.addEventListener('change', apply);
  filters.forEach(function (filter) {{ filter.node.addEventListener('change', apply); }});
  apply();
  restoreSimulatorLink(true);
}})();
</script>
"""

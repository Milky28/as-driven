from __future__ import annotations

import csv
import re
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED_COLUMNS = {
    "Car",
    "Chassis Manufacturer",
    "Class",
    "Year",
    "Auto Blip",
    "Shift Cut",
    "# of Gears",
    "Shift Type",
    "Wheel Rim Type",
}

OPTIONAL_COLUMNS = {"Steering DOR"}


def _indicator(value: str) -> str:
    normalized = value.strip().casefold()
    # This blank-to-No rule is source-specific and must not be reused globally.
    if normalized in {"", "n", "no", "false", "0", "-"}:
        return "no"
    if normalized in {"y", "yes", "true", "1", "x"}:
        return "yes"
    return "unknown"


def _integer(value: str) -> int | None:
    match = re.search(r"\d+", value)
    return int(match.group()) if match else None


def _year(value: str) -> dict[str, Any]:
    years = [int(item) for item in re.findall(r"(?:18|19|20|21)\d{2}", value)]
    result: dict[str, Any] = {"label": value.strip() or "unknown"}
    if years:
        result["from"] = years[0]
        result["to"] = years[-1]
    return result


def _shift(value: str) -> dict[str, str]:
    key = value.strip().casefold()
    exact = {
        "h": ("unknown", "h-pattern", "standard-h"),
        "h-dogleg": ("unknown", "h-pattern", "dogleg-h"),
        "seq-stick": ("sequential", "sequential-stick", "sequential"),
        "seq-paddle": ("sequential", "sequential-paddles", "sequential"),
        "paddles": ("sequential", "sequential-paddles", "sequential"),
        "automatic": ("automatic", "automatic-lever", "automatic-gate"),
        "seq": ("sequential", "unknown", "sequential"),
    }
    gearbox, actuation, pattern = exact.get(key, ("unknown", "unknown", "unknown"))
    return {"gearbox_type": gearbox, "shift_actuation": actuation, "shift_pattern": pattern}


def _wheel(value: str) -> dict[str, str]:
    raw = value.strip()
    code = raw.upper()
    # The compact source code is preserved. The source discussion explicitly
    # describes GTF1 as a modern GT/F1-style rim; F1 identifies the formula
    # family; and an initial R establishes the round family. Other source codes
    # continue to fail closed.
    if code.startswith("GTF1"):
        shape = "gt-style"
    elif code.startswith("F1"):
        shape = "formula"
    elif code.startswith("R"):
        shape = "round"
    else:
        shape = "unknown"
    return {"normalized": shape, "source_label": raw}


def import_ams2_csv(
    path: Path, *, source_id: str, verified_game_version: str
) -> dict[str, Any]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        try:
            headers = next(reader)
        except StopIteration as exc:
            raise ValueError("AMS2 CSV is empty") from exc
        missing = sorted(REQUIRED_COLUMNS - set(headers))
        if missing:
            raise ValueError(f"AMS2 CSV missing columns: {', '.join(missing)}")
        positions = {
            name: headers.index(name)
            for name in REQUIRED_COLUMNS | OPTIONAL_COLUMNS
            if name in headers
        }
        candidates = []
        for line_number, row in enumerate(reader, start=2):
            if len(row) < len(headers):
                row += [""] * (len(headers) - len(row))
            get = lambda name: row[positions[name]].strip() if name in positions else ""
            car = get("Car")
            # The source currently has a machine-name row immediately below
            # the display headers, plus class-divider rows that contain a
            # label in Car but no class or control data.
            if not car or car.casefold() == "name":
                continue
            if not any(
                get(name)
                for name in ("Class", "# of Gears", "Shift Type", "Wheel Rim Type")
            ):
                continue
            shift = _shift(get("Shift Type"))
            rim = _wheel(get("Wheel Rim Type"))
            auto_blip = _indicator(get("Auto Blip"))
            shift_cut = _indicator(get("Shift Cut"))
            steering_dor = _integer(get("Steering DOR"))
            steering = {
                "wheel_rim": {
                    "shape": rim["normalized"],
                    "source_label": rim["source_label"],
                }
            }
            behavior = {
                "shift_type": get("Shift Type") or "unknown",
                "auto_blip": auto_blip,
                "shift_cut": shift_cut,
                "wheel_rim_type": rim,
            }
            if steering_dor is not None:
                steering["degrees_of_rotation"] = steering_dor
                behavior["steering_dor"] = steering_dor
            candidates.append(
                {
                    "source_row": line_number,
                    "identity": {
                        "display_name": car,
                        "chassis_manufacturer": get("Chassis Manufacturer") or "unknown",
                        "year": _year(get("Year")),
                        "class": get("Class") or "unknown",
                    },
                    "authentic_controls_candidate": {
                        "transmission": {
                            "forward_gears": _integer(get("# of Gears")),
                            **shift,
                        },
                        "steering": steering,
                    },
                    "simulator_candidate": {
                        "simulator": "ams2",
                        "verified_game_version": verified_game_version,
                        "behavior": behavior,
                    },
                    "raw_source_values": {
                        name: get(name)
                        for name in sorted(REQUIRED_COLUMNS | OPTIONAL_COLUMNS)
                        if name in positions
                    },
                }
            )
    return {
        "importer": "ams2-google-sheet-csv",
        "importer_version": "0.1.1",
        "source_id": source_id,
        "imported_at": date.today().isoformat(),
        "review_required": True,
        "source_rules": [
            "Blank Auto Blip and Shift Cut indicators are No for this source only.",
            "Compact wheel-rim labels are preserved; GTF1 prefixes normalize to GT-style, F1 prefixes normalize to Formula, and R prefixes normalize to round.",
            "H-Dogleg describes actuation/layout and does not establish synchromesh versus dogbox.",
            "Steering DOR is retained when present but is optional reference metadata.",
        ],
        "candidates": candidates,
    }

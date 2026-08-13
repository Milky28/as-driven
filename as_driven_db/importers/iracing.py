from __future__ import annotations

import re
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from typing import Any


def _key(value: str) -> str:
    value = value.replace("–", "-").replace("—", "-").replace("‑", "-")
    return re.sub(r"\s+", " ", value).strip().casefold()


CATEGORY_PROFILES: dict[str, dict[str, Any]] = {
    _key("Semi-Automatic Sequential"): {
        "gearbox_type": "semi-automatic",
        "shift_actuation": "sequential-paddles-or-stick",
        "shift_cut": "yes",
        "auto_blip": "unknown",
        "upshift_lift": "not-required",
        "downshift_manual_blip": "not-required",
    },
    _key("Automatic Dual Clutch - Manual Shift"): {
        "gearbox_type": "dual-clutch",
        "shift_actuation": "sequential-paddles",
        "shift_cut": "yes",
        "auto_blip": "yes",
        "upshift_lift": "not-required",
        "downshift_manual_blip": "not-required",
    },
    _key("Dog-Box Sequential - with throttle cut"): {
        "gearbox_type": "dogbox",
        "shift_actuation": "sequential-stick",
        "shift_cut": "yes",
        "auto_blip": "no",
        "upshift_lift": "not-required",
        "downshift_manual_blip": "required",
    },
    _key("Dog-Box Sequential - without throttle cut"): {
        "gearbox_type": "dogbox",
        "shift_actuation": "sequential-stick",
        "shift_cut": "no",
        "auto_blip": "no",
        "upshift_lift": "required",
        "downshift_manual_blip": "required",
    },
    _key("Dog-Box H-Pattern"): {
        "gearbox_type": "dogbox",
        "shift_actuation": "h-pattern",
        "shift_cut": "no",
        "auto_blip": "no",
        "upshift_lift": "required",
        "downshift_manual_blip": "required",
    },
    _key("Synchromesh H-Pattern"): {
        "gearbox_type": "synchromesh",
        "shift_actuation": "h-pattern",
        "shift_cut": "no",
        "auto_blip": "no",
        "upshift_lift": "required",
        "downshift_manual_blip": "optional",
    },
    _key("Dog Box - 1 and 2 Speed"): {
        "gearbox_type": "dogbox",
        "shift_actuation": "direct-selection",
        "shift_cut": "not-applicable",
        "auto_blip": "not-applicable",
        "upshift_lift": "not-applicable",
        "downshift_manual_blip": "not-applicable",
    },
    _key("Direct Drive"): {
        "gearbox_type": "direct-drive",
        "shift_actuation": "direct-selection",
        "shift_cut": "not-applicable",
        "auto_blip": "not-applicable",
        "upshift_lift": "not-applicable",
        "downshift_manual_blip": "not-applicable",
    },
    _key("Automatic - Manual Shift"): {
        "gearbox_type": "automatic",
        "shift_actuation": "automatic-lever",
        "shift_cut": "not-applicable",
        "auto_blip": "not-applicable",
        "upshift_lift": "not-required",
        "downshift_manual_blip": "not-required",
    },
}


class _IRacingListParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.current_category: str | None = None
        self.in_li = False
        self.li_parts: list[str] = []
        self.items: list[tuple[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.casefold() == "li":
            self.in_li = True
            self.li_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag.casefold() == "li" and self.in_li:
            text = re.sub(r"\s+", " ", " ".join(self.li_parts)).strip()
            if self.current_category and text:
                self.items.append((self.current_category, text))
            self.in_li = False
            self.li_parts = []

    def handle_data(self, data: str) -> None:
        text = re.sub(r"\s+", " ", data).strip()
        if not text:
            return
        normalized = _key(text)
        # Some revisions put the category title and "Gear Lever" text in the
        # same HTML node. Longest-prefix matching accepts that layout without
        # matching a car name or inventing a new category.
        for category in sorted(CATEGORY_PROFILES, key=len, reverse=True):
            if normalized == category or normalized.startswith(category + " "):
                self.current_category = category
                break
        if self.in_li:
            self.li_parts.append(text)


def _car_parts(raw: str) -> tuple[str, int | None, bool]:
    legacy = raw.strip().casefold().startswith("[legacy]")
    cleaned = re.sub(r"^\[Legacy\]\s*", "", raw, flags=re.IGNORECASE).strip()
    speed = re.search(r"\((\d+)[- ]?[Ss]peed", cleaned)
    gears = int(speed.group(1)) if speed else None
    name = re.sub(r"\s*\([^)]*\d+[- ]?[Ss]peed[^)]*\)\s*", " ", cleaned)
    name = re.sub(r"\s+", " ", name).strip(" -")
    return name, gears, legacy


def import_iracing_html(path: Path, *, source_id: str) -> dict[str, Any]:
    parser = _IRacingListParser()
    parser.feed(path.read_text(encoding="utf-8"))
    candidates = []
    for category, raw_car in parser.items:
        name, gears, legacy = _car_parts(raw_car)
        profile = CATEGORY_PROFILES[category]
        candidates.append(
            {
                "identity": {"display_name": name},
                "simulator_candidate": {
                    "simulator": "iracing",
                    "legacy_content": legacy,
                    "behavior": {"forward_gears": gears, **profile},
                },
                "source_category": category,
                "raw_source_value": raw_car,
            }
        )
    return {
        "importer": "iracing-transmission-html",
        "importer_version": "0.1.0",
        "source_id": source_id,
        "imported_at": date.today().isoformat(),
        "review_required": True,
        "source_rules": [
            "Category-level instructions are inherited by each listed car.",
            "No iRacing page date is treated as a game build; reviewers must add verified_game_version separately.",
            "No-blip-required is kept separate from automatic blip when the article does not establish the mechanism.",
        ],
        "candidates": candidates,
    }

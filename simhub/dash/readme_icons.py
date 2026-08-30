"""Dark-tiled copies of the preflight icons, for the README.

The production icons are one off-white colour on transparency because they are
drawn onto a dark dashboard. Embedded directly in the README they are invisible
against GitHub's light theme, so this renders the same geometry onto an opaque
dark tile.

It calls the production builders rather than redrawing anything, so the README
cannot end up illustrating shapes the plugin no longer uses.

    python simhub/dash/readme_icons.py
"""

from __future__ import annotations

import argparse
from pathlib import Path

from icons import INK, Canvas, generate_preflight_icons

OUTPUT_DIRECTORY = Path(__file__).resolve().parents[2] / "docs" / "images"

# One representative icon per thing the card answers, rather than the whole
# family: the README is an introduction, not the asset inventory. Only current
# vocabulary belongs here - `yoke` is retired, labelled "Open-top rim (legacy)"
# by PreflightLabels, and held by no curated record.
README_ICONS = (
    "wheel-round",
    "wheel-gt-formula",
    "wheel-d-shaped-open-top",
    "shift-h-pattern",
    "shift-dogleg-h",
    "shift-sequential-stick",
    "control-clutch",
    "control-throttle",
)

TILE_RADIUS = 22.0


def _tile(canvas: Canvas, color: tuple[int, int, int, int] = INK) -> None:
    """Fill the canvas with an opaque rounded tile."""
    size = float(canvas.size)
    radius = TILE_RADIUS
    canvas.polygon(
        [(radius, 0.0), (size - radius, 0.0), (size - radius, size), (radius, size)],
        color,
    )
    canvas.polygon(
        [(0.0, radius), (size, radius), (size, size - radius), (0.0, size - radius)],
        color,
    )
    for x in (radius, size - radius):
        for y in (radius, size - radius):
            canvas.disk(x, y, radius, color)


def build() -> dict[str, bytes]:
    """Render the README subset as opaque PNG tiles."""
    from icons import (  # noqa: PLC0415 - the builders are module-private
        _flat_clutch,
        _flat_shifter,
        _flat_throttle,
        _flat_wheel,
    )

    builders = {
        "wheel-round": lambda canvas: _flat_wheel(canvas, "round"),
        "wheel-gt-formula": lambda canvas: _flat_wheel(canvas, "gt-formula"),
        "wheel-d-shaped-open-top": lambda canvas: _flat_wheel(
            canvas, "d-shaped", open_top=True
        ),
        "shift-h-pattern": lambda canvas: _flat_shifter(canvas, "h-pattern"),
        "shift-dogleg-h": lambda canvas: _flat_shifter(canvas, "dogleg-h"),
        "shift-sequential-stick": lambda canvas: _flat_shifter(
            canvas, "sequential-stick"
        ),
        "control-clutch": _flat_clutch,
        "control-throttle": _flat_throttle,
    }
    missing = sorted(set(README_ICONS) - set(generate_preflight_icons()))
    if missing:
        raise ValueError(f"no production icon is named: {', '.join(missing)}")

    output: dict[str, bytes] = {}
    for name in README_ICONS:
        canvas = Canvas(size=128)
        _tile(canvas)
        builders[name](canvas)
        output[name] = canvas.png()
    return output


def write(output_directory: Path = OUTPUT_DIRECTORY) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    for name, data in build().items():
        (output_directory / f"{name}.png").write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=OUTPUT_DIRECTORY)
    write(parser.parse_args().output)

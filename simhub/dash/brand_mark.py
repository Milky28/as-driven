"""Deterministic brand-mark candidates for the As Driven plugin.

The production mark is a checked-in PNG that cannot be reviewed in a diff. These
candidates are generated from code the same way the control icons are, so a
change to the silhouette is a readable edit rather than an opaque binary.

Why the production mark reads as a helmeted face: a closed enclosing circle, a
symmetric pair of horizontal spokes at brow height, a central mass where a nose
sits, a cluster of vertical bars where a mouth sits, and exact bilateral
symmetry. The circle alone is not the fault; the symmetric internal arrangement
is.

Two rules follow, learned by rendering the first attempts and looking at them:

1. Nothing touches the rim. An element joined to the arc at the same stroke
   weight fuses into one outline and the mark reads as a letter, not a wheel.
2. No symmetric pairs, and no centred mass. Offset the shifter instead.
"""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from icons import INK, RGBA, WHITE, Canvas

VARIANTS = ("lever", "rim-lever", "gate")


def _lever(canvas: Canvas, color: RGBA, s: float, *, scale: float = 1.0,
           dx: float = 0.0, dy: float = 0.0) -> None:
    """Raked gear lever: ball, shaft, and a short gate bar at the base."""
    def p(x: float, y: float) -> tuple[float, float]:
        return ((64 + (x - 64) * scale + dx) * s, (64 + (y - 64) * scale + dy) * s)

    canvas.line([p(70, 52), p(52, 99)], 14.0 * s * scale, color)
    ball = p(76, 39)
    canvas.disk(ball[0], ball[1], 17.0 * s * scale, color)
    canvas.line([p(34, 105), p(70, 105)], 9.0 * s * scale, color)


def _rim(canvas: Canvas, color: RGBA, s: float, *, radius: float,
         stroke: float) -> None:
    canvas.ellipse(64 * s, 64 * s, radius * s, radius * s, stroke * s, color)


def _gate(canvas: Canvas, color: RGBA, s: float) -> None:
    """H-pattern gate with the lever resting in one gate, so it is asymmetric."""
    stroke = 9.0 * s
    canvas.line([(44 * s, 34 * s), (44 * s, 94 * s)], stroke, color)
    canvas.line([(88 * s, 34 * s), (88 * s, 94 * s)], stroke, color)
    canvas.line([(44 * s, 64 * s), (88 * s, 64 * s)], stroke, color)
    canvas.disk(88 * s, 34 * s, 14.0 * s, color)


def build(variant: str, *, size: int = 128, on_dark: bool = False) -> bytes:
    canvas = Canvas(size=size, supersample=4)
    s = size / 128.0
    if on_dark:
        # Review aid only: the shipped mark is white on transparency, which is
        # invisible against a light preview background.
        canvas.disk(64 * s, 64 * s, 96 * s, INK)

    if variant == "lever":
        _lever(canvas, WHITE, s)
    elif variant == "rim-lever":
        # Thin rim, bold lever, generous negative space between them.
        _rim(canvas, WHITE, s, radius=47.0, stroke=7.0)
        _lever(canvas, WHITE, s, scale=0.60, dx=4.0, dy=-2.0)
    elif variant == "gate":
        _gate(canvas, WHITE, s)
    else:
        raise SystemExit(f"unknown variant: {variant}")
    return canvas.png()


# The selected production silhouette, and the two places it ships. The plugin
# embeds its copy and downscales to 24 and 64 pixels at runtime; the dashboard
# generator packs a 128-pixel raster.
PRODUCTION_VARIANT = "rim-lever"
_REPO = Path(__file__).resolve().parents[2]
PRODUCTION_TARGETS = (
    (_REPO / "simhub" / "AsDriven.Plugin" / "Assets"
     / "as-driven-mark.png", 512),
    (_REPO / "simhub" / "dash" / "assets" / "brand-mark.png", 128),
)


def write_production() -> list[Path]:
    """Write the selected mark to both shipped locations."""
    written = []
    for path, size in PRODUCTION_TARGETS:
        path.write_bytes(build(PRODUCTION_VARIANT, size=size))
        written.append(path)
    return written


def main() -> None:
    parser = argparse.ArgumentParser(description="Render brand-mark candidates.")
    parser.add_argument("--output", type=Path)
    parser.add_argument("--size", type=int, default=128)
    parser.add_argument(
        "--on-dark",
        action="store_true",
        help="render on an ink disk so a white mark is visible in review",
    )
    parser.add_argument(
        "--production",
        action="store_true",
        help=f"write the selected {PRODUCTION_VARIANT} mark to both shipped assets",
    )
    args = parser.parse_args()

    if args.production:
        for path in write_production():
            print(f"wrote {path.relative_to(_REPO).as_posix()}")
        return

    if args.output is None:
        raise SystemExit("--output is required unless --production is given")
    args.output.mkdir(parents=True, exist_ok=True)
    for variant in VARIANTS:
        path = args.output / f"mark-{variant}-{args.size}.png"
        path.write_bytes(build(variant, size=args.size, on_dark=args.on_dark))
        print(f"wrote {path}")


if __name__ == "__main__":
    main()

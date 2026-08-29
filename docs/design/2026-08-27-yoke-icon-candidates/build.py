from __future__ import annotations

import math
import sys
from collections.abc import Callable
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "simhub" / "dash"))

from icons import Canvas, RGBA, WHITE, _flat_wheel  # noqa: E402


class ScaledCanvas:
    """Map the production 128-pixel drawing grid onto a review size."""

    def __init__(self, size: int) -> None:
        self.canvas = Canvas(size=size, supersample=8 if size <= 24 else 4)
        self.scale = size / 128

    def disk(self, x: float, y: float, radius: float, color: RGBA) -> None:
        self.canvas.disk(x * self.scale, y * self.scale, radius * self.scale, color)

    def line(
        self,
        points: list[tuple[float, float]],
        width: float,
        color: RGBA,
        *,
        closed: bool = False,
    ) -> None:
        self.canvas.line(
            [(x * self.scale, y * self.scale) for x, y in points],
            width * self.scale,
            color,
            closed=closed,
        )

    def ellipse(
        self,
        center_x: float,
        center_y: float,
        radius_x: float,
        radius_y: float,
        width: float,
        color: RGBA,
        *,
        start: float = 0,
        end: float = math.tau,
    ) -> None:
        self.canvas.ellipse(
            center_x * self.scale,
            center_y * self.scale,
            radius_x * self.scale,
            radius_y * self.scale,
            width * self.scale,
            color,
            start=start,
            end=end,
        )

    def rectangle(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        width: float,
        color: RGBA,
    ) -> None:
        self.canvas.rectangle(
            left * self.scale,
            top * self.scale,
            right * self.scale,
            bottom * self.scale,
            width * self.scale,
            color,
        )


Builder = Callable[[ScaledCanvas], None]


def current(canvas: ScaledCanvas) -> None:
    _flat_wheel(canvas, "yoke")


def open_arc(canvas: ScaledCanvas) -> None:
    """The semantic minimum: an unmistakably open steering rim."""
    canvas.ellipse(
        64,
        61,
        45,
        47,
        12,
        WHITE,
        start=-0.25 * math.pi,
        end=1.25 * math.pi,
    )


def grip_arc(canvas: ScaledCanvas) -> None:
    """An open rim with heavier hand-grip zones and no human-like hub."""
    canvas.ellipse(
        64,
        61,
        44,
        46,
        8,
        WHITE,
        start=-0.25 * math.pi,
        end=1.25 * math.pi,
    )
    canvas.line([(96, 28), (103, 48), (99, 69)], 17, WHITE)
    canvas.line([(32, 28), (25, 48), (29, 69)], 17, WHITE)


def low_hub(canvas: ScaledCanvas) -> None:
    """A low center boss avoids the head-and-body reading of the current hub."""
    canvas.line(
        [(24, 30), (31, 67), (47, 91), (64, 101), (81, 91), (97, 67), (104, 30)],
        11,
        WHITE,
    )
    canvas.line([(34, 62), (50, 77), (78, 77), (94, 62)], 8, WHITE)
    canvas.rectangle(51, 72, 77, 91, 6, WHITE)


def center_bar(canvas: ScaledCanvas) -> None:
    """A broad race-yoke crossbar reads as equipment, not anatomy."""
    canvas.line([(24, 29), (31, 63), (47, 77), (81, 77), (97, 63), (104, 29)], 12, WHITE)
    canvas.line([(43, 76), (85, 76)], 12, WHITE)
    canvas.rectangle(53, 65, 75, 87, 6, WHITE)


CANDIDATES: dict[str, Builder] = {
    "current": current,
    "a-open-arc": open_arc,
    "b-grip-arc": grip_arc,
    "c-low-hub": low_hub,
    "d-center-bar": center_bar,
}


def main() -> None:
    output = Path(__file__).resolve().parent
    for name, builder in CANDIDATES.items():
        for size in (128, 24):
            canvas = ScaledCanvas(size)
            builder(canvas)
            (output / f"{name}-{size}.png").write_bytes(canvas.canvas.png())


if __name__ == "__main__":
    main()

from __future__ import annotations

import argparse
import math
import struct
import zlib
from collections.abc import Callable
from pathlib import Path


RGBA = tuple[int, int, int, int]
WHITE: RGBA = (255, 255, 255, 255)
AMBER: RGBA = (255, 176, 32, 255)
ORANGE: RGBA = (255, 135, 91, 255)
MUTED: RGBA = (142, 160, 178, 255)
GHOST: RGBA = (217, 226, 236, 118)
INK: RGBA = (17, 26, 36, 255)
RASTER_ASSET_DIRECTORY = Path(__file__).with_name("assets")
PREFLIGHT_ASSET_DIRECTORY = Path(__file__).with_name("preflight-assets")


class Canvas:
    """Small dependency-free supersampled icon canvas."""

    def __init__(self, size: int = 128, supersample: int = 4) -> None:
        self.size = size
        self.supersample = supersample
        self.width = size * supersample
        self.pixels = bytearray(self.width * self.width * 4)

    def _blend(self, x: int, y: int, color: RGBA) -> None:
        if x < 0 or y < 0 or x >= self.width or y >= self.width:
            return
        offset = (y * self.width + x) * 4
        source_alpha = color[3] / 255.0
        destination_alpha = self.pixels[offset + 3] / 255.0
        output_alpha = source_alpha + destination_alpha * (1.0 - source_alpha)
        if output_alpha <= 0:
            return
        for channel in range(3):
            destination = self.pixels[offset + channel]
            output = (
                color[channel] * source_alpha
                + destination * destination_alpha * (1.0 - source_alpha)
            ) / output_alpha
            self.pixels[offset + channel] = round(output)
        self.pixels[offset + 3] = round(output_alpha * 255)

    def disk(self, x: float, y: float, radius: float, color: RGBA) -> None:
        scale = self.supersample
        cx, cy, r = x * scale, y * scale, radius * scale
        left = max(0, math.floor(cx - r))
        right = min(self.width - 1, math.ceil(cx + r))
        top = max(0, math.floor(cy - r))
        bottom = min(self.width - 1, math.ceil(cy + r))
        radius_squared = r * r
        for py in range(top, bottom + 1):
            for px in range(left, right + 1):
                if (px + 0.5 - cx) ** 2 + (py + 0.5 - cy) ** 2 <= radius_squared:
                    self._blend(px, py, color)

    def clear_disk(self, x: float, y: float, radius: float) -> None:
        scale = self.supersample
        cx, cy, r = x * scale, y * scale, radius * scale
        left = max(0, math.floor(cx - r))
        right = min(self.width - 1, math.ceil(cx + r))
        top = max(0, math.floor(cy - r))
        bottom = min(self.width - 1, math.ceil(cy + r))
        radius_squared = r * r
        for py in range(top, bottom + 1):
            for px in range(left, right + 1):
                if (px + 0.5 - cx) ** 2 + (py + 0.5 - cy) ** 2 <= radius_squared:
                    offset = (py * self.width + px) * 4
                    self.pixels[offset : offset + 4] = b"\x00\x00\x00\x00"

    def polygon(self, points: list[tuple[float, float]], color: RGBA) -> None:
        scale = self.supersample
        scaled = [(x * scale, y * scale) for x, y in points]
        left = max(0, math.floor(min(point[0] for point in scaled)))
        right = min(self.width - 1, math.ceil(max(point[0] for point in scaled)))
        top = max(0, math.floor(min(point[1] for point in scaled)))
        bottom = min(self.width - 1, math.ceil(max(point[1] for point in scaled)))
        for py in range(top, bottom + 1):
            sample_y = py + 0.5
            for px in range(left, right + 1):
                sample_x = px + 0.5
                inside = False
                previous = scaled[-1]
                for current in scaled:
                    if ((current[1] > sample_y) != (previous[1] > sample_y)) and (
                        sample_x
                        < (previous[0] - current[0])
                        * (sample_y - current[1])
                        / (previous[1] - current[1])
                        + current[0]
                    ):
                        inside = not inside
                    previous = current
                if inside:
                    self._blend(px, py, color)

    def line(
        self,
        points: list[tuple[float, float]],
        width: float,
        color: RGBA,
        *,
        closed: bool = False,
    ) -> None:
        pairs = list(zip(points, points[1:]))
        if closed and len(points) > 2:
            pairs.append((points[-1], points[0]))
        for start, end in pairs:
            self._segment(start, end, width, color)

    def _segment(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        width: float,
        color: RGBA,
    ) -> None:
        scale = self.supersample
        x1, y1 = start[0] * scale, start[1] * scale
        x2, y2 = end[0] * scale, end[1] * scale
        radius = width * scale / 2
        left = max(0, math.floor(min(x1, x2) - radius))
        right = min(self.width - 1, math.ceil(max(x1, x2) + radius))
        top = max(0, math.floor(min(y1, y2) - radius))
        bottom = min(self.width - 1, math.ceil(max(y1, y2) + radius))
        dx, dy = x2 - x1, y2 - y1
        length_squared = dx * dx + dy * dy
        for py in range(top, bottom + 1):
            for px in range(left, right + 1):
                if length_squared == 0:
                    projection = 0.0
                else:
                    projection = ((px + 0.5 - x1) * dx + (py + 0.5 - y1) * dy) / length_squared
                    projection = max(0.0, min(1.0, projection))
                nearest_x = x1 + projection * dx
                nearest_y = y1 + projection * dy
                if (px + 0.5 - nearest_x) ** 2 + (py + 0.5 - nearest_y) ** 2 <= radius * radius:
                    self._blend(px, py, color)

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
        steps = max(24, round(max(radius_x, radius_y) * abs(end - start) / 3))
        points = [
            (
                center_x + math.cos(start + (end - start) * index / steps) * radius_x,
                center_y + math.sin(start + (end - start) * index / steps) * radius_y,
            )
            for index in range(steps + 1)
        ]
        self.line(points, width, color, closed=abs(end - start - math.tau) < 0.001)

    def rectangle(
        self,
        left: float,
        top: float,
        right: float,
        bottom: float,
        width: float,
        color: RGBA,
    ) -> None:
        self.line(
            [(left, top), (right, top), (right, bottom), (left, bottom)],
            width,
            color,
            closed=True,
        )

    def arrow_head(
        self,
        tip: tuple[float, float],
        direction_radians: float,
        size: float,
        width: float,
        color: RGBA,
    ) -> None:
        back = direction_radians + math.pi
        left = (
            tip[0] + math.cos(back - 0.55) * size,
            tip[1] + math.sin(back - 0.55) * size,
        )
        right = (
            tip[0] + math.cos(back + 0.55) * size,
            tip[1] + math.sin(back + 0.55) * size,
        )
        self.line([left, tip, right], width, color)

    def png(self) -> bytes:
        output = bytearray(self.size * self.size * 4)
        sample_count = self.supersample * self.supersample
        for y in range(self.size):
            for x in range(self.size):
                alpha_sum = 0
                premultiplied = [0, 0, 0]
                for sample_y in range(self.supersample):
                    for sample_x in range(self.supersample):
                        source_x = x * self.supersample + sample_x
                        source_y = y * self.supersample + sample_y
                        source = (source_y * self.width + source_x) * 4
                        alpha = self.pixels[source + 3]
                        alpha_sum += alpha
                        for channel in range(3):
                            premultiplied[channel] += self.pixels[source + channel] * alpha
                target = (y * self.size + x) * 4
                if alpha_sum:
                    for channel in range(3):
                        output[target + channel] = round(premultiplied[channel] / alpha_sum)
                output[target + 3] = round(alpha_sum / sample_count)
        raw = b"".join(
            b"\x00" + bytes(output[row * self.size * 4 : (row + 1) * self.size * 4])
            for row in range(self.size)
        )
        signature = b"\x89PNG\r\n\x1a\n"
        return signature + _chunk(b"IHDR", struct.pack(">IIBBBBB", self.size, self.size, 8, 6, 0, 0, 0)) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")


def _chunk(kind: bytes, data: bytes) -> bytes:
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)


SEGMENTS = {
    "0": "ab cdef".replace(" ", ""),
    "1": "bc",
    "2": "abdeg",
    "3": "abcdg",
    "4": "bcfg",
    "5": "acdfg",
    "6": "acdefg",
    "7": "abc",
    "8": "abcdefg",
    "9": "abcdfg",
}


def _glyph(canvas: Canvas, value: str, x: float, y: float, scale: float, color: RGBA = WHITE) -> None:
    if value == "R":
        canvas.line([(x, y + 12 * scale), (x, y), (x + 6 * scale, y), (x + 7 * scale, y + 5 * scale), (x, y + 6 * scale)], 1.7 * scale, color)
        canvas.line([(x + 3 * scale, y + 6 * scale), (x + 8 * scale, y + 12 * scale)], 1.7 * scale, color)
        return
    segments = SEGMENTS[value]
    definitions = {
        "a": ((x, y), (x + 7 * scale, y)),
        "b": ((x + 7 * scale, y), (x + 7 * scale, y + 6 * scale)),
        "c": ((x + 7 * scale, y + 6 * scale), (x + 7 * scale, y + 12 * scale)),
        "d": ((x, y + 12 * scale), (x + 7 * scale, y + 12 * scale)),
        "e": ((x, y + 6 * scale), (x, y + 12 * scale)),
        "f": ((x, y), (x, y + 6 * scale)),
        "g": ((x, y + 6 * scale), (x + 7 * scale, y + 6 * scale)),
    }
    for segment in segments:
        canvas.line(list(definitions[segment]), 1.7 * scale, color)


def _question(canvas: Canvas, color: RGBA = MUTED) -> None:
    canvas.ellipse(64, 64, 45, 45, 6, color)
    canvas.line([(51, 48), (56, 39), (69, 37), (78, 43), (78, 53), (64, 64), (64, 73)], 7, color)
    canvas.disk(64, 88, 4, color)


def _wheel(canvas: Canvas, kind: str) -> None:
    if kind == "unknown":
        _question(canvas)
        return
    if kind == "gt-formula":
        canvas.rectangle(34, 38, 94, 88, 7, WHITE)
        canvas.line([(34, 43), (22, 36), (18, 47), (22, 88), (35, 96), (42, 84)], 10, WHITE)
        canvas.line([(94, 43), (106, 36), (110, 47), (106, 88), (93, 96), (86, 84)], 10, WHITE)
        canvas.disk(64, 64, 7, WHITE)
        return
    if kind == "yoke":
        canvas.line([(22, 35), (38, 28), (53, 58), (75, 58), (90, 28), (106, 35)], 9, WHITE)
        canvas.line([(64, 58), (64, 94)], 7, WHITE)
        canvas.disk(64, 60, 8, WHITE)
        return
    if kind == "d-shaped":
        points = [(64 + math.cos(angle) * 45, 62 + math.sin(angle) * 45) for angle in [math.pi + index * math.pi / 24 for index in range(25)]]
        points.extend([(105, 85), (23, 85)])
        canvas.line(points, 7, WHITE, closed=True)
    else:
        canvas.ellipse(64, 64, 45, 45, 7, WHITE)
    canvas.disk(64, 64, 7, WHITE)
    canvas.line([(58, 60), (32, 48)], 6, WHITE)
    canvas.line([(70, 60), (96, 48)], 6, WHITE)
    canvas.line([(64, 70), (64, 98)], 6, WHITE)


def _gate(canvas: Canvas, dogleg: bool) -> None:
    xs = [28, 64, 100]
    canvas.line([(28, 37), (28, 91)], 5, WHITE)
    canvas.line([(64, 37), (64, 91)], 5, WHITE)
    canvas.line([(100, 37), (100, 91)], 5, WHITE)
    canvas.line([(28, 64), (100, 64)], 5, WHITE)
    top = ["R", "2", "4"] if dogleg else ["1", "3", "5"]
    bottom = ["1", "3", "5"] if dogleg else ["2", "4", "6"]
    for index, value in enumerate(top):
        _glyph(canvas, value, xs[index] - 4, 16, 0.9)
    for index, value in enumerate(bottom):
        _glyph(canvas, value, xs[index] - 4, 99, 0.9)
    if dogleg:
        canvas.line([(18, 107), (38, 107)], 4, AMBER)


def _shift(canvas: Canvas, kind: str) -> None:
    if kind == "unknown":
        _question(canvas)
    elif kind == "h-pattern":
        _gate(canvas, False)
    elif kind == "dogleg-h":
        _gate(canvas, True)
    elif kind == "sequential-stick":
        canvas.rectangle(50, 15, 78, 58, 7, WHITE)
        canvas.line([(55, 26), (73, 26)], 4, MUTED)
        canvas.line([(64, 58), (64, 101)], 7, WHITE)
        canvas.line([(39, 104), (89, 104)], 8, WHITE)
        canvas.line([(92, 30), (108, 30)], 4, AMBER)
        canvas.line([(100, 22), (100, 38)], 4, AMBER)
        canvas.line([(92, 81), (108, 81)], 4, AMBER)
    elif kind == "sequential-paddles":
        canvas.ellipse(64, 64, 37, 37, 7, WHITE)
        canvas.rectangle(15, 29, 27, 94, 6, WHITE)
        canvas.rectangle(101, 29, 113, 94, 6, WHITE)
        canvas.disk(64, 64, 7, WHITE)
    elif kind == "automatic-lever":
        canvas.rectangle(35, 13, 82, 113, 6, WHITE)
        canvas.line([(58, 28), (58, 98)], 6, WHITE)
        canvas.disk(58, 28, 11, WHITE)
        for y in (30, 52, 74, 96):
            canvas.line([(92, y), (108, y)], 4, MUTED)
    elif kind == "direct-selection":
        canvas.rectangle(13, 38, 115, 90, 6, WHITE)
        for index, x in enumerate((34, 64, 94)):
            canvas.ellipse(x, 64, 12, 12, 4, AMBER if index == 0 else WHITE)


def _manual_badge(canvas: Canvas, x: float = 98, y: float = 96) -> None:
    canvas.disk(x, y, 20, AMBER)
    canvas.line(
        [(x - 10, y + 8), (x - 10, y - 9), (x, y + 2), (x + 10, y - 9), (x + 10, y + 8)],
        5,
        INK,
    )


def _gear(canvas: Canvas) -> None:
    center_x, center_y = 53, 62
    points: list[tuple[float, float]] = []
    for index in range(8):
        angle = index * math.pi / 4
        for offset, radius in (
            (-0.31, 34),
            (-0.22, 34),
            (-0.18, 45),
            (0.18, 45),
            (0.22, 34),
            (0.31, 34),
        ):
            points.append(
                (
                    center_x + math.cos(angle + offset) * radius,
                    center_y + math.sin(angle + offset) * radius,
                )
            )
    canvas.polygon(points, WHITE)
    canvas.clear_disk(center_x, center_y, 14)
    canvas.line([(76, 25), (62, 57), (79, 56), (66, 99), (101, 50), (82, 51), (95, 25)], 6, AMBER)


def _pedal_blip(canvas: Canvas, manual: bool) -> None:
    if manual:
        pedal = [(29, 25), (65, 16), (78, 88), (42, 100)]
        canvas.line(pedal, 8, WHITE, closed=True)
        for x, y in ((45, 34), (51, 50), (56, 66), (62, 82)):
            canvas.disk(x, y, 2.7, WHITE)
        canvas.line([(61, 96), (69, 112)], 7, WHITE)
        canvas.line([(50, 114), (91, 114)], 7, WHITE)
        _manual_badge(canvas)
    else:
        canvas.line([(49, 35), (76, 27), (85, 88), (56, 96)], 7, WHITE, closed=True)
        canvas.ellipse(64, 61, 47, 47, 6, AMBER, start=math.pi * 0.35, end=math.pi * 1.75)
        tip = (98, 28)
        canvas.arrow_head(tip, -0.55, 16, 6, AMBER)


def _lift_required(canvas: Canvas) -> None:
    # Traced from the approved ImageGen concept: one pressing foot, one lifted ghost,
    # and exactly one curved direction arrow.
    canvas.line([(17, 31), (43, 27), (58, 102), (31, 110), (17, 31)], 7, WHITE, closed=True)
    for x, y in ((29, 43), (33, 57), (37, 71), (42, 85), (47, 99)):
        canvas.disk(x, y, 2.4, WHITE)
    pressing = [(38, 58), (53, 50), (67, 60), (80, 67), (101, 72), (108, 82), (96, 91), (76, 87), (57, 77), (42, 72)]
    canvas.line(pressing, 7, WHITE, closed=True)
    lifted = [(48, 48), (57, 29), (69, 25), (80, 38), (91, 47), (108, 52), (111, 63), (100, 69), (85, 65), (69, 55)]
    canvas.line(lifted, 6, GHOST, closed=True)
    arrow = [(48, 38), (44, 27), (49, 18), (62, 12), (76, 13), (88, 21)]
    canvas.line(arrow, 6, AMBER)
    canvas.arrow_head((88, 21), 0.55, 15, 6, AMBER)


def generate_icons(size: int = 128) -> dict[str, bytes]:
    builders: dict[str, Callable[[Canvas], None]] = {
        "brand-mark": lambda canvas: _wheel(canvas, "round"),
        "wheel-round": lambda canvas: _wheel(canvas, "round"),
        "wheel-d-shaped": lambda canvas: _wheel(canvas, "d-shaped"),
        "wheel-gt-formula": lambda canvas: _wheel(canvas, "gt-formula"),
        "wheel-yoke": lambda canvas: _wheel(canvas, "yoke"),
        "wheel-unknown": lambda canvas: _wheel(canvas, "unknown"),
        "shift-h-pattern": lambda canvas: _shift(canvas, "h-pattern"),
        "shift-dogleg-h": lambda canvas: _shift(canvas, "dogleg-h"),
        "shift-sequential-stick": lambda canvas: _shift(canvas, "sequential-stick"),
        "shift-sequential-paddles": lambda canvas: _shift(canvas, "sequential-paddles"),
        "shift-automatic-lever": lambda canvas: _shift(canvas, "automatic-lever"),
        "shift-direct-selection": lambda canvas: _shift(canvas, "direct-selection"),
        "shift-unknown": lambda canvas: _shift(canvas, "unknown"),
        "cut-auto": _gear,
        "cut-unknown": _question,
        "blip-auto": lambda canvas: _pedal_blip(canvas, False),
        "blip-manual": lambda canvas: _pedal_blip(canvas, True),
        "blip-unknown": _question,
        "lift-required": _lift_required,
    }
    icons: dict[str, bytes] = {}
    for name, builder in builders.items():
        raster_path = RASTER_ASSET_DIRECTORY / f"{name}.png"
        if raster_path.is_file():
            data = raster_path.read_bytes()
            if data[:8] != b"\x89PNG\r\n\x1a\n" or len(data) < 24:
                raise ValueError(f"Raster icon is not a valid PNG: {raster_path}")
            width, height = struct.unpack(">II", data[16:24])
            if (width, height) != (size, size):
                raise ValueError(
                    f"Raster icon must be {size}x{size}, got {width}x{height}: {raster_path}"
                )
            icons[name] = data
            continue
        canvas = Canvas(size=size)
        builder(canvas)
        icons[name] = canvas.png()
    return icons


def _flat_wheel(canvas: Canvas, kind: str) -> None:
    """Monochrome wheel-rim symbols for the row-based preflight overlay."""
    if kind == "unknown":
        _question(canvas, WHITE)
        return

    if kind == "gt-formula":
        # Broad modern race-wheel body with molded side grips, a control face,
        # and a continuous lower rim. Display presence remains separate data;
        # the rectangle identifies the wheel category, not fitted equipment.
        rim = [
            (35, 23), (93, 23), (105, 29), (113, 48),
            (111, 76), (99, 99), (83, 106), (45, 106),
            (29, 99), (17, 76), (15, 48), (23, 29),
        ]
        canvas.line(rim, 11, WHITE, closed=True)
        canvas.rectangle(43, 35, 85, 65, 6, WHITE)
        for x in (35, 93):
            canvas.disk(x, 43, 4, WHITE)
            canvas.disk(x, 57, 4, WHITE)
        for x in (52, 64, 76):
            canvas.disk(x, 80, 5, WHITE)
        canvas.line([(42, 94), (86, 94)], 7, WHITE)
        return

    if kind == "yoke":
        # A broad open-top U reads as steering hardware rather than the narrow
        # fork/antenna silhouette produced by the earlier concept.
        canvas.line([(23, 30), (31, 72), (48, 94), (64, 102), (80, 94), (97, 72), (105, 30)], 11, WHITE)
        canvas.disk(64, 70, 8, WHITE)
        canvas.line([(58, 68), (35, 58)], 8, WHITE)
        canvas.line([(70, 68), (93, 58)], 8, WHITE)
        canvas.line([(64, 77), (64, 98)], 8, WHITE)
        return

    if kind == "other":
        rim = [(64, 17), (96, 28), (111, 57), (101, 91), (64, 109), (27, 91), (17, 57), (32, 28)]
        canvas.line(rim, 9, WHITE, closed=True)
        canvas.disk(64, 64, 8, WHITE)
        canvas.line([(58, 60), (33, 45)], 8, WHITE)
        canvas.line([(70, 60), (95, 45)], 8, WHITE)
        canvas.line([(64, 71), (64, 96)], 8, WHITE)
        return

    if kind == "d-shaped":
        arc = [
            (64 + math.cos(math.pi + index * math.pi / 32) * 45,
             62 + math.sin(math.pi + index * math.pi / 32) * 45)
            for index in range(33)
        ]
        rim = arc + [(101, 94), (27, 94)]
        canvas.line(rim, 9, WHITE, closed=True)
    else:
        canvas.ellipse(64, 64, 46, 46, 9, WHITE)

    canvas.disk(64, 64, 8, WHITE)
    canvas.line([(58, 60), (34, 47)], 8, WHITE)
    canvas.line([(70, 60), (94, 47)], 8, WHITE)
    canvas.line([(64, 71), (64, 96 if kind == "round" else 89)], 8, WHITE)


def _flat_gate(canvas: Canvas, *, dogleg: bool) -> None:
    xs = (34, 64, 94)
    for x in xs:
        canvas.line([(x, 32), (x, 96)], 7, WHITE)
    canvas.line([(34, 64), (94, 64)], 7, WHITE)
    canvas.disk(34, 94 if dogleg else 34, 8, WHITE)
    if dogleg:
        # The heavier rising route makes the isolated first-gear position read
        # even after the 128-pixel master is reduced to a 24-pixel row glyph.
        canvas.line([(34, 90), (34, 64), (64, 64), (64, 38)], 10, WHITE)


def _flat_shifter(canvas: Canvas, kind: str) -> None:
    if kind == "unknown":
        _question(canvas, WHITE)
    elif kind == "h-pattern":
        _flat_gate(canvas, dogleg=False)
    elif kind == "dogleg-h":
        _flat_gate(canvas, dogleg=True)
    elif kind == "sequential-stick":
        # Tall cylindrical motorsport handle rather than a road-car ball knob.
        canvas.ellipse(64, 17, 15, 6, 7, WHITE, start=math.pi, end=math.tau)
        canvas.line([(49, 17), (49, 52)], 7, WHITE)
        canvas.line([(79, 17), (79, 52)], 7, WHITE)
        canvas.ellipse(64, 52, 15, 6, 7, WHITE, start=0, end=math.pi)
        canvas.line([(64, 58), (64, 84)], 11, WHITE)
        canvas.line([(43, 88), (85, 88)], 10, WHITE)
        canvas.line([(35, 103), (93, 103)], 10, WHITE)
    elif kind == "sequential-paddles":
        # Two independent solid blades, based on the familiar OEM-style paddle
        # profile. The wider center gap keeps them distinct at row-icon size;
        # no hub or bridge is implied because the paddles are separate controls.
        left = [
            (38, 16), (24, 33), (15, 57), (16, 84), (28, 108),
            (43, 116), (38, 98), (34, 81), (35, 63), (43, 40),
        ]
        right = [(128 - x, y) for x, y in left]
        canvas.polygon(left, WHITE)
        canvas.polygon(right, WHITE)
    elif kind == "automatic-lever":
        # Side-view automatic selector with its P-R-N-D positions, rather than
        # a manual-style gate. The compact stroke letters remain useful marks
        # when the icon is reduced below the size where they can be read.
        knob = [
            (22, 13), (46, 13), (51, 18), (51, 47),
            (46, 52), (22, 52), (17, 47), (17, 18),
        ]
        canvas.polygon(knob, WHITE)
        canvas.line([(13, 57), (57, 57)], 11, WHITE)
        canvas.line([(34, 62), (34, 108), (51, 108), (51, 78)], 9, WHITE)

        rows = (20, 46, 72, 98)
        for y in rows:
            canvas.line([(61, y), (70, y)], 4, WHITE)

        # P
        canvas.line([(78, 29), (78, 11), (91, 11), (95, 15), (95, 20), (91, 24), (78, 24)], 4, WHITE)
        # R
        canvas.line([(78, 55), (78, 37), (91, 37), (95, 41), (95, 46), (91, 49), (78, 49)], 4, WHITE)
        canvas.line([(88, 49), (96, 56)], 4, WHITE)
        # N
        canvas.line([(78, 81), (78, 63), (96, 81), (96, 63)], 4, WHITE)
        # D
        canvas.line([(78, 107), (78, 89), (89, 89), (96, 96), (96, 100), (89, 107), (78, 107)], 4, WHITE)
    elif kind == "direct-selection":
        for index, x in enumerate((30, 64, 98)):
            canvas.ellipse(x, 64, 15, 15, 7, WHITE)
            if index == 0:
                canvas.disk(x, 64, 7, WHITE)
        canvas.line([(17, 99), (111, 99)], 8, WHITE)


def _flat_clutch(canvas: Canvas) -> None:
    # A broad solid pad and centered stem read as a pedal rather than a hand at
    # small sizes. Punched grip holes preserve the familiar motorsport face.
    canvas.line([(64, 12), (64, 52)], 12, WHITE)
    face = [
        (31, 48), (97, 48), (104, 56), (99, 109),
        (92, 116), (36, 116), (29, 109), (24, 56),
    ]
    canvas.polygon(face, WHITE)
    for x, y in ((47, 68), (81, 68), (64, 84), (47, 101), (81, 101)):
        canvas.clear_disk(x, y, 6)


def _flat_throttle(canvas: Canvas) -> None:
    # A narrower, taller pad and offset bent stem distinguish the accelerator
    # from the clutch before the grip-hole pattern can be resolved.
    canvas.line([(39, 10), (39, 34), (54, 51)], 12, WHITE)
    face = [
        (47, 45), (85, 45), (92, 52), (96, 115),
        (90, 121), (42, 121), (36, 115), (40, 52),
    ]
    canvas.polygon(face, WHITE)
    for x, y in ((56, 62), (76, 62), (66, 77), (56, 92), (76, 92), (66, 108)):
        canvas.clear_disk(x, y, 5.2)


def _flat_info(canvas: Canvas) -> None:
    canvas.ellipse(64, 64, 45, 45, 8, WHITE)
    canvas.disk(64, 42, 6, WHITE)
    canvas.line([(64, 57), (64, 88)], 10, WHITE)


def generate_preflight_icons(size: int = 128) -> dict[str, bytes]:
    """Build the flat, single-colour family used by the row-based proposal."""
    if size != 128:
        raise ValueError("Preflight icon masters are authored on a 128-pixel grid")
    builders: dict[str, Callable[[Canvas], None]] = {
        "wheel-round": lambda canvas: _flat_wheel(canvas, "round"),
        "wheel-d-shaped": lambda canvas: _flat_wheel(canvas, "d-shaped"),
        "wheel-gt-formula": lambda canvas: _flat_wheel(canvas, "gt-formula"),
        "wheel-yoke": lambda canvas: _flat_wheel(canvas, "yoke"),
        "wheel-other": lambda canvas: _flat_wheel(canvas, "other"),
        "wheel-unknown": lambda canvas: _flat_wheel(canvas, "unknown"),
        "shift-h-pattern": lambda canvas: _flat_shifter(canvas, "h-pattern"),
        "shift-dogleg-h": lambda canvas: _flat_shifter(canvas, "dogleg-h"),
        "shift-sequential-stick": lambda canvas: _flat_shifter(canvas, "sequential-stick"),
        "shift-sequential-paddles": lambda canvas: _flat_shifter(canvas, "sequential-paddles"),
        "shift-automatic-lever": lambda canvas: _flat_shifter(canvas, "automatic-lever"),
        "shift-direct-selection": lambda canvas: _flat_shifter(canvas, "direct-selection"),
        "shift-unknown": lambda canvas: _flat_shifter(canvas, "unknown"),
        "control-clutch": _flat_clutch,
        "control-throttle": _flat_throttle,
        "note-info": _flat_info,
    }
    output: dict[str, bytes] = {}
    for name, builder in builders.items():
        canvas = Canvas(size=size)
        builder(canvas)
        output[name] = canvas.png()
    return output


def write_preflight_icons(output_directory: Path = PREFLIGHT_ASSET_DIRECTORY) -> None:
    output_directory.mkdir(parents=True, exist_ok=True)
    for name, data in generate_preflight_icons().items():
        (output_directory / f"{name}.png").write_bytes(data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Render the flat preflight icon family.")
    parser.add_argument(
        "--output",
        type=Path,
        default=PREFLIGHT_ASSET_DIRECTORY,
        help="directory for the 128x128 transparent PNG masters",
    )
    arguments = parser.parse_args()
    write_preflight_icons(arguments.output)

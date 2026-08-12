from __future__ import annotations

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
    if kind == "formula":
        canvas.rectangle(39, 43, 89, 84, 6, WHITE)
        canvas.line([(39, 46), (24, 35), (19, 43), (22, 84), (34, 94), (42, 83)], 10, WHITE)
        canvas.line([(89, 46), (104, 35), (109, 43), (106, 84), (94, 94), (86, 83)], 10, WHITE)
        canvas.disk(64, 64, 7, WHITE)
        return
    if kind == "gt-style":
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
        "wheel-gt-style": lambda canvas: _wheel(canvas, "gt-style"),
        "wheel-prototype": lambda canvas: _wheel(canvas, "formula"),
        "wheel-formula": lambda canvas: _wheel(canvas, "formula"),
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

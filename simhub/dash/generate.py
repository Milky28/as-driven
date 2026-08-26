from __future__ import annotations

import argparse
import hashlib
import json
import uuid
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, NamedTuple

from icons import RASTER_ASSET_DIRECTORY, generate_preflight_icons


ACCENT = "#FF27C7F3"
GREEN = "#FF45D483"
ORANGE = "#FFFF875B"
WHITE = "#FFFFFFFF"
TEXT = "#FFD9E2EC"
MUTED = "#FF91A9BD"
SLATE = "#FF24465F"
CARD = "#F20A1119"
GROUP_PANEL = "#66102030"
TRANSPARENT = "#00FFFFFF"
ICON_SIZE = 128


class TemplateSpec(NamedTuple):
    key: str
    stem: str
    width: int
    height: int
    overlay: bool = True


TEMPLATES = (
    TemplateSpec("detailed", "As Driven Preflight Overlay", 720, 428),
    TemplateSpec("compact", "As Driven Preflight Compact", 520, 360),
    TemplateSpec("verification", "As Driven Verification Drive", 700, 220),
    TemplateSpec("display", "As Driven Preflight Display", 780, 360, False),
)


@lru_cache(maxsize=1)
def _icon_assets() -> dict[str, bytes]:
    """The flat preflight family, plus the brand mark used in the card title.

    The mark is a reviewed raster rather than generated geometry, so it is read
    from the approved asset directory instead of being redrawn here.
    """
    assets = generate_preflight_icons(size=ICON_SIZE)
    assets["brand-mark"] = (RASTER_ASSET_DIRECTORY / "brand-mark.png").read_bytes()
    return assets


def _image_metadata() -> list[dict[str, Any]]:
    return [
        {
            "Name": name,
            "Extension": ".png",
            "Modified": False,
            "Optimized": True,
            "Width": ICON_SIZE,
            "Height": ICON_SIZE,
            "Length": len(data),
            "MD5": hashlib.md5(data).hexdigest().upper(),
        }
        for name, data in sorted(_icon_assets().items())
    ]


class ItemFactory:
    def __init__(self, width: int, height: int) -> None:
        self.width = width
        self.height = height
        self._sid = 0

    def _next_sid(self) -> int:
        self._sid += 1
        return self._sid

    @staticmethod
    def _binding(expression: str, target: str) -> dict[str, Any]:
        return {
            "Formula": {"Expression": expression},
            "Mode": 2,
            "TargetPropertyName": target,
        }

    def rectangle(
        self,
        name: str,
        left: float,
        top: float,
        width: float,
        height: float,
        color: str,
        *,
        radius: int = 0,
        border_color: str = TRANSPARENT,
        border: int = 0,
        rotation: float = 0,
    ) -> dict[str, Any]:
        item = {
            "$type": "SimHub.Plugins.OutputPlugins.GraphicalDash.Models.RectangleItem, SimHub.Plugins",
            "IsRectangleItem": True,
            "BackgroundColor": color,
            "BorderStyle": {
                "BorderTop": border,
                "BorderBottom": border,
                "BorderLeft": border,
                "BorderRight": border,
                "BorderColor": border_color,
                "RadiusTopLeft": radius,
                "RadiusTopRight": radius,
                "RadiusBottomLeft": radius,
                "RadiusBottomRight": radius,
            },
            "Left": left,
            "Top": top,
            "Width": width,
            "Height": height,
            "Visible": True,
            "Name": name,
            "Sid": self._next_sid(),
        }
        if rotation:
            item["Rotation"] = rotation
        return item

    def ellipse(
        self,
        name: str,
        left: float,
        top: float,
        width: float,
        height: float,
        color: str,
        *,
        thickness: float = 3,
        fill: str = TRANSPARENT,
    ) -> dict[str, Any]:
        return {
            "$type": "SimHub.Plugins.OutputPlugins.GraphicalDash.Models.EllipseItem, SimHub.Plugins",
            "FillColor": fill,
            "EllipseColor": color,
            "EllipseThickness": thickness,
            "EllipseBackgroundImage": "None",
            "BackgroundColor": TRANSPARENT,
            "Left": left,
            "Top": top,
            "Width": width,
            "Height": height,
            "Visible": True,
            "Name": name,
            "Sid": self._next_sid(),
        }

    def image(
        self,
        name: str,
        asset_name: str,
        left: float,
        top: float,
        width: float,
        height: float,
    ) -> dict[str, Any]:
        return {
            "$type": "SimHub.Plugins.OutputPlugins.GraphicalDash.Models.ImageItem, SimHub.Plugins",
            "Image": asset_name,
            "AutoSize": False,
            "BackgroundColor": TRANSPARENT,
            "Left": left,
            "Top": top,
            "Width": width,
            "Height": height,
            "Opacity": 100.0,
            "Visible": True,
            "IsFreezed": True,
            "Name": name,
            "Sid": self._next_sid(),
        }

    def text(
        self,
        name: str,
        text: str,
        left: float,
        top: float,
        width: float,
        height: float,
        font_size: float,
        color: str,
        *,
        expression: str | None = None,
        horizontal_alignment: int = 0,
        font_weight: str = "Normal",
        rotation: float = 0,
    ) -> dict[str, Any]:
        item: dict[str, Any] = {
            "$type": "SimHub.Plugins.OutputPlugins.GraphicalDash.Models.TextItem, SimHub.Plugins",
            "IsTextItem": True,
            "Font": "Segoe UI",
            "FontWeight": font_weight,
            "FontStyle": "Normal",
            "FontSize": font_size,
            "Text": text,
            "TextColor": color,
            "HorizontalAlignment": horizontal_alignment,
            "VerticalAlignment": 1,
            "TextMask": "0" * 64,
            "BackgroundColor": TRANSPARENT,
            "Left": left,
            "Top": top,
            "Width": width,
            "Height": height,
            "Visible": True,
            "Name": name,
            "Sid": self._next_sid(),
        }
        if rotation:
            item["Rotation"] = rotation
        if expression is not None:
            item["Bindings"] = {"Text": self._binding(expression, "Text")}
        return item

    def layer(
        self,
        name: str,
        children: list[dict[str, Any]],
        *,
        visible_expression: str | None = None,
    ) -> dict[str, Any]:
        layer: dict[str, Any] = {
            "$type": "SimHub.Plugins.OutputPlugins.GraphicalDash.Models.Layer, SimHub.Plugins",
            "Top": 0.0,
            "Left": 0.0,
            "Height": float(self.height),
            "Width": float(self.width),
            "BackgroundColor": TRANSPARENT,
            "Childrens": children,
            "Group": True,
            "Visible": True,
            "Name": name,
            "Sid": self._next_sid(),
        }
        if visible_expression is not None:
            layer["Bindings"] = {
                "Visible": self._binding(visible_expression, "Visible")
            }
        return layer


def _wheel_icon(factory: ItemFactory, prefix: str, x: float, y: float, scale: float) -> list[dict[str, Any]]:
    size = 46 * scale
    prop = "[AsDriven.WheelRimShape]"
    # gt-style, prototype and formula are retired into gt-formula and share its
    # icon. They stay matched so an older installed dataset still renders.
    merged = (
        prop + " == 'gt-formula' || " + prop + " == 'gt-style' || "
        + prop + " == 'prototype' || " + prop + " == 'formula'"
    )
    variants = (
        ("Round", "wheel-round", prop + " == 'round'"),
        ("DShape", "wheel-d-shaped", prop + " == 'd-shaped'"),
        ("GTFormula", "wheel-gt-formula", merged),
        ("Yoke", "wheel-yoke", prop + " == 'yoke'"),
        (
            "Unknown",
            "wheel-unknown",
            prop + " != 'round' && " + prop + " != 'd-shaped' && "
            + prop + " != 'gt-formula' && " + prop + " != 'gt-style' && "
            + prop + " != 'prototype' && " + prop + " != 'formula' && "
            + prop + " != 'yoke'",
        ),
    )
    return [
        factory.layer(
            prefix + suffix,
            [factory.image(prefix + suffix + "Bitmap", asset, x, y, size, size)],
            visible_expression=expression,
        )
        for suffix, asset, expression in variants
    ]


def _shift_icon(factory: ItemFactory, prefix: str, x: float, y: float, scale: float) -> list[dict[str, Any]]:
    prop = "[AsDriven.ShiftActuation]"
    size = 46 * scale
    variants = (
        ("HPattern", "shift-h-pattern", prop + " == 'h-pattern' && [AsDriven.ShiftPattern] != 'dogleg-h'"),
        (
            "DoglegH",
            "shift-dogleg-h",
            prop + " == 'h-pattern' && [AsDriven.ShiftPattern] == 'dogleg-h'"
            " && [AsDriven.FirstGearPosition] != 'down-right'",
        ),
        (
            "DoglegHMirrored",
            "shift-dogleg-h-mirrored",
            prop + " == 'h-pattern' && [AsDriven.ShiftPattern] == 'dogleg-h'"
            " && [AsDriven.FirstGearPosition] == 'down-right'",
        ),
        ("Stick", "shift-sequential-stick", prop + " == 'sequential-stick'"),
        ("Paddles", "shift-sequential-paddles", prop + " == 'sequential-paddles'"),
        ("Automatic", "shift-automatic-lever", prop + " == 'automatic-lever'"),
        ("Direct", "shift-direct-selection", prop + " == 'direct-selection'"),
        (
            "Unknown",
            "shift-unknown",
            prop + " != 'h-pattern' && " + prop + " != 'sequential-stick' && "
            + prop + " != 'sequential-paddles' && " + prop + " != 'automatic-lever' && "
            + prop + " != 'direct-selection'",
        ),
    )
    return [
        factory.layer(
            prefix + suffix,
            [factory.image(prefix + suffix + "Bitmap", asset, x, y, size, size)],
            visible_expression=expression,
        )
        for suffix, asset, expression in variants
    ]


def _frame(factory: ItemFactory) -> list[dict[str, Any]]:
    margin = 4
    return [
        # The card and accent share symmetric safe areas. This avoids a clipped
        # frame or accent after Dash Studio applies display scaling.
        factory.rectangle("CardShadow", 6, 7, factory.width - 12, factory.height - 12, "#B0000000", radius=18),
        factory.rectangle("Card", margin, margin, factory.width - 2 * margin, factory.height - 2 * margin, CARD, radius=17, border_color=SLATE, border=2),
        factory.rectangle("Accent", 20, margin, factory.width - 40, 5, ACCENT, radius=2),
    ]


def _header(factory: ItemFactory, compact: bool = False) -> list[dict[str, Any]]:
    mark_size = 40 if compact else 46
    left = 16 if compact else 28
    top = 15 if compact else 22
    return [factory.image("Mark", "brand-mark", left, top, mark_size, mark_size)]


def _confidence_value_expression() -> str:
    prop = "[AsDriven.Confidence]"
    return (
        f"if({prop} == 'verified', 'Verified', "
        f"if({prop} == 'high', 'High', "
        f"if({prop} == 'medium', 'Medium', "
        f"if({prop} == 'low', 'Low', 'Unknown'))))"
    )


def _preview_badge(
    factory: ItemFactory,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    compact: bool = False,
) -> dict[str, Any]:
    if compact:
        text_items = [
            factory.text("PreviewBadgeTitle", "PREVIEW", left, top + 2, width, 13, 8, "#FF07121C", horizontal_alignment=1, font_weight="Bold"),
            factory.text("PreviewBadgeLive", "NOT LIVE", left, top + 14, width, 12, 7.5, "#FF07121C", horizontal_alignment=1, font_weight="Bold"),
        ]
    else:
        text_items = [
            factory.text("PreviewBadgeText", "PREVIEW - NOT LIVE", left, top, width, height, 10.5, "#FF07121C", horizontal_alignment=1, font_weight="Bold"),
        ]
    return factory.layer(
        "PreviewBadge",
        [factory.rectangle("PreviewBadgeBackground", left, top, width, height, ACCENT, radius=6)] + text_items,
        visible_expression="[AsDriven.MatchKind] == 'preview'",
    )



BAND_PANEL = "#6B102030"
NOTE_PANEL = "#1427C7F3"
RAIL_FIT = "#2227C7F3"
RAIL_YOU = "#26FF875B"
RAIL_CAR = "#2145D483"
CELL_YOU = "#1AFF875B"
CELL_CAR = "#1745D483"


def _tone_layers(
    factory: ItemFactory,
    prefix: str,
    tone_property: str,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    you: str,
    car: str,
    unknown: str | None = None,
    radius: int = 0,
) -> list[dict[str, Any]]:
    """Stack one rectangle per tone and let visibility pick between them.

    A rectangle's fill is a fixed value in the dashboard model, so a colour that
    depends on the car has to be expressed as overlapping items. This is the
    same mechanism the icon variants already use.
    """
    prop = "[AsDriven." + tone_property + "]"
    variants = [("You", you, prop + " == 'you'"), ("Car", car, prop + " == 'car'")]
    if unknown is not None:
        # Optional and unknown share a transparent cell: neither is demanded of
        # the driver, and neither is handled by the car.
        variants.append((
            "Rest", unknown, prop + " != 'you' && " + prop + " != 'car'"))
    return [
        factory.layer(
            prefix + suffix,
            [factory.rectangle(prefix + suffix + "Fill", left, top, width, height, color, radius=radius)],
            visible_expression=expression,
        )
        for suffix, color, expression in variants
    ]


def _known_text(
    factory: ItemFactory,
    prefix: str,
    tone_property: str,
    left: float,
    top: float,
    width: float,
    height: float,
    size: float,
    *,
    expression: str,
) -> list[dict[str, Any]]:
    """Ordinary text for an established value, grey for a gap.

    A simpler split than `_tone_text`: this line states a fact about the car
    rather than dividing work between the driver and the car, so there is no
    "you" or "car" colour to pick. Same mechanism though - a text item's colour
    is fixed in the dashboard model, so the choice is overlapping layers.
    """
    prop = "[AsDriven." + tone_property + "]"
    variants = [
        ("Known", TEXT, prop + " == 'known'"),
        ("Unknown", MUTED, prop + " != 'known'"),
    ]
    return [
        factory.layer(
            prefix + suffix,
            [factory.text(prefix + suffix + "Text", "", left, top, width, height, size,
                          color, expression=expression)],
            visible_expression=visible,
        )
        for suffix, color, visible in variants
    ]


def _tone_text(
    factory: ItemFactory,
    prefix: str,
    tone_property: str,
    text: str,
    left: float,
    top: float,
    width: float,
    height: float,
    size: float,
    *,
    expression: str,
    rotation: float = 0,
    alignment: int | None = None,
) -> list[dict[str, Any]]:
    """The same trick for text colour."""
    prop = "[AsDriven." + tone_property + "]"
    # Optional is a settled answer and reads in ordinary text; only a genuinely
    # unestablished value is greyed, so grey always means "not known".
    variants = [
        ("You", ORANGE, prop + " == 'you'"),
        ("Car", GREEN, prop + " == 'car'"),
        ("Optional", TEXT, prop + " == 'optional'"),
        ("Unknown", MUTED,
         prop + " != 'you' && " + prop + " != 'car' && " + prop + " != 'optional'"),
    ]
    return [
        factory.layer(
            prefix + suffix,
            [factory.text(prefix + suffix + "Text", text, left, top, width, height, size,
                          color, expression=expression, font_weight="Bold",
                          horizontal_alignment=(
                              alignment if alignment is not None
                              else (1 if rotation else 0)),
                          rotation=rotation)],
            visible_expression=visible,
        )
        for suffix, color, visible in variants
    ]


def _rail(
    factory: ItemFactory,
    name: str,
    label: str,
    left: float,
    top: float,
    height: float,
    *,
    width: float,
    color: str,
    fill: str,
    size: float,
) -> list[dict[str, Any]]:
    """A band's vertical spine. The label reads bottom to top beside the cells."""
    return [
        factory.rectangle(name + "Fill", left, top, width, height, fill),
        factory.text(
            name + "Label", label,
            left + width / 2 - height / 2, top + height / 2 - width / 2,
            height, width, size, color,
            horizontal_alignment=1, font_weight="Bold", rotation=270,
        ),
    ]


def _fit_band(
    factory: ItemFactory,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    rail_width: float,
    rail_size: float,
    head_size: float,
    sub_size: float,
    icon_size: float,
) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = [
        factory.rectangle("FitBand", left, top, width, height, BAND_PANEL, radius=7,
                          border_color=SLATE, border=1),
    ]
    children.extend(_rail(factory, "FitRail", "FIT", left + 1, top + 1, height - 2,
                          width=rail_width, color=ACCENT, fill=RAIL_FIT, size=rail_size))
    cell_left = left + rail_width + 1
    cell_width = (width - rail_width - 2) / 2
    icon_top = top + (height - icon_size) / 2
    text_left = cell_left + icon_size + 22
    text_width = cell_width - icon_size - 30
    children.extend(_wheel_icon(factory, "FitWheel", cell_left + 14, icon_top, icon_size / 46))
    children.extend([
        factory.text("FitWheelHead", "Rim", text_left, top + height / 2 - head_size - 3,
                     text_width, head_size + 6, head_size, WHITE,
                     expression="[AsDriven.WheelRimLabel]", font_weight="Bold"),
    ])
    # Whether the rim carries a display or shift lights does not follow from its
    # shape - GT / Formula rims split almost evenly - so this line is the only
    # place a driver learns it, and greying it made a known fact look like a gap.
    # Grey now means the same thing here as everywhere else on the card: no
    # evidence. A rim that plainly has neither reads as the settled answer it is.
    children.extend(
        _known_text(factory, "FitWheelSub", "WheelFeatureTone", text_left,
                    top + height / 2 + 2, text_width, sub_size + 6, sub_size,
                    expression="[AsDriven.WheelFeatureLabel]"))
    children.extend([
        factory.rectangle("FitDivider", cell_left + cell_width, top + 8, 1, height - 16, SLATE),
    ])
    second_left = cell_left + cell_width
    second_text = second_left + icon_size + 22
    children.extend(_shift_icon(factory, "FitShift", second_left + 14, icon_top, icon_size / 46))
    children.extend([
        factory.text("FitShiftHead", "Shifter", second_text, top + height / 2 - head_size - 3,
                     text_width, head_size + 6, head_size, WHITE,
                     expression="[AsDriven.ShifterLabel]", font_weight="Bold"),
        factory.text("FitShiftSub", "", second_text, top + height / 2 + 2,
                     text_width, sub_size + 6, sub_size, MUTED,
                     expression="[AsDriven.ShifterGateLabel]"),
        _differs_marker(factory, "FitShiftDiffers", "ShifterDiffers",
                        second_text, top + height - 21, text_width, sub_size - 1),
        _differs_marker(factory, "FitWheelDiffers", "WheelDiffers",
                        text_left, top + height - 21, text_width, sub_size - 1),
    ])
    return children


def _use_band(
    factory: ItemFactory,
    left: float,
    top: float,
    width: float,
    height: float,
    *,
    rail_width: float,
    rail_size: float,
    head_size: float,
    value_size: float,
) -> list[dict[str, Any]]:
    children: list[dict[str, Any]] = [
        factory.rectangle("UseBand", left, top, width, height, BAND_PANEL, radius=7,
                          border_color=SLATE, border=1),
    ]
    # The rail states the band's answer; each cell then states its own, so a
    # cell that disagrees is never overpainted by the band.
    children.extend(_tone_layers(
        factory, "UseRail", "UseBandTone", left + 1, top + 1, rail_width, height - 2,
        you=RAIL_YOU, car=RAIL_CAR, unknown=RAIL_FIT))
    children.extend(_tone_text(
        factory, "UseRailLabel", "UseBandTone", "USE",
        left + 1 + rail_width / 2 - (height - 2) / 2,
        top + 1 + (height - 2) / 2 - rail_width / 2,
        height - 2, rail_width, rail_size, expression="'USE'", rotation=270))
    cell_left = left + rail_width + 1
    cell_width = (width - rail_width - 2) / 3
    moments = (
        ("Launch", "LaunchTone", "[AsDriven.LaunchLabel]", "[AsDriven.LaunchDetailLabel]"),
        ("Upshift", "UpshiftTone", "[AsDriven.UpshiftLabel]", "[AsDriven.UpshiftClutchLabel]"),
        ("Downshift", "DownshiftTone", "[AsDriven.DownshiftLabel]",
         "[AsDriven.DownshiftClutchLabel]"),
    )
    for index, (title, tone, value, detail) in enumerate(moments):
        x = cell_left + cell_width * index
        children.extend(_tone_layers(
            factory, "UseCell" + title, tone, x + 1, top + 2, cell_width - 2, height - 4,
            you=CELL_YOU, car=CELL_CAR, unknown=TRANSPARENT))
        if index:
            children.append(
                factory.rectangle("UseDivider" + title, x, top + 8, 1, height - 16, SLATE))
        children.extend(_tone_text(
            factory, "UseHead" + title, tone, title,
            x + 14, top + 10, cell_width - 60, head_size + 6,
            head_size, expression="'" + title + "'"))
        children.append(
            factory.text("UseValue" + title, "", x + 14, top + head_size + 16,
                         cell_width - 24, value_size + 6, value_size, TEXT,
                         expression=value))
        # Every running shift states its clutch, even when the answer is no.
        # Silence there reads as "not checked", which is a different fact.
        children.append(
            factory.text("UseClutch" + title, "", x + 14, top + head_size + value_size + 21,
                         cell_width - 24, value_size + 5, value_size - 1.5, MUTED,
                         expression=detail))
        children.append(_differs_marker(
            factory, "UseDiffers" + title, title + "Differs",
            x + 14, top + head_size + value_size * 2 + 25, cell_width - 24, value_size - 2))
    return children


def _differs_marker(
    factory: ItemFactory,
    name: str,
    flag_property: str,
    left: float,
    top: float,
    width: float,
    size: float,
) -> dict[str, Any]:
    """Explains whether effective simulator guidance departs or fills a gap.

    The card shows effective behaviour. A known real-car value that changes in
    the simulator is a departure; an observed simulator value over an unknown
    real-car baseline is useful guidance, but cannot be called a disagreement.
    """
    return factory.layer(
        name,
        [
            factory.layer(
                name + "Departure",
                [factory.text(name + "Text", "* not as the real car", left, top,
                              width, size + 6, size, ACCENT,
                              expression="'* not as the real car'")],
                visible_expression="[AsDriven." + flag_property + "]",
            ),
            factory.layer(
                name + "Unestablished",
                [factory.text(name + "UnestablishedText", "* real car not established",
                              left, top, width, size + 6, size, MUTED,
                              expression="'* real car not established'")],
                visible_expression="[AsDriven."
                                   + flag_property.replace("Differs", "Unestablished")
                                   + "] && ![AsDriven." + flag_property + "]",
            ),
        ],
    )


NOTE_LINES = 5
NOTE_PADDING = 7


def _driver_note(
    factory: ItemFactory,
    left: float,
    top: float,
    width: float,
    *,
    size: float,
    line_height: float,
    prefix: str,
) -> list[dict[str, Any]]:
    """The one place the card can say why a car behaves as it does.

    Dashboard text items do not wrap, so the summary arrives pre-broken as three
    line properties and is drawn one item per line. The whole group hides when
    the record carries no summary, so a card without one ends after the Use band
    rather than reserving an empty panel.
    """
    # The panel is sized from its own line metrics rather than by hand, so a
    # line can never end up drawn past the edge of the box holding it.
    height = NOTE_PADDING * 2 + line_height * NOTE_LINES
    present = "[AsDriven.DriverSummary] != ''"
    children = [
        factory.rectangle("NotePanel", left, top, width, height, NOTE_PANEL, radius=6),
        factory.rectangle("NoteRail", left, top, 2, height, ACCENT),
        factory.image("NoteIcon", "note-info", left + 13, top + NOTE_PADDING + 2, 16, 16),
    ]
    for index in range(NOTE_LINES):
        children.append(factory.text(
            "NoteLine" + str(index + 1), "",
            left + 38, top + NOTE_PADDING + line_height * index,
            width - 50, line_height, size, TEXT,
            expression="[AsDriven." + prefix + "Line" + str(index + 1) + "]"))
    return [factory.layer("DriverNote", children, visible_expression=present)]


def _card_header(
    factory: ItemFactory,
    *,
    left: float,
    top: float,
    mark: float,
    name_size: float,
    class_size: float,
    match_size: float,
    width: float,
    show_class: bool = True,
) -> list[dict[str, Any]]:
    text_left = left + mark + 14
    match_width = 150 if match_size >= 12 else 118
    match_left = left + width - match_width
    children = [
        factory.image("Mark", "brand-mark", left, top + 1, mark, mark),
        factory.text("Title", "Current car", text_left, top - 1,
                     match_left - text_left - 10, name_size + 9, name_size, WHITE,
                     expression="[AsDriven.OverlayCarNameDetailed]", font_weight="Bold"),
    ]
    if show_class:
        children.append(
            factory.text("CarClass", "", text_left, top + name_size + 6,
                         match_left - text_left - 10, class_size + 6, class_size, MUTED,
                         expression="[AsDriven.OverlayCarClassDetailed]"))
    children.extend([
        factory.ellipse("MatchDot", match_left, top + mark / 2 - 4, 8, 8, GREEN,
                        thickness=4, fill=GREEN),
        factory.text("Match", "Telemetry matched", match_left + 13, top + mark / 2 - match_size,
                     match_width - 13, match_size + 8, match_size, GREEN,
                     expression="if([AsDriven.MatchKind] == 'preview', 'Preview - not live', "
                                "'Telemetry matched')",
                     font_weight="Bold"),
    ])
    return children


def _matched_detailed(factory: ItemFactory) -> dict[str, Any]:
    left = 22
    width = factory.width - 2 * left
    children = _card_header(factory, left=left, top=16, mark=36, name_size=22,
                            class_size=12, match_size=13, width=width)
    children.append(factory.rectangle("HeaderRule", left, 68, width, 1, SLATE))
    children.extend(_fit_band(factory, left, 80, width, 82, rail_width=30, rail_size=13,
                              head_size=16, sub_size=12.5, icon_size=42))
    children.extend(_use_band(factory, left, 166, width, 92, rail_width=30, rail_size=13,
                              head_size=15, value_size=13))
    children.extend(_driver_note(factory, left, 264, width, size=12.5,
                                 line_height=17, prefix="DriverSummary"))
    children.extend([
        _preview_badge(factory, factory.width - left - 150, 14, 150, 30),
        factory.rectangle("FooterRule", left, 371, width, 1, SLATE),
        factory.text("Evidence", "", left, 377, width - 180, 19, 11.5, MUTED,
                     expression="[AsDriven.SimulatorLabel] + ' ' + if([AsDriven.VerifiedGameVersion] == '', 'unknown', "
                                "[AsDriven.VerifiedGameVersion]) + ' - Confidence: ' + "
                                + _confidence_value_expression()),
        factory.text("Dataset", "", left + width - 180, 377, 180, 19, 11.5, MUTED,
                     expression="'Dataset ' + [AsDriven.DatasetVersion]",
                     horizontal_alignment=2),
    ])
    return factory.layer("MatchedState", children, visible_expression="[AsDriven.HasMatch]")


def _matched_compact(factory: ItemFactory) -> dict[str, Any]:
    left = 16
    width = factory.width - 2 * left
    children = _card_header(factory, left=left, top=12, mark=28, name_size=17,
                            class_size=10.5, match_size=11, width=width)
    children.append(factory.rectangle("HeaderRule", left, 55, width, 1, SLATE))
    children.extend(_fit_band(factory, left, 60, width, 58, rail_width=24, rail_size=11,
                              head_size=13, sub_size=10.5, icon_size=30))
    children.extend(_use_band(factory, left, 124, width, 78, rail_width=24, rail_size=11,
                              head_size=12, value_size=11))
    children.extend(_driver_note(factory, left, 206, width, size=11,
                                 line_height=15, prefix="DriverSummaryCompact"))
    children.extend([
        _preview_badge(factory, factory.width - left - 118, 10, 118, 26, compact=True),
        factory.rectangle("FooterRule", left, 303, width, 1, SLATE),
        factory.text("Evidence", "", left, 309, width - 150, 18, 10, MUTED,
                     expression="[AsDriven.SimulatorLabel] + ' ' + if([AsDriven.VerifiedGameVersion] == '', 'unknown', "
                                "[AsDriven.VerifiedGameVersion]) + ' - ' + "
                                + _confidence_value_expression()),
        factory.text("Dataset", "", left + width - 150, 309, 150, 18, 10, MUTED,
                     expression="'Dataset ' + [AsDriven.DatasetVersion]",
                     horizontal_alignment=2),
    ])
    return factory.layer("MatchedState", children, visible_expression="[AsDriven.HasMatch]")


def _empty_state(factory: ItemFactory, unmatched: bool, compact: bool) -> dict[str, Any]:
    accent = ORANGE if unmatched else ACCENT
    title_expression = (
        "if([AsDriven.RawCarIdentifier] == '', 'Unknown car', [AsDriven.RawCarIdentifier])"
        if unmatched
        else "if([AsDriven.MatchStatus] == 'database-error', 'Database unavailable', if([AsDriven.MatchStatus] == 'runtime-error', 'Plugin runtime error', 'Waiting for a car'))"
    )
    left = 16 if compact else 28
    children = _header(factory, compact=compact)
    children.extend([
        factory.text("StateEyebrow", "CONTRIBUTION NEEDED" if unmatched else "AUTHENTIC SETUP", 60 if compact else 92, 20 if compact else 24, factory.width - 100, 22, 11 if compact else 13, accent, font_weight="Bold"),
        factory.text("StateTitle", "Unmapped car" if unmatched else "Waiting for a car", 60 if compact else 92, 42 if compact else 52, factory.width - 110, 38, 21 if compact else 30, WHITE, expression=title_expression, font_weight="Bold"),
        factory.rectangle("StateRule", left, 82 if compact else 108, factory.width - 2 * left, 2, SLATE),
        # Pre-broken, because a dashboard text item does not wrap: the waiting
        # line ran off the card and ended mid-word at "gui". One item per line,
        # the same way the note panel draws a summary.
        *[
            factory.text(
                "StateBody" + str(index + 1), line,
                left, (105 if compact else 140) + (20 if compact else 28) * index,
                factory.width - 2 * left, 26 if compact else 34,
                16 if compact else 22, TEXT, font_weight="Bold",
            )
            for index, line in enumerate(
                ["No curated record exists", "for this exact identity."]
                if unmatched
                else ["Start a supported simulator session",
                      "to see authentic controls guidance."]
            )
        ],
        factory.text("StateSafety", "No hardware or technique values have been assumed." if unmatched else "Dataset ready • waiting for telemetry", left, factory.height - 50, factory.width - 2 * left, 28, 12 if compact else 15, MUTED),
    ])
    if unmatched:
        cta_top = 158 if compact else 205
        hint_top = 196 if compact else 247
        children.extend([
            factory.rectangle(
                "ContributionCtaPanel",
                left,
                cta_top,
                factory.width - 2 * left,
                31,
                "#FF10352C",
                radius=7,
                border_color=GREEN,
                border=2,
            ),
            factory.text(
                "ContributionCta",
                "CONTRIBUTE IN AS DRIVEN",
                left + 10,
                cta_top + 2,
                factory.width - 2 * left - 20,
                27,
                11 if compact else 13,
                GREEN,
                horizontal_alignment=1,
                font_weight="Bold",
            ),
            factory.text(
                "ContributionHint",
                "Open the As Driven page in SimHub and choose Contribute this car.",
                left,
                hint_top,
                factory.width - 2 * left,
                40,
                10 if compact else 12,
                MUTED,
                font_weight="Bold",
            ),
        ])
    expression = "![AsDriven.HasMatch] && [AsDriven.MatchStatus] == 'unmatched'" if unmatched else "![AsDriven.HasMatch] && [AsDriven.MatchStatus] != 'unmatched'"
    return factory.layer("UnmatchedState" if unmatched else "WaitingState", children, visible_expression=expression)


def _verification_drive(factory: ItemFactory) -> list[dict[str, Any]]:
    progress_expression = (
        "if([AsDriven.VerificationDriveStepNumber] == 0, 'READY', "
        "'STEP ' + [AsDriven.VerificationDriveStepNumber] + "
        "' / ' + [AsDriven.VerificationDriveStepCount])"
    )
    pending_status = factory.layer(
        "PendingStatus",
        [factory.text("PendingStatusText", "Waiting for telemetry", 34, 146, 628, 28, 12, WHITE, expression="[AsDriven.VerificationDriveStatus]")],
        visible_expression="![AsDriven.VerificationDriveResultReady]",
    )
    successful_status = factory.layer(
        "SuccessfulStatus",
        [
            factory.text("SuccessBadge", "✓ CAPTURED", 34, 146, 126, 28, 12, GREEN, font_weight="Bold"),
            factory.text("SuccessSummary", "Result captured", 164, 146, 498, 28, 13, WHITE, expression="[AsDriven.VerificationDriveResult]", font_weight="Bold"),
        ],
        visible_expression="[AsDriven.VerificationDriveResultReady] && [AsDriven.VerificationDriveResultSuccessful]",
    )
    # A negative outcome is still a captured result: the drive sets the result as
    # ready either way, and a stalled move-off is the finding that the car needs
    # the clutch. Badging it REVIEW read as a fault and hid that anything had been
    # captured at all, so both states say CAPTURED and only the colour differs.
    review_status = factory.layer(
        "ReviewStatus",
        [
            factory.text("ReviewBadge", "✓ CAPTURED", 34, 146, 126, 28, 12, ORANGE, font_weight="Bold"),
            factory.text("ReviewSummary", "Result captured", 164, 146, 498, 28, 13, WHITE, expression="[AsDriven.VerificationDriveResult]", font_weight="Bold"),
        ],
        visible_expression="[AsDriven.VerificationDriveResultReady] && ![AsDriven.VerificationDriveResultSuccessful]",
    )
    # Before a result exists the driver is still performing the manoeuvre, so the
    # bottom row shows live telemetry with the verbs muted for reference. Once a
    # result is captured the telemetry stops mattering and a decision starts, so
    # the whole row becomes one full-width sentence. Abbreviations like "RETRY
    # redo" did not fit in the 302-pixel corner and were not readable; at 648
    # pixels each verb can say what it actually does.
    controls_idle = factory.layer(
        "ControlsIdle",
        [
            factory.text("LiveValues", "Waiting for live telemetry", 24, 181, 350, 23, 11, MUTED, expression="[AsDriven.VerificationDriveLiveValues]"),
            factory.text("ControlsIdleText", "NEXT / ACCEPT   •   RETRY   •   SKIP   •   CANCEL", 370, 181, 302, 23, 10, MUTED, horizontal_alignment=2, font_weight="Bold"),
        ],
        visible_expression="![AsDriven.VerificationDriveResultReady]",
    )
    controls_ready = factory.layer(
        "ControlsReady",
        [factory.text("ControlsReadyText", "NEXT to accept this result   •   RETRY to drive this test again   •   SKIP to answer it in the form", 24, 181, 648, 23, 11, ACCENT, font_weight="Bold")],
        visible_expression="[AsDriven.VerificationDriveResultReady]",
    )
    return [
        factory.rectangle("Card", 4, 4, 692, 212, CARD, radius=18, border_color=SLATE, border=2),
        factory.rectangle("Accent", 20, 4, 660, 5, ACCENT, radius=3),
        factory.text("Eyebrow", "GUIDED VERIFICATION", 24, 18, 250, 24, 13, ACCENT, font_weight="Bold"),
        factory.text("Progress", "STEP 1 / 6", 520, 18, 152, 24, 13, MUTED, expression=progress_expression, horizontal_alignment=2, font_weight="Bold"),
        factory.rectangle("HeaderRule", 24, 48, 648, 1, SLATE),
        factory.text("Title", "Verification step", 24, 56, 648, 34, 24, WHITE, expression="[AsDriven.VerificationDriveTitle]", font_weight="Bold"),
        factory.text("PromptLine1", "Follow the current test prompt.", 24, 91, 648, 22, 14, TEXT, expression="[AsDriven.VerificationDrivePromptLine1]", font_weight="Bold"),
        factory.text("PromptLine2", "Then continue to the next step.", 24, 115, 648, 22, 14, TEXT, expression="[AsDriven.VerificationDrivePromptLine2]", font_weight="Bold"),
        factory.rectangle("StatusPanel", 24, 143, 648, 34, "#FF102333", radius=7, border_color=SLATE, border=1),
        pending_status,
        successful_status,
        review_status,
        controls_idle,
        controls_ready,
    ]


def _template_spec(overlay: bool, variant: str) -> TemplateSpec:
    key = variant if overlay else "display"
    for spec in TEMPLATES:
        if spec.key == key:
            return spec
    raise ValueError("Unsupported popup variant: " + variant)


def build_dashboard(*, overlay: bool, variant: str = "detailed") -> dict[str, Any]:
    spec = _template_spec(overlay, variant)
    factory = ItemFactory(spec.width, spec.height)
    if spec.key == "verification":
        children = _verification_drive(factory)
    else:
        children = _frame(factory)
        if spec.key == "compact":
            children.append(_matched_compact(factory))
        else:
            children.append(_matched_detailed(factory))
        children.extend([
            _empty_state(factory, unmatched=True, compact=spec.key == "compact"),
            _empty_state(factory, unmatched=False, compact=spec.key == "compact"),
        ])
    visible_expression = None
    if overlay:
        property_suffix = {
            "detailed": "Detailed",
            "compact": "Compact",
            "verification": "Verification",
        }[spec.key]
        visible_expression = (
            "[AsDriven.VerificationDriveVisible]"
            if spec.key == "verification"
            else "[AsDriven.Popup" + property_suffix + "Visible]"
        )
    outer = factory.layer(
        "VerificationCard" if spec.key == "verification" else "PreflightCard",
        children,
        visible_expression=visible_expression,
    )
    dashboard_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "as-driven/" + spec.key + "/dashboard"))
    screen_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "as-driven/" + spec.key + "/screen"))
    metadata = build_metadata(overlay=overlay, variant=variant)
    return {
        "Version": 2,
        "Id": dashboard_id,
        "BaseHeight": spec.height,
        "BaseWidth": spec.width,
        "BackgroundColor": "#00000000",
        "Screens": [{
            "Name": "Preflight",
            "InGameScreen": True,
            "IdleScreen": True,
            "PitScreen": False,
            "ScreenId": screen_id,
            "IsForegroundLayer": False,
            "IsBackgroundLayer": False,
            "BackgroundColor": "#00000000",
            "Items": [outer],
            "RenderingSkip": 0,
            "CanOpen": False,
            "IsFreezed": False,
        }],
        "SnapToGrid": True,
        "HideLabels": False,
        "ShowForeground": True,
        "ForegroundOpacity": 50.0,
        "ShowBackground": True,
        "BackgroundOpacity": 50.0,
        "ShowBoundingRectangles": True,
        "GridSize": 8,
        "Images": _image_metadata(),
        "Metadata": metadata,
        "ShowOnScreenControls": False,
        "IsOverlay": overlay,
        "EnableClickThroughOverlay": overlay,
        "EnableOnDashboardMessaging": True,
    }


def build_metadata(*, overlay: bool, variant: str = "detailed") -> dict[str, Any]:
    spec = _template_spec(overlay, variant)
    size_name = spec.key.title() if spec.key != "display" else "Detailed"
    return {
        "Category": "As Driven",
        "Title": spec.stem,
        "Description": (
            "In-simulator prompts for the guided control verification drive."
            if spec.key == "verification"
            else size_name + " car-change popup with packaged control and technique icons."
            if overlay
            else "Persistent detailed display for authentic controls guidance."
        ),
        "Author": "Jason Kinslow",
        "ScreenCount": 1.0,
        "InGameScreensIndexs": [0],
        "IdleScreensIndexs": [0],
        "MainPreviewIndex": 0,
        "IsOverlay": overlay,
        "Width": float(spec.width),
        "Height": float(spec.height),
        "OverlaySizeWarning": False,
        "MetadataVersion": 2.0,
        "EnableOnDashboardMessaging": True,
        "PitScreensIndexs": [],
    }


def write_dashboards(output_directory: Path) -> list[Path]:
    output_directory.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    for spec in TEMPLATES:
        variant = "detailed" if not spec.overlay else spec.key
        dashboard = build_dashboard(overlay=spec.overlay, variant=variant)
        template_directory = output_directory / spec.stem
        template_directory.mkdir(parents=True, exist_ok=True)
        dashboard_path = template_directory / f"{spec.stem}.djson"
        metadata_path = template_directory / f"{spec.stem}.djson.metadata"
        resources_path = template_directory / f"{spec.stem}.djson.ressources"
        dashboard_path.write_text(json.dumps(dashboard, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        metadata_path.write_text(json.dumps(build_metadata(overlay=spec.overlay, variant=variant), indent=2) + "\n", encoding="utf-8")
        with zipfile.ZipFile(resources_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            for name, data in sorted(_icon_assets().items()):
                info = zipfile.ZipInfo(f"{name}.png", date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, data)
        written.extend([dashboard_path, metadata_path, resources_path])
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate As Driven SimHub Dash Studio artifacts.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for path in write_dashboards(args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

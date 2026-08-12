from __future__ import annotations

import argparse
import hashlib
import json
import uuid
import zipfile
from functools import lru_cache
from pathlib import Path
from typing import Any, Callable, NamedTuple

from icons import generate_icons


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
    TemplateSpec("detailed", "Authentic Controls Preflight Overlay", 840, 360),
    TemplateSpec("compact", "Authentic Controls Preflight Compact", 520, 300),
    TemplateSpec("glance", "Authentic Controls Preflight Glance", 320, 120),
    TemplateSpec("verification", "Authentic Controls Verification Drive", 700, 220),
    TemplateSpec("display", "Authentic Controls Preflight Display", 900, 360, False),
)


@lru_cache(maxsize=1)
def _icon_assets() -> dict[str, bytes]:
    return generate_icons(size=ICON_SIZE)


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


def _line(
    factory: ItemFactory,
    name: str,
    x: float,
    y: float,
    length: float,
    thickness: float,
    rotation: float = 0,
    color: str = WHITE,
) -> dict[str, Any]:
    return factory.rectangle(
        name, x, y, length, thickness, color, radius=max(1, int(thickness / 2)), rotation=rotation
    )


def _wheel_icon(factory: ItemFactory, prefix: str, x: float, y: float, scale: float) -> list[dict[str, Any]]:
    size = 46 * scale
    prop = "[AuthenticControls.WheelRimShape]"
    variants = (
        ("Round", "wheel-round", prop + " == 'round'"),
        ("DShape", "wheel-d-shaped", prop + " == 'd-shaped'"),
        ("GTStyle", "wheel-gt-style", prop + " == 'gt-style'"),
        ("Prototype", "wheel-prototype", prop + " == 'prototype'"),
        ("Formula", "wheel-formula", prop + " == 'formula'"),
        ("Yoke", "wheel-yoke", prop + " == 'yoke'"),
        (
            "Unknown",
            "wheel-unknown",
            prop + " != 'round' && " + prop + " != 'd-shaped' && "
            + prop + " != 'gt-style' && " + prop + " != 'prototype' && "
            + prop + " != 'formula' && " + prop + " != 'yoke'",
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
    prop = "[AuthenticControls.ShiftActuation]"
    size = 46 * scale
    variants = (
        ("HPattern", "shift-h-pattern", prop + " == 'h-pattern' && [AuthenticControls.ShiftPattern] != 'dogleg-h'"),
        ("DoglegH", "shift-dogleg-h", prop + " == 'h-pattern' && [AuthenticControls.ShiftPattern] == 'dogleg-h'"),
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


def _automation_icon(
    factory: ItemFactory,
    prefix: str,
    x: float,
    y: float,
    scale: float,
    property_name: str,
    kind: str,
) -> list[dict[str, Any]]:
    prop = "[AuthenticControls." + property_name + "]"
    size = 46 * scale
    if kind == "cut":
        variants = (
            ("Yes", "cut-auto", prop + " == 'yes'"),
            ("No", "lift-required", prop + " == 'no'"),
            ("Unknown", "cut-unknown", prop + " != 'yes' && " + prop + " != 'no'"),
        )
    else:
        variants = (
            ("Yes", "blip-auto", prop + " == 'yes'"),
            ("No", "blip-manual", prop + " == 'no'"),
            ("Unknown", "blip-unknown", prop + " != 'yes' && " + prop + " != 'no'"),
        )
    return [
        factory.layer(
            prefix + suffix,
            [factory.image(prefix + suffix + "Bitmap", asset, x, y, size, size)],
            visible_expression=expression,
        )
        for suffix, asset, expression in variants
    ]


def _rail_item(
    factory: ItemFactory,
    name: str,
    x: float,
    width: float,
    icon_top: float,
    icon_size: float,
    label_top: float,
    icon_builder: Callable[[ItemFactory, str, float, float, float], list[dict[str, Any]]],
    label: str,
    value_expression: str,
    *,
    label_size: float,
    value_size: float,
    show_value: bool = True,
) -> list[dict[str, Any]]:
    scale = icon_size / 46
    icon_x = x + (width - icon_size) / 2
    children = icon_builder(factory, name + "Icon", icon_x, icon_top, scale)
    children.append(factory.text(name + "Label", label, x + 4, label_top, width - 8, 18, label_size, ACCENT, horizontal_alignment=1, font_weight="Bold"))
    if show_value:
        children.append(factory.text(name + "Value", "Unknown", x + 5, label_top + 18, width - 10, 28, value_size, WHITE, expression=value_expression, horizontal_alignment=1, font_weight="Bold"))
    return children


def _group_heading(
    factory: ItemFactory,
    name: str,
    text: str,
    x: float,
    y: float,
    width: float,
    font_size: float,
) -> dict[str, Any]:
    return factory.text(
        name,
        text,
        x,
        y,
        width,
        18,
        font_size,
        ACCENT,
        horizontal_alignment=1,
        font_weight="Bold",
    )


def _separator(
    factory: ItemFactory,
    name: str,
    x: float,
    top: float,
    height: float,
    *,
    group: bool = False,
) -> dict[str, Any]:
    return factory.rectangle(name, x, top, 2 if group else 1, height, ACCENT if group else SLATE)


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


def _wheel_value_expression() -> str:
    prop = "[AuthenticControls.WheelRimShape]"
    return (
        f"if({prop} == 'round', 'Round', "
        f"if({prop} == 'd-shaped', 'D-shaped', "
        f"if({prop} == 'gt-style', 'GT-style', "
        f"if({prop} == 'prototype', 'Prototype', "
        f"if({prop} == 'formula', 'Formula', "
        f"if({prop} == 'yoke', 'Yoke', 'Unknown'))))))"
    )


def _shift_value_expression() -> str:
    actuation = "[AuthenticControls.ShiftActuation]"
    pattern = "[AuthenticControls.ShiftPattern]"
    return (
        f"if({pattern} == 'dogleg-h', 'Dogleg H-pattern', "
        f"if({actuation} == 'h-pattern', 'H-pattern', "
        f"if({actuation} == 'sequential-stick', 'Sequential stick', "
        f"if({actuation} == 'sequential-paddles', 'Sequential paddles', "
        f"if({actuation} == 'automatic-lever', 'Automatic lever', "
        f"if({actuation} == 'direct-selection', 'Direct selection', 'Unknown'))))))"
    )


def _automation_value_expression(property_name: str, action: str) -> str:
    prop = "[AuthenticControls." + property_name + "]"
    return (
        f"if({prop} == 'yes', 'Automatic throttle {action}', "
        f"if({prop} == 'no', 'Manual {action}', 'Unknown'))"
    )


def _upshift_value_expression() -> str:
    prop = "[AuthenticControls.ShiftCut]"
    return (
        f"if({prop} == 'yes', 'Automatic throttle cut', "
        f"if({prop} == 'no', 'Lift throttle', 'Unknown'))"
    )


def _match_value_expression(*, include_match: bool) -> str:
    prop = "[AuthenticControls.MatchKind]"
    suffix = " match" if include_match else ""
    return (
        f"if({prop} == 'preview', 'Preview', "
        f"if({prop} == 'telemetry-name', 'Telemetry name{suffix}', "
        f"if({prop} == 'display-name', 'Display name{suffix}', "
        f"if({prop} == 'internal-id', 'Internal ID{suffix}', "
        f"if({prop} == 'car-path', 'Car path{suffix}', "
        f"if({prop} == 'class-id', 'Class ID{suffix}', "
        f"if({prop} == 'alias', 'Alias{suffix}', 'Matched')))))))"
    )


def _confidence_value_expression() -> str:
    prop = "[AuthenticControls.Confidence]"
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
            factory.text("PreviewBadgeText", "PREVIEW — NOT LIVE", left, top, width, height, 10.5, "#FF07121C", horizontal_alignment=1, font_weight="Bold"),
        ]
    return factory.layer(
        "PreviewBadge",
        [factory.rectangle("PreviewBadgeBackground", left, top, width, height, ACCENT, radius=6)] + text_items,
        visible_expression="[AuthenticControls.MatchKind] == 'preview'",
    )


def _matched_detailed(factory: ItemFactory) -> dict[str, Any]:
    content_left = 28
    content_width = factory.width - 2 * content_left
    column_width = content_width / 4
    columns = [content_left + column_width * index for index in range(4)]
    match_width = 176
    match_left = factory.width - content_left - match_width
    title_left = 90
    title_width = match_left - title_left - 12
    children = _header(factory)
    children.extend([
        factory.text("Title", "Current car", title_left, 19, title_width, 29, 21.5, WHITE, expression="[AuthenticControls.OverlayCarNameDetailed]", font_weight="Bold"),
        factory.text("CarClass", "", title_left, 48, title_width, 20, 12, MUTED, expression="[AuthenticControls.OverlayCarClassDetailed]", font_weight="Bold"),
        factory.text("Match", "Matched", match_left, 27, match_width, 22, 11, GREEN, expression="if([AuthenticControls.MatchKind] == 'preview', '', '✓  ' + " + _match_value_expression(include_match=True) + ")", horizontal_alignment=2, font_weight="Bold"),
        _preview_badge(factory, match_left, 22, match_width, 30),
        factory.rectangle("Rule", content_left, 78, content_width, 2, SLATE),
        factory.rectangle("PhysicalControlsGroup", content_left, 86, column_width * 2 - 4, 164, GROUP_PANEL, radius=7, border_color=SLATE, border=1),
        factory.rectangle("ShiftingTechniqueGroup", columns[2] + 4, 86, column_width * 2 - 4, 164, GROUP_PANEL, radius=7, border_color=SLATE, border=1),
        _group_heading(factory, "PhysicalControlsHeading", "PHYSICAL CONTROLS", columns[0], 90, column_width * 2 - 4, 11),
        _group_heading(factory, "ShiftingTechniqueHeading", "SHIFTING TECHNIQUE", columns[2] + 4, 90, column_width * 2 - 4, 11),
        _separator(factory, "WheelShiftSeparator", columns[1], 116, 132),
        _separator(factory, "UpshiftDownshiftSeparator", columns[3], 116, 132),
    ])
    wheel_value = _wheel_value_expression()
    shift_value = _shift_value_expression()
    cut_value = _upshift_value_expression()
    blip_value = _automation_value_expression("AutoBlip", "blip")
    children.extend(_rail_item(factory, "Wheel", columns[0], column_width, 116, 84, 202, _wheel_icon, "WHEEL", wheel_value, label_size=9.5, value_size=11))
    children.extend(_rail_item(factory, "Shift", columns[1], column_width, 116, 84, 202, _shift_icon, "SHIFT", shift_value, label_size=9.5, value_size=11))
    children.extend(_rail_item(factory, "Cut", columns[2], column_width, 116, 84, 202, lambda f, p, x, y, s: _automation_icon(f, p, x, y, s, "ShiftCut", "cut"), "UPSHIFT", cut_value, label_size=9.5, value_size=11))
    children.extend(_rail_item(factory, "Blip", columns[3], column_width, 116, 84, 202, lambda f, p, x, y, s: _automation_icon(f, p, x, y, s, "AutoBlip", "blip"), "DOWNSHIFT", blip_value, label_size=9.5, value_size=11))
    evidence_expression = "'Verified for ' + if([AuthenticControls.RawGameName] == 'Automobilista2', 'AMS2', if([AuthenticControls.RawGameName] == '', 'Unknown simulator', [AuthenticControls.RawGameName])) + ' ' + if([AuthenticControls.VerifiedGameVersion] == '', 'Unknown', [AuthenticControls.VerifiedGameVersion]) + '  •  Confidence: ' + " + _confidence_value_expression()
    children.extend([
        factory.rectangle("TechniqueRule", content_left, 252, content_width, 1, SLATE),
        _group_heading(factory, "DrivingTechniqueHeading", "DRIVING TECHNIQUE", content_left, 258, content_width, 10),
        factory.text("TechniqueSummaryLine1", "Shifting technique", content_left + 10, 277, content_width - 20, 21, 13.5, TEXT, expression="[AuthenticControls.TechniqueSummaryLine1]"),
        factory.text("TechniqueSummaryLine2", "", content_left + 10, 298, content_width - 20, 21, 13.5, TEXT, expression="[AuthenticControls.TechniqueSummaryLine2]"),
        factory.rectangle("EvidenceRule", content_left, 327, content_width, 1, SLATE),
        factory.text("Evidence", "Evidence", content_left, 333, content_width - 206, 22, 10, MUTED, expression=evidence_expression),
        factory.text("Dataset", "Dataset", content_left + content_width - 188, 333, 188, 22, 10, MUTED, expression="'Dataset ' + [AuthenticControls.DatasetVersion]", horizontal_alignment=2),
    ])
    return factory.layer("MatchedState", children, visible_expression="[AuthenticControls.HasMatch]")


def _matched_compact(factory: ItemFactory) -> dict[str, Any]:
    children = _header(factory, compact=True)
    children.extend([
        factory.text("Title", "Current car", 68, 13, 310, 23, 17.5, WHITE, expression="[AuthenticControls.OverlayCarNameCompact]", font_weight="Bold"),
        factory.text("CarClass", "", 68, 37, 310, 14, 9.5, MUTED, expression="[AuthenticControls.OverlayCarClassCompact]", font_weight="Bold"),
        factory.text("Match", "✓", 422, 20, 78, 22, 11, GREEN, expression="if([AuthenticControls.MatchKind] == 'preview', '', '✓')", horizontal_alignment=2, font_weight="Bold"),
        _preview_badge(factory, 390, 15, 110, 30, compact=True),
        factory.rectangle("Rule", 16, 62, 488, 1, SLATE),
        factory.rectangle("PhysicalControlsGroup", 16, 68, 240, 139, GROUP_PANEL, radius=6, border_color=SLATE, border=1),
        factory.rectangle("ShiftingTechniqueGroup", 264, 68, 240, 139, GROUP_PANEL, radius=6, border_color=SLATE, border=1),
        _group_heading(factory, "PhysicalControlsHeading", "PHYSICAL CONTROLS", 16, 71, 240, 9),
        _group_heading(factory, "ShiftingTechniqueHeading", "SHIFTING TECHNIQUE", 264, 71, 240, 9),
        _separator(factory, "WheelShiftSeparator", 138, 87, 120),
        _separator(factory, "UpshiftDownshiftSeparator", 382, 87, 120),
    ])
    wheel_value = _wheel_value_expression()
    shift_value = _shift_value_expression()
    cut_value = _upshift_value_expression()
    blip_value = _automation_value_expression("AutoBlip", "blip")
    children.extend(_rail_item(factory, "Wheel", 16, 122, 88, 62, 153, _wheel_icon, "WHEEL", wheel_value, label_size=8.5, value_size=9.5))
    children.extend(_rail_item(factory, "Shift", 138, 122, 88, 62, 153, _shift_icon, "SHIFT", shift_value, label_size=8.5, value_size=9.5))
    children.extend(_rail_item(factory, "Cut", 260, 122, 88, 62, 153, lambda f, p, x, y, s: _automation_icon(f, p, x, y, s, "ShiftCut", "cut"), "UPSHIFT", cut_value, label_size=8.5, value_size=9.5))
    children.extend(_rail_item(factory, "Blip", 382, 122, 88, 62, 153, lambda f, p, x, y, s: _automation_icon(f, p, x, y, s, "AutoBlip", "blip"), "DOWNSHIFT", blip_value, label_size=8.5, value_size=9.5))
    evidence_expression = "'Verified ' + if([AuthenticControls.VerifiedGameVersion] == '', 'version unknown', [AuthenticControls.VerifiedGameVersion]) + '  •  Confidence: ' + " + _confidence_value_expression()
    children.extend([
        factory.rectangle("TechniqueRule", 16, 209, 488, 1, SLATE),
        _group_heading(factory, "DrivingTechniqueHeading", "DRIVING TECHNIQUE", 16, 214, 488, 8.5),
        factory.text("TechniqueSummaryLine1", "Shifting technique", 24, 231, 472, 17, 9.5, TEXT, expression="[AuthenticControls.TechniqueSummaryCompactLine1]"),
        factory.text("TechniqueSummaryLine2", "", 24, 248, 472, 17, 9.5, TEXT, expression="[AuthenticControls.TechniqueSummaryCompactLine2]"),
        factory.rectangle("EvidenceRule", 16, 270, 488, 1, SLATE),
        factory.text("Evidence", "Evidence", 16, 276, 360, 18, 8.5, MUTED, expression=evidence_expression),
        factory.text("Dataset", "Dataset", 380, 276, 124, 18, 8.5, MUTED, expression="'Dataset ' + [AuthenticControls.DatasetVersion]", horizontal_alignment=2),
    ])
    return factory.layer("MatchedState", children, visible_expression="[AuthenticControls.HasMatch]")


def _matched_glance(factory: ItemFactory) -> dict[str, Any]:
    children = [
        factory.image("Mark", "brand-mark", 12, 8, 30, 30),
        factory.text("Title", "Current car", 50, 8, 174, 24, 15, WHITE, expression="[AuthenticControls.OverlayCarNameGlance]", font_weight="Bold"),
        factory.text("Match", "✓", 278, 9, 26, 22, 12, GREEN, expression="if([AuthenticControls.MatchKind] == 'preview', '', '✓')", horizontal_alignment=1, font_weight="Bold"),
        _preview_badge(factory, 232, 6, 72, 30, compact=True),
        factory.rectangle("Rule", 12, 39, 292, 1, SLATE),
        factory.rectangle("PhysicalControlsGroup", 12, 41, 142, 69, GROUP_PANEL, radius=4, border_color=SLATE, border=1),
        factory.rectangle("ShiftingTechniqueGroup", 162, 41, 142, 69, GROUP_PANEL, radius=4, border_color=SLATE, border=1),
        _group_heading(factory, "PhysicalControlsHeading", "PHYSICAL CONTROLS", 12, 43, 142, 7),
        _group_heading(factory, "ShiftingTechniqueHeading", "SHIFTING TECHNIQUE", 162, 43, 142, 7),
        _separator(factory, "WheelShiftSeparator", 85, 54, 54),
        _separator(factory, "UpshiftDownshiftSeparator", 231, 54, 54),
    ]
    children.extend(_rail_item(factory, "Wheel", 12, 73, 54, 38, 94, _wheel_icon, "WHEEL", "''", label_size=7, value_size=7, show_value=False))
    children.extend(_rail_item(factory, "Shift", 85, 73, 54, 38, 94, _shift_icon, "SHIFT", "''", label_size=7, value_size=7, show_value=False))
    children.extend(_rail_item(factory, "Cut", 158, 73, 54, 38, 94, lambda f, p, x, y, s: _automation_icon(f, p, x, y, s, "ShiftCut", "cut"), "UPSHIFT", "''", label_size=7, value_size=7, show_value=False))
    children.extend(_rail_item(factory, "Blip", 231, 73, 54, 38, 94, lambda f, p, x, y, s: _automation_icon(f, p, x, y, s, "AutoBlip", "blip"), "BLIP", "''", label_size=7, value_size=7, show_value=False))
    return factory.layer("MatchedState", children, visible_expression="[AuthenticControls.HasMatch]")


def _empty_state(factory: ItemFactory, unmatched: bool, compact: bool) -> dict[str, Any]:
    is_glance = factory.height <= 120
    accent = ORANGE if unmatched else ACCENT
    title_expression = (
        "if([AuthenticControls.RawCarIdentifier] == '', 'Unknown car', [AuthenticControls.RawCarIdentifier])"
        if unmatched
        else "if([AuthenticControls.MatchStatus] == 'database-error', 'Database unavailable', if([AuthenticControls.MatchStatus] == 'runtime-error', 'Plugin runtime error', 'Waiting for a car'))"
    )
    if is_glance:
        children = [
            factory.rectangle("StateMark", 12, 14, 28, 28, accent, radius=6),
            factory.text("StateMarkText", "!" if unmatched else "…", 12, 14, 28, 28, 16, "#FF111820", horizontal_alignment=1, font_weight="Bold"),
            factory.text("StateTitle", "Unmapped car" if unmatched else "Waiting for a car", 48, 12, 256, 28, 16, WHITE, expression=title_expression, font_weight="Bold"),
            factory.text("StateBody", "Contribution available - no values assumed" if unmatched else "Start a supported session", 12, 54, 292, 34, 12, MUTED, font_weight="Bold"),
        ]
    else:
        left = 16 if compact else 28
        children = _header(factory, compact=compact)
        children.extend([
            factory.text("StateEyebrow", "CONTRIBUTION NEEDED" if unmatched else "AUTHENTIC SETUP", 60 if compact else 92, 20 if compact else 24, factory.width - 100, 22, 11 if compact else 13, accent, font_weight="Bold"),
            factory.text("StateTitle", "Unmapped car" if unmatched else "Waiting for a car", 60 if compact else 92, 42 if compact else 52, factory.width - 110, 38, 21 if compact else 30, WHITE, expression=title_expression, font_weight="Bold"),
            factory.rectangle("StateRule", left, 82 if compact else 108, factory.width - 2 * left, 2, SLATE),
            factory.text("StateBody", "No curated record exists for this exact identity." if unmatched else "Start a supported simulator session to see authentic controls guidance.", left, 105 if compact else 140, factory.width - 2 * left, 48, 16 if compact else 22, TEXT, font_weight="Bold"),
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
                    "CONTRIBUTE IN AUTHENTIC CONTROLS",
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
                    "Open the Authentic Controls page in SimHub and choose Contribute this car.",
                    left,
                    hint_top,
                    factory.width - 2 * left,
                    40,
                    10 if compact else 12,
                    MUTED,
                    font_weight="Bold",
                ),
            ])
    expression = "![AuthenticControls.HasMatch] && [AuthenticControls.MatchStatus] == 'unmatched'" if unmatched else "![AuthenticControls.HasMatch] && [AuthenticControls.MatchStatus] != 'unmatched'"
    return factory.layer("UnmatchedState" if unmatched else "WaitingState", children, visible_expression=expression)


def _verification_drive(factory: ItemFactory) -> list[dict[str, Any]]:
    progress_expression = (
        "if([AuthenticControls.VerificationDriveStepNumber] == 0, 'READY', "
        "'STEP ' + [AuthenticControls.VerificationDriveStepNumber] + "
        "' / ' + [AuthenticControls.VerificationDriveStepCount])"
    )
    pending_status = factory.layer(
        "PendingStatus",
        [factory.text("PendingStatusText", "Waiting for telemetry", 34, 146, 628, 28, 12, WHITE, expression="[AuthenticControls.VerificationDriveStatus]")],
        visible_expression="![AuthenticControls.VerificationDriveResultReady]",
    )
    successful_status = factory.layer(
        "SuccessfulStatus",
        [
            factory.text("SuccessBadge", "✓ CAPTURED", 34, 146, 126, 28, 12, GREEN, font_weight="Bold"),
            factory.text("SuccessSummary", "Result captured", 164, 146, 498, 28, 13, WHITE, expression="[AuthenticControls.VerificationDriveResult]", font_weight="Bold"),
        ],
        visible_expression="[AuthenticControls.VerificationDriveResultReady] && [AuthenticControls.VerificationDriveResultSuccessful]",
    )
    review_status = factory.layer(
        "ReviewStatus",
        [
            factory.text("ReviewBadge", "REVIEW", 34, 146, 94, 28, 12, ORANGE, font_weight="Bold"),
            factory.text("ReviewSummary", "Review result", 132, 146, 530, 28, 13, WHITE, expression="[AuthenticControls.VerificationDriveResult]", font_weight="Bold"),
        ],
        visible_expression="[AuthenticControls.VerificationDriveResultReady] && ![AuthenticControls.VerificationDriveResultSuccessful]",
    )
    return [
        factory.rectangle("Card", 4, 4, 692, 212, CARD, radius=18, border_color=SLATE, border=2),
        factory.rectangle("Accent", 20, 4, 660, 5, ACCENT, radius=3),
        factory.text("Eyebrow", "GUIDED VERIFICATION", 24, 18, 250, 24, 13, ACCENT, font_weight="Bold"),
        factory.text("Progress", "STEP 1 / 6", 520, 18, 152, 24, 13, MUTED, expression=progress_expression, horizontal_alignment=2, font_weight="Bold"),
        factory.rectangle("HeaderRule", 24, 48, 648, 1, SLATE),
        factory.text("Title", "Verification step", 24, 56, 648, 34, 24, WHITE, expression="[AuthenticControls.VerificationDriveTitle]", font_weight="Bold"),
        factory.text("PromptLine1", "Follow the current test prompt.", 24, 91, 648, 22, 14, TEXT, expression="[AuthenticControls.VerificationDrivePromptLine1]", font_weight="Bold"),
        factory.text("PromptLine2", "Then continue to the next step.", 24, 115, 648, 22, 14, TEXT, expression="[AuthenticControls.VerificationDrivePromptLine2]", font_weight="Bold"),
        factory.rectangle("StatusPanel", 24, 143, 648, 34, "#FF102333", radius=7, border_color=SLATE, border=1),
        pending_status,
        successful_status,
        review_status,
        factory.text("LiveValues", "Waiting for live telemetry", 24, 181, 350, 23, 11, MUTED, expression="[AuthenticControls.VerificationDriveLiveValues]"),
        factory.text("Controls", "NEXT / ACCEPT   •   RETRY   •   SKIP   •   CANCEL", 370, 181, 302, 23, 10, ACCENT, horizontal_alignment=2, font_weight="Bold"),
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
        if spec.key in ("detailed", "display"):
            children.append(_matched_detailed(factory))
        elif spec.key == "compact":
            children.append(_matched_compact(factory))
        else:
            children.append(_matched_glance(factory))
        children.extend([
            _empty_state(factory, unmatched=True, compact=spec.key == "compact"),
            _empty_state(factory, unmatched=False, compact=spec.key == "compact"),
        ])
    visible_expression = None
    if overlay:
        property_suffix = {
            "detailed": "Detailed",
            "compact": "Compact",
            "glance": "Glance",
            "verification": "Verification",
        }[spec.key]
        visible_expression = (
            "[AuthenticControls.VerificationDriveVisible]"
            if spec.key == "verification"
            else "[AuthenticControls.Popup" + property_suffix + "Visible]"
        )
    outer = factory.layer(
        "VerificationCard" if spec.key == "verification" else "PreflightCard",
        children,
        visible_expression=visible_expression,
    )
    dashboard_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "authentic-controls/" + spec.key + "/dashboard"))
    screen_id = str(uuid.uuid5(uuid.NAMESPACE_URL, "authentic-controls/" + spec.key + "/screen"))
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
        "Category": "Authentic Controls",
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
    parser = argparse.ArgumentParser(description="Generate Authentic Controls SimHub Dash Studio artifacts.")
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    for path in write_dashboards(args.output):
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

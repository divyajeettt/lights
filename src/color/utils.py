"""Pure color helpers."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass

from src.models import Color


@dataclass(frozen=True)
class HsvCommand:
    h: int
    s: int
    v: int


def parse_rgb(value: str) -> Color:
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != 6:
        raise ValueError("RGB color must look like #00aaff")
    return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb: Color) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def relative_luminance(rgb: Color) -> float:
    r, g, b = rgb
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def rgb_saturation(rgb: Color) -> float:
    r, g, b = (channel / 255 for channel in rgb)
    return colorsys.rgb_to_hsv(r, g, b)[1]


def is_usable_album_color(
    rgb: Color,
    min_luminance: float,
    min_saturation: float,
) -> bool:
    return (
        relative_luminance(rgb) >= min_luminance
        and rgb_saturation(rgb) >= min_saturation
    )


def rgb_to_hsv_command(
    rgb: Color,
    h_max: int = 360,
    s_max: int = 255,
    v_max: int = 255,
    min_value_percent: float = 35.0,
) -> HsvCommand:
    r, g, b = (channel / 255 for channel in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    min_v = int(round(v_max * (min_value_percent / 100)))
    hue = int(round(h * h_max))
    if hue >= h_max:
        hue = 0
    sat = max(1, int(round(s * s_max)))
    val = max(min_v, int(round(v * v_max)))
    return HsvCommand(h=hue, s=sat, v=val)

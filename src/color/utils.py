"""Pure color helpers."""

from __future__ import annotations

import colorsys
from dataclasses import dataclass

from src.models import Color

RGB_HEX_LENGTH = 6
RGB_BYTE_MAX = 255
PERCENT_MAX = 100

DEFAULT_HUE_MAX = 360
DEFAULT_SATURATION_MAX = RGB_BYTE_MAX
DEFAULT_VALUE_MAX = RGB_BYTE_MAX
DEFAULT_MIN_VALUE_PERCENT = 35.0

RED_LUMINANCE_WEIGHT = 0.2126
GREEN_LUMINANCE_WEIGHT = 0.7152
BLUE_LUMINANCE_WEIGHT = 0.0722


@dataclass(frozen=True)
class HsvCommand:
    h: int
    s: int
    v: int


def parse_rgb(value: str) -> Color:
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != RGB_HEX_LENGTH:
        raise ValueError("RGB color must look like #00aaff")
    return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb: Color) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def relative_luminance(rgb: Color) -> float:
    r, g, b = rgb
    return (
        RED_LUMINANCE_WEIGHT * r
        + GREEN_LUMINANCE_WEIGHT * g
        + BLUE_LUMINANCE_WEIGHT * b
    ) / RGB_BYTE_MAX


def rgb_saturation(rgb: Color) -> float:
    r, g, b = (channel / RGB_BYTE_MAX for channel in rgb)
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
    h_max: int = DEFAULT_HUE_MAX,
    s_max: int = DEFAULT_SATURATION_MAX,
    v_max: int = DEFAULT_VALUE_MAX,
    min_value_percent: float = DEFAULT_MIN_VALUE_PERCENT,
) -> HsvCommand:
    r, g, b = (channel / RGB_BYTE_MAX for channel in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    min_v = int(round(v_max * (min_value_percent / PERCENT_MAX)))
    hue = int(round(h * h_max))
    if hue >= h_max:
        hue = 0
    sat = int(round(s * s_max))
    val = max(min_v, int(round(v * v_max)))
    return HsvCommand(h=hue, s=sat, v=val)

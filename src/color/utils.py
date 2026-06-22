"""Pure color helpers."""

import colorsys
from dataclasses import dataclass

from src.models import Color

from .constants import (
    BLUE_LUMINANCE_WEIGHT,
    BRIGHTNESS_SCALE,
    GREEN_LUMINANCE_WEIGHT,
    MIN_VALUE_PERCENT,
    PERCENT_MAX,
    RED_LUMINANCE_WEIGHT,
    RGB_BYTE_MAX,
    RGB_HEX_LENGTH,
)


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


def derive_palette_variants(rgb: Color, count: int) -> list[Color]:
    if count <= 0:
        return []
    r, g, b = (channel / RGB_BYTE_MAX for channel in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    variants = [rgb]
    for index in range(1, count):
        next_h = (h + index / count) % 1.0
        next_s = max(0.35, s)
        next_v = max(0.35, v)
        nr, ng, nb = colorsys.hsv_to_rgb(next_h, next_s, next_v)
        variants.append(
            (
                int(round(nr * RGB_BYTE_MAX)),
                int(round(ng * RGB_BYTE_MAX)),
                int(round(nb * RGB_BYTE_MAX)),
            )
        )
    return variants


def rgb_to_hsv_command(rgb: Color, *, h_max: int, s_max: int, v_max: int) -> HsvCommand:
    r, g, b = (channel / RGB_BYTE_MAX for channel in rgb)
    h, s, _v = colorsys.rgb_to_hsv(r, g, b)
    min_v = int(round(v_max * (MIN_VALUE_PERCENT / PERCENT_MAX)))
    hue = int(round(h * h_max))
    if hue >= h_max:
        hue = 0
    sat = int(round(s * s_max))
    scaled_value = relative_luminance(rgb) * BRIGHTNESS_SCALE
    val = min(v_max, max(min_v, int(round(scaled_value * v_max))))
    return HsvCommand(h=hue, s=sat, v=val)

"""Pure color helpers."""

import colorsys
import math
from dataclasses import dataclass

from src.models import Color

from .constants import (
    BLACK,
    BLACK_DISTANCE_GAMMA,
    MIN_VALUE_PERCENT,
    PERCENT_MAX,
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
                round(nr * RGB_BYTE_MAX),
                round(ng * RGB_BYTE_MAX),
                round(nb * RGB_BYTE_MAX),
            )
        )
    return variants


def rgb_to_hsv_command(rgb: Color, *, h_max: int, s_max: int, v_max: int) -> HsvCommand:
    r, g, b = (channel / RGB_BYTE_MAX for channel in rgb)
    h, s, _v = colorsys.rgb_to_hsv(r, g, b)
    min_v = round(v_max * (MIN_VALUE_PERCENT / PERCENT_MAX))
    if (hue := round(h * h_max)) >= h_max:
        hue = 0
    sat = round(s * s_max)
    black_distance = math.dist(rgb, BLACK) / math.sqrt(3)
    scaled_value = black_distance ** BLACK_DISTANCE_GAMMA
    val = min(v_max, max(min_v, round(scaled_value * v_max)))
    return HsvCommand(h=hue, s=sat, v=val)

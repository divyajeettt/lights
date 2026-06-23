"""Pure color helpers."""

import colorsys
import math
from dataclasses import dataclass

from src.models import Color

from .constants import (
    BLACK,
    BLACK_DISTANCE_GAMMA,
    MIN_VALUE_PERCENT,
    NEAR_BLACK_THRESHOLD,
    PERCENT_MAX,
    RGB_BYTE_MAX,
    RGB_HEX_LENGTH,
    SATURATION_BOOST_THRESHOLD,
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


def normalize_rgb(rgb: Color) -> Color:
    return tuple(channel / RGB_BYTE_MAX for channel in rgb)


def black_distance(rgb: Color, *, normalize: bool) -> float:
    if normalize:
        rgb = normalize_rgb(rgb)
    return math.dist(rgb, BLACK) / math.sqrt(3)


def rgb_to_hsv_command(rgb: Color, *, h_max: int, s_max: int, v_max: int) -> HsvCommand:
    r, g, b = normalize_rgb(rgb)
    h, s, _v = colorsys.rgb_to_hsv(r, g, b)

    hue = round(h * h_max)
    if hue >= h_max:
        hue = 0

    # 1. Calculate true distance to black
    distance_from_black = black_distance((r, g, b), normalize=False)

    # 2. HARD THRESHOLD: If it's practically black, force the value to absolute 0
    # This overrides min_v so the bulb actually shuts off for black-ish colors.
    if distance_from_black < NEAR_BLACK_THRESHOLD:
        return HsvCommand(h=0, s=0, v=0)

    # 3. SATURATION BOOST: If the color is dark, pump up the saturation
    # to prevent the bulb from falling back to its bright white channel.
    if distance_from_black < SATURATION_BOOST_THRESHOLD:
        # Quadratically scale saturation up the darker the color gets
        s_boost = ((1.0 - distance_from_black) ** 2) * SATURATION_BOOST_THRESHOLD
        s = min(1.0, s + s_boost)

    sat = round(s * s_max)

    # 4. Standard value scaling
    min_v = round(v_max * (MIN_VALUE_PERCENT / PERCENT_MAX))
    scaled_value = distance_from_black**BLACK_DISTANCE_GAMMA
    val = min(v_max, max(min_v, round(scaled_value * v_max)))

    return HsvCommand(h=hue, s=sat, v=val)

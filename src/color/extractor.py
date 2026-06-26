"""Album art color extraction."""

import colorsys
from io import BytesIO

import colorgram
import requests
from PIL import Image

from src.models import Color

from .constants import (
    COLORGRAM_PALETTE_COLORS,
    FALLBACK_PALETTE_ATTEMPTS,
    MIN_DIVERSE_HUE_DEGREES,
    MIN_DIVERSE_SATURATION_THRESHOLD,
    NEAR_BLACK_THRESHOLD,
)
from .utils import black_distance, normalize_rgb


def image_pixel_data(image: Image.Image) -> Image.core.ImagingCore:
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def _visible_rgb_image(image: Image.Image) -> Image.Image:
    pixels = [(r, g, b) for r, g, b, a in image_pixel_data(image) if a >= 128]
    if not pixels:
        raise RuntimeError("Album art image had no visible pixels")

    rgb_image = Image.new("RGB", (len(pixels), 1))
    rgb_image.putdata(pixels)
    return rgb_image


def _colorgram_palette_from_image_bytes(
    image_bytes: bytes,
    colors: int,
) -> list[Color]:
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    rgb_image = _visible_rgb_image(image)
    buffer = BytesIO()
    rgb_image.save(buffer, format="PNG")
    buffer.seek(0)

    extracted = colorgram.extract(buffer, colors)
    return [(color.rgb.r, color.rgb.g, color.rgb.b) for color in extracted]


def _hsv_color(rgb: Color) -> tuple[float, float, float]:
    return colorsys.rgb_to_hsv(*normalize_rgb(rgb))


def _hue_distance_degrees(first_hue: float, second_hue: float) -> float:
    distance = abs(first_hue - second_hue) * 360
    return min(distance, 360 - distance)


def _is_diverse_color(candidate: Color, selected: list[Color]) -> bool:
    candidate_hue, candidate_saturation, _ = _hsv_color(candidate)
    if candidate_saturation < MIN_DIVERSE_SATURATION_THRESHOLD:
        return False

    selected_hues = [
        hue
        for hue, saturation, _ in (_hsv_color(color) for color in selected)
        if saturation >= MIN_DIVERSE_SATURATION_THRESHOLD
    ]
    return all(
        _hue_distance_degrees(candidate_hue, selected_hue) >= MIN_DIVERSE_HUE_DEGREES
        for selected_hue in selected_hues
    )


def _select_visible_palette_colors(
    visible_palette: list[Color], *, count: int
) -> list[Color]:
    selected: list[Color] = []
    selected_indexes: set[int] = set()
    for index, color in enumerate(visible_palette):
        if len(selected) >= count:
            break
        if not selected or _is_diverse_color(color, selected):
            selected.append(color)
            selected_indexes.add(index)

    for index, color in enumerate(visible_palette):
        if len(selected) >= count:
            break
        if index not in selected_indexes:
            selected.append(color)
            selected_indexes.add(index)

    return selected


def album_palette_from_image_bytes(
    image_bytes: bytes, *, count: int
) -> tuple[list[Color], bool]:
    if count <= 0:
        raise ValueError("Palette color count must be greater than 0")

    extraction_count = max(COLORGRAM_PALETTE_COLORS, count, FALLBACK_PALETTE_ATTEMPTS)
    palette = _colorgram_palette_from_image_bytes(image_bytes, colors=extraction_count)
    fallback_used = False

    visible_palette = [
        color
        for color in palette
        if black_distance(color, normalize=True) > NEAR_BLACK_THRESHOLD
    ]
    selected = (
        _select_visible_palette_colors(visible_palette, count=count)
        if len(visible_palette) >= count
        else palette[:count]
    )

    if len(selected) < count:
        raise RuntimeError("Album art image did not yield enough visible colors")
    return selected, fallback_used


def album_rgb_from_image_bytes(image_bytes: bytes) -> tuple[Color, bool]:
    palette, fallback_used = album_palette_from_image_bytes(image_bytes, count=1)
    return palette[0], fallback_used


def album_rgb_from_url(image_url: str) -> tuple[Color, bool]:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return album_rgb_from_image_bytes(response.content)


def album_palette_from_url(image_url: str, *, count: int) -> tuple[list[Color], bool]:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return album_palette_from_image_bytes(response.content, count=count)

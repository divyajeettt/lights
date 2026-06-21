"""Album art color extraction."""

from __future__ import annotations

from io import BytesIO
from typing import Any

import requests
from PIL import Image

from src.config import env, env_float
from src.models import Color

from .utils import is_usable_album_color, parse_rgb


def image_pixel_data(image: Image.Image) -> Any:
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def album_rgb_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
    fallback_rgb: Color | None = None,
) -> tuple[Color, bool]:
    if min_luminance is None:
        min_luminance = env_float("ALBUM_COLOR_MIN_LUMINANCE", 0.08)
    if min_saturation is None:
        min_saturation = env_float("ALBUM_COLOR_MIN_SATURATION", 0.12)
    if fallback_rgb is None:
        fallback_rgb = parse_rgb(env("ALBUM_COLOR_FALLBACK", "#ff6600"))

    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    image.thumbnail((160, 160), Image.Resampling.LANCZOS)

    pixels = []
    for r, g, b, a in image_pixel_data(image):
        if a < 128:
            continue
        pixels.append((r, g, b))
    if not pixels:
        raise RuntimeError("Album art image had no visible pixels")

    rgb_image = Image.new("RGB", (len(pixels), 1))
    rgb_image.putdata(pixels)
    palette = rgb_image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    counts = palette.getcolors(maxcolors=colors)
    if not counts:
        raise RuntimeError("Could not quantize album art")
    pal = palette.getpalette()

    candidates = []
    for count, palette_index in counts:
        offset = palette_index * 3
        rgb = (pal[offset], pal[offset + 1], pal[offset + 2])
        if is_usable_album_color(rgb, min_luminance, min_saturation):
            candidates.append((count, rgb))

    if not candidates:
        return fallback_rgb, True

    return max(candidates, key=lambda item: item[0])[1], False


def dominant_rgb_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
    fallback_rgb: Color | None = None,
) -> Color:
    rgb, _ = album_rgb_from_image_bytes(
        image_bytes,
        colors=colors,
        min_luminance=min_luminance,
        min_saturation=min_saturation,
        fallback_rgb=fallback_rgb,
    )
    return rgb


def album_rgb_from_url(image_url: str) -> tuple[Color, bool]:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return album_rgb_from_image_bytes(response.content)


def dominant_rgb_from_url(image_url: str) -> Color:
    rgb, _ = album_rgb_from_url(image_url)
    return rgb

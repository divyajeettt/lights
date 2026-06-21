"""Album art color extraction."""

from io import BytesIO
from typing import Any

import requests
from PIL import Image

from src.config import env, env_float
from src.constants import (
    DEFAULT_ALBUM_COLOR_FALLBACK,
    DEFAULT_ALBUM_COLOR_MIN_LUMINANCE,
    DEFAULT_ALBUM_COLOR_MIN_SATURATION,
)
from src.enums import AlbumColorEnvVar
from src.models import Color

from .utils import derive_palette_variants, is_usable_album_color, parse_rgb


def image_pixel_data(image: Image.Image) -> Any:
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def _palette_candidates_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
) -> list[tuple[int, Color]]:
    if min_luminance is None:
        min_luminance = env_float(
            AlbumColorEnvVar.MIN_LUMINANCE,
            DEFAULT_ALBUM_COLOR_MIN_LUMINANCE,
        )
    if min_saturation is None:
        min_saturation = env_float(
            AlbumColorEnvVar.MIN_SATURATION,
            DEFAULT_ALBUM_COLOR_MIN_SATURATION,
        )

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

    return sorted(candidates, key=lambda item: item[0], reverse=True)


def album_palette_from_image_bytes(
    image_bytes: bytes,
    count: int,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
    fallback_rgb: Color | None = None,
) -> tuple[list[Color], bool]:
    if count <= 0:
        raise ValueError("Palette color count must be greater than 0")
    if fallback_rgb is None:
        fallback_rgb = parse_rgb(
            env(AlbumColorEnvVar.FALLBACK, DEFAULT_ALBUM_COLOR_FALLBACK)
        )

    candidates = _palette_candidates_from_image_bytes(
        image_bytes,
        colors=colors,
        min_luminance=min_luminance,
        min_saturation=min_saturation,
    )
    if not candidates:
        return derive_palette_variants(fallback_rgb, count), True

    palette = [rgb for _candidate_count, rgb in candidates[:count]]
    if len(palette) < count:
        variants = derive_palette_variants(palette[0], count)
        palette.extend(variants[len(palette) : count])
    return palette, False


def album_rgb_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
    fallback_rgb: Color | None = None,
) -> tuple[Color, bool]:
    palette, fallback_used = album_palette_from_image_bytes(
        image_bytes,
        count=1,
        colors=colors,
        min_luminance=min_luminance,
        min_saturation=min_saturation,
        fallback_rgb=fallback_rgb,
    )
    return palette[0], fallback_used


def album_rgb_from_url(image_url: str) -> tuple[Color, bool]:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return album_rgb_from_image_bytes(response.content)


def album_palette_from_url(image_url: str, count: int) -> tuple[list[Color], bool]:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return album_palette_from_image_bytes(response.content, count=count)

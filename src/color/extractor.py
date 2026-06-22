"""Album art color extraction."""

from io import BytesIO
from typing import Any

import colorgram
import requests
from PIL import Image

from src.models import Color

from .constants import FALLBACK_PALETTE_ATTEMPTS


def image_pixel_data(image: Image.Image) -> Any:
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
    colors: int = 16,
) -> list[Color]:
    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    rgb_image = _visible_rgb_image(image)
    buffer = BytesIO()
    rgb_image.save(buffer, format="PNG")
    buffer.seek(0)

    extracted = colorgram.extract(buffer, colors)
    return [(color.rgb.r, color.rgb.g, color.rgb.b) for color in extracted]


def album_palette_from_image_bytes(
    image_bytes: bytes,
    count: int,
    colors: int = 16,
) -> tuple[list[Color], bool]:
    if count <= 0:
        raise ValueError("Palette color count must be greater than 0")

    extraction_count = max(colors, count, FALLBACK_PALETTE_ATTEMPTS)
    palette = _colorgram_palette_from_image_bytes(image_bytes, colors=extraction_count)
    fallback_used = False

    selected = palette[:count]
    if len(selected) < count:
        selected.extend(palette[count:FALLBACK_PALETTE_ATTEMPTS])
    if len(selected) < count:
        raise RuntimeError("Album art image did not yield enough visible colors")
    return selected[:count], fallback_used


def album_rgb_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
) -> tuple[Color, bool]:
    palette, fallback_used = album_palette_from_image_bytes(
        image_bytes,
        count=1,
        colors=colors,
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

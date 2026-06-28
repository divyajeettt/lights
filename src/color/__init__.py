"""Color utilities and album-art extraction."""

from typing import Final

from .extractor import (
    album_palette_from_image_bytes,
    album_palette_from_url,
    album_rgb_from_image_bytes,
    album_rgb_from_url,
    image_pixel_data,
)
from .utils import (
    HsvCommand,
    black_distance,
    derive_palette_variants,
    normalize_rgb,
    parse_rgb,
    rgb_hex,
    rgb_to_hsv_command,
)

__all__: Final[list[str]] = [
    "HsvCommand",
    "album_palette_from_image_bytes",
    "album_palette_from_url",
    "album_rgb_from_image_bytes",
    "album_rgb_from_url",
    "black_distance",
    "derive_palette_variants",
    "image_pixel_data",
    "normalize_rgb",
    "parse_rgb",
    "rgb_hex",
    "rgb_to_hsv_command",
]

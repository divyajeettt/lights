from io import BytesIO

import pytest
from PIL import Image

from src.color import album_palette_from_image_bytes, album_rgb_from_image_bytes


def make_png_bytes(
    rgba: tuple[int, int, int, int],
    size: tuple[int, int] = (4, 4),
) -> bytes:
    image = Image.new("RGBA", size, rgba)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_album_rgb_from_image_bytes_uses_fallback_for_unusable_color() -> None:
    image_bytes = make_png_bytes((20, 20, 20, 255))

    rgb, fallback_used = album_rgb_from_image_bytes(
        image_bytes,
        min_luminance=0.5,
        min_saturation=0.5,
        fallback_rgb=(255, 102, 0),
    )

    assert rgb == (255, 102, 0)
    assert fallback_used is True


def test_album_rgb_from_image_bytes_rejects_transparent_image() -> None:
    image_bytes = make_png_bytes((20, 20, 20, 0))

    with pytest.raises(RuntimeError, match="no visible pixels"):
        album_rgb_from_image_bytes(image_bytes, fallback_rgb=(255, 102, 0))


def test_album_palette_from_image_bytes_fills_missing_colors_with_variants() -> None:
    image_bytes = make_png_bytes((0, 170, 255, 255))

    palette, fallback_used = album_palette_from_image_bytes(
        image_bytes,
        count=2,
        min_luminance=0.01,
        min_saturation=0.01,
        fallback_rgb=(255, 102, 0),
    )

    assert palette[0] == (0, 170, 255)
    assert len(palette) == 2
    assert fallback_used is False

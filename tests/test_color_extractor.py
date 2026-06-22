from io import BytesIO

import pytest
from PIL import Image

from src.color import (
    album_palette_from_image_bytes,
    album_rgb_from_image_bytes,
    extractor,
)


def make_png_bytes(
    rgba: tuple[int, int, int, int],
    size: tuple[int, int] = (4, 4),
) -> bytes:
    image = Image.new("RGBA", size, rgba)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def make_transparent_padded_png_bytes() -> bytes:
    image = Image.new("RGBA", (4, 4), (0, 0, 0, 0))
    image.putpixel((0, 0), (255, 0, 0, 255))
    image.putpixel((1, 0), (0, 255, 0, 255))
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


class StubRgb:
    def __init__(self, rgb: tuple[int, int, int]) -> None:
        self.r, self.g, self.b = rgb


class StubColor:
    def __init__(self, rgb: tuple[int, int, int]) -> None:
        self.rgb = StubRgb(rgb)


def test_album_rgb_from_image_bytes_uses_first_colorgram_palette_color(
    monkeypatch,
) -> None:
    image_bytes = make_png_bytes((20, 20, 20, 255))

    monkeypatch.setattr(
        extractor.colorgram,
        "extract",
        lambda _image, _colors: [
            StubColor((0, 170, 255)),
            StubColor((255, 102, 0)),
        ],
    )

    rgb, fallback_used = album_rgb_from_image_bytes(image_bytes)

    assert rgb == (0, 170, 255)
    assert fallback_used is False


def test_album_palette_from_image_bytes_uses_colorgram_palette_order(
    monkeypatch,
) -> None:
    image_bytes = make_png_bytes((0, 170, 255, 255))

    monkeypatch.setattr(
        extractor.colorgram,
        "extract",
        lambda _image, _colors: [
            StubColor((0, 170, 255)),
            StubColor((255, 102, 0)),
            StubColor((51, 204, 102)),
        ],
    )

    palette, fallback_used = album_palette_from_image_bytes(image_bytes, count=2)

    assert palette == [(0, 170, 255), (255, 102, 0)]
    assert fallback_used is False


def test_album_palette_from_image_bytes_uses_fallback_when_colorgram_finds_no_colors(
    monkeypatch,
) -> None:
    image_bytes = make_png_bytes((20, 20, 20, 255))

    monkeypatch.setattr(extractor.colorgram, "extract", lambda _image, _colors: [])

    with pytest.raises(RuntimeError, match="did not yield enough visible colors"):
        album_palette_from_image_bytes(image_bytes, count=1)


def test_album_palette_from_image_bytes_uses_fixed_fallback_after_palette_attempts(
    monkeypatch,
) -> None:
    image_bytes = make_png_bytes((0, 170, 255, 255))

    monkeypatch.setattr(
        extractor.colorgram,
        "extract",
        lambda _image, _colors: [
            StubColor((0, 170, 255)),
            StubColor((255, 102, 0)),
            StubColor((51, 204, 102)),
            StubColor((128, 64, 255)),
            StubColor((255, 230, 40)),
        ],
    )

    with pytest.raises(RuntimeError, match="did not yield enough visible colors"):
        album_palette_from_image_bytes(image_bytes, count=6)


def test_album_palette_from_image_bytes_extracts_at_least_five_fallback_candidates(
    monkeypatch,
) -> None:
    image_bytes = make_png_bytes((0, 170, 255, 255))
    requested_counts = []

    def extract(_image, colors):
        requested_counts.append(colors)
        return [StubColor((0, 170, 255))]

    monkeypatch.setattr(extractor.colorgram, "extract", extract)

    album_palette_from_image_bytes(
        image_bytes,
        count=1,
        colors=1,
    )

    assert requested_counts == [5]


def test_album_palette_from_image_bytes_strips_transparent_pixels_before_colorgram(
    monkeypatch,
) -> None:
    image_bytes = make_transparent_padded_png_bytes()
    colorgram_pixels = []

    def extract(image, _colors):
        colorgram_image = Image.open(image).convert("RGB")
        colorgram_pixels.extend(extractor.image_pixel_data(colorgram_image))
        return [StubColor((255, 0, 0))]

    monkeypatch.setattr(extractor.colorgram, "extract", extract)

    album_palette_from_image_bytes(image_bytes, count=1)

    assert colorgram_pixels == [(255, 0, 0), (0, 255, 0)]


def test_album_rgb_from_image_bytes_rejects_transparent_image() -> None:
    image_bytes = make_png_bytes((20, 20, 20, 0))

    with pytest.raises(RuntimeError, match="no visible pixels"):
        album_rgb_from_image_bytes(image_bytes)

from src.color import is_usable_album_color, parse_rgb, rgb_to_hsv_command


def test_parse_rgb_parses_hex_string() -> None:
    assert parse_rgb("#00aaff") == (0, 170, 255)


def test_is_usable_album_color_rejects_dark_gray() -> None:
    assert not is_usable_album_color(
        (20, 20, 20),
        min_luminance=0.08,
        min_saturation=0.12,
    )


def test_rgb_to_hsv_command_applies_min_value_floor() -> None:
    hsv = rgb_to_hsv_command((1, 1, 1), v_max=255, min_value_percent=35.0)
    assert hsv.v >= 89

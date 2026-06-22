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
    hsv = rgb_to_hsv_command((1, 1, 1), h_max=360, s_max=255, v_max=255)
    assert hsv.v == 3


def test_rgb_to_hsv_command_uses_relative_luminance_for_value() -> None:
    blue = rgb_to_hsv_command(
        (0, 0, 255),
        h_max=360,
        s_max=1000,
        v_max=1000,
    )
    red = rgb_to_hsv_command(
        (255, 0, 0),
        h_max=360,
        s_max=1000,
        v_max=1000,
    )

    assert blue.v == 18
    assert red.v == 53
    assert blue.v < red.v


def test_rgb_to_hsv_command_applies_brightness_scale_constant() -> None:
    hsv = rgb_to_hsv_command(
        (255, 255, 255),
        h_max=360,
        s_max=1000,
        v_max=1000,
    )

    assert hsv.v == 250


def test_rgb_to_hsv_command_preserves_grayscale_saturation() -> None:
    hsv = rgb_to_hsv_command((128, 128, 128), h_max=360, s_max=255, v_max=255)
    assert hsv.s == 0

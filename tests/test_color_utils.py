from src.color import parse_rgb, rgb_to_hsv_command


def test_parse_rgb_parses_hex_string() -> None:
    assert parse_rgb("#00aaff") == (0, 170, 255)


def test_rgb_to_hsv_command_applies_min_value_floor() -> None:
    hsv = rgb_to_hsv_command((1, 1, 1), h_max=360, s_max=255, v_max=255)
    assert hsv.v == 3


def test_rgb_to_hsv_command_scales_value_by_black_distance_gamma() -> None:
    dark = rgb_to_hsv_command(
        (0x0F, 0x0B, 0x27),
        h_max=360,
        s_max=1000,
        v_max=1000,
    )
    bright = rgb_to_hsv_command(
        (0xBF, 0x9C, 0x83),
        h_max=360,
        s_max=1000,
        v_max=1000,
    )

    assert dark.v == 10
    assert bright.v == 365
    assert dark.v < bright.v


def test_rgb_to_hsv_command_allows_white_to_reach_full_value() -> None:
    hsv = rgb_to_hsv_command(
        (255, 255, 255),
        h_max=360,
        s_max=1000,
        v_max=1000,
    )

    assert hsv.v == 1000


def test_rgb_to_hsv_command_preserves_grayscale_saturation() -> None:
    hsv = rgb_to_hsv_command((128, 128, 128), h_max=360, s_max=255, v_max=255)
    assert hsv.s == 0

"""Constants for color utilities."""

from typing import Final

from src.models import Color

COLORGRAM_PALETTE_COLORS: Final[int] = 5
FALLBACK_PALETTE_ATTEMPTS: Final[int] = 5
NEAR_BLACK_THRESHOLD: Final[float] = 0.1
SATURATION_BOOST_THRESHOLD: Final[float] = 0.4
MIN_DIVERSE_HUE_DEGREES: Final[int] = 30
MIN_DIVERSE_SATURATION_THRESHOLD: Final[float] = 0.2

RGB_HEX_LENGTH: Final[int] = 6
RGB_BYTE_MAX: Final[int] = 255
PERCENT_MAX: Final[int] = 100

MIN_VALUE_PERCENT: Final[float] = 1.0
BLACK_DISTANCE_GAMMA: Final[float] = 2.5

BLACK: Final[Color] = (0, 0, 0)

"""TinyTuya local-device constants."""

from typing import Final

TINYTUYA_HUE_MAX: Final[int] = 360
TINYTUYA_SATURATION_VALUE_MAX: Final[int] = 1000

SUPPORTED_TUYA_PROTOCOL_VERSIONS: Final[frozenset[str]] = frozenset(
    {"3.1", "3.2", "3.3", "3.4", "3.5"}
)

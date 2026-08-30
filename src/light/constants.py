"""TinyTuya local-device constants."""

from typing import Final

TINYTUYA_HUE_MAX: Final[int] = 360
TINYTUYA_LOCAL_KEY_LENGTH: Final[int] = 16
TINYTUYA_PORT: Final[int] = 6668
TINYTUYA_SATURATION_VALUE_MAX: Final[int] = 1000
TINYTUYA_SOCKET_RETRY_LIMIT: Final[int] = 1
TINYTUYA_SOCKET_TIMEOUT_SECONDS: Final[float] = 1.0

SUPPORTED_TUYA_PROTOCOL_VERSIONS: Final[frozenset[str]] = frozenset(
    {"3.1", "3.2", "3.3", "3.4", "3.5"}
)

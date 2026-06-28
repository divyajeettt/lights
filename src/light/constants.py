"""Constants for light integrations."""

from typing import Final

TUYA_ENDPOINT: Final[str] = "https://openapi.tuyain.com"
TUYA_TOKEN_PATH: Final[str] = "/v1.0/token"
TUYA_DEVICE_SPECIFICATIONS_PATH: Final[str] = "/v1.0/devices/{device_id}/specifications"
TUYA_DEVICE_STATUS_PATH: Final[str] = "/v1.0/devices/{device_id}/status"
TUYA_DEVICE_COMMANDS_PATH: Final[str] = "/v1.0/devices/{device_id}/commands"
TUYA_COLOR_CODE_V2_SUFFIX: Final[str] = "_v2"
TUYA_DEFAULT_HUE_MAX: Final[int] = 360
TUYA_DEFAULT_SATURATION_VALUE_MAX: Final[int] = 255
TUYA_V2_SATURATION_VALUE_MAX: Final[int] = 1000
TUYA_COLOR_CODE_CANDIDATES: Final[tuple[str, ...]] = (
    "colour_data_v2",
    "colour_data",
    "color_data",
    "colour_data_hsv",
)
TUYA_SWITCH_CODE_CANDIDATES: Final[tuple[str, ...]] = (
    "switch_led",
    "switch",
)

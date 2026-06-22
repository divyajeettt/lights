"""Constants for light integrations."""

TUYA_ENDPOINT = "https://openapi.tuyain.com"
TUYA_TOKEN_PATH = "/v1.0/token"
TUYA_DEVICE_SPECIFICATIONS_PATH = "/v1.0/devices/{device_id}/specifications"
TUYA_DEVICE_STATUS_PATH = "/v1.0/devices/{device_id}/status"
TUYA_DEVICE_COMMANDS_PATH = "/v1.0/devices/{device_id}/commands"
TUYA_COLOR_CODE_V2_SUFFIX = "_v2"
TUYA_DEFAULT_HUE_MAX = 360
TUYA_DEFAULT_SATURATION_VALUE_MAX = 255
TUYA_V2_SATURATION_VALUE_MAX = 1000
TUYA_COLOR_CODE_CANDIDATES = (
    "colour_data_v2",
    "colour_data",
    "color_data",
    "colour_data_hsv",
)

"""Shared constants for the application."""

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_SCOPE = "user-read-currently-playing user-read-playback-state"
SPOTIFY_LOCAL_REDIRECT_SCHEME = "http"
SPOTIFY_LOCAL_REDIRECT_HOSTS = {"127.0.0.1", "localhost"}
SPOTIFY_DEFAULT_CALLBACK_HOST = "127.0.0.1"

DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
DEFAULT_POLL_SECONDS = 1.0
DEFAULT_ALBUM_COLOR_FALLBACK = "#ff6600"
DEFAULT_TUYA_ENDPOINT = "https://openapi.tuyain.com"
DEFAULT_TUYA_BRIGHTNESS_SCALE = 0.25
DEFAULT_TUYA_MIN_VALUE_PERCENT = 1.0
DEFAULT_SPOTIFY_CACHE_FILE = ".cache/spotify_token.json"

TUYA_TOKEN_PATH = "/v1.0/token"
TUYA_DEVICE_SPECIFICATIONS_PATH = "/v1.0/devices/{device_id}/specifications"
TUYA_DEVICE_STATUS_PATH = "/v1.0/devices/{device_id}/status"
TUYA_DEVICE_COMMANDS_PATH = "/v1.0/devices/{device_id}/commands"
TUYA_COLOR_CODE_V2_SUFFIX = "_v2"
TUYA_DEFAULT_HUE_MAX = 360
TUYA_DEFAULT_SATURATION_VALUE_MAX = 255
TUYA_V2_SATURATION_VALUE_MAX = 1000

TUYA_SWITCH_CODE_CANDIDATES = ("switch_led", "switch", "switch_1")
TUYA_WORK_MODE_CODE_CANDIDATES = ("work_mode", "mode")
TUYA_COLOR_CODE_CANDIDATES = (
    "colour_data_v2",
    "colour_data",
    "color_data",
    "colour_data_hsv",
)

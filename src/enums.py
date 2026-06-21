"""Closed string vocabularies used across integrations."""

from enum import StrEnum


class AppEnvVar(StrEnum):
    POLL_SECONDS = "POLL_SECONDS"


class AlbumColorEnvVar(StrEnum):
    FALLBACK = "ALBUM_COLOR_FALLBACK"
    MIN_LUMINANCE = "ALBUM_COLOR_MIN_LUMINANCE"
    MIN_SATURATION = "ALBUM_COLOR_MIN_SATURATION"


class LightBackend(StrEnum):
    TUYA_CLOUD = "tuya_cloud"
    HOME_ASSISTANT = "homeassistant"


class LightEnvVar(StrEnum):
    BACKEND = "LIGHT_BACKEND"


class HomeAssistantEnvVar(StrEnum):
    ENTITY_ID = "HOME_ASSISTANT_ENTITY_ID"
    TOKEN = "HOME_ASSISTANT_TOKEN"
    URL = "HOME_ASSISTANT_URL"


class HomeAssistantPayloadField(StrEnum):
    ENTITY_ID = "entity_id"
    RGB_COLOR = "rgb_color"


class SpotifyEnvVar(StrEnum):
    CACHE_FILE = "SPOTIFY_CACHE_FILE"
    CLIENT_ID = "SPOTIFY_CLIENT_ID"
    REDIRECT_URI = "SPOTIFY_REDIRECT_URI"


class SpotifyGrantType(StrEnum):
    AUTHORIZATION_CODE = "authorization_code"
    REFRESH_TOKEN = "refresh_token"


class SpotifyOAuthParam(StrEnum):
    ADDITIONAL_TYPES = "additional_types"
    CLIENT_ID = "client_id"
    CODE = "code"
    CODE_CHALLENGE = "code_challenge"
    CODE_CHALLENGE_METHOD = "code_challenge_method"
    CODE_VERIFIER = "code_verifier"
    ERROR = "error"
    GRANT_TYPE = "grant_type"
    REDIRECT_URI = "redirect_uri"
    REFRESH_TOKEN = "refresh_token"
    RESPONSE_TYPE = "response_type"
    SCOPE = "scope"
    STATE = "state"


class SpotifyPkceMethod(StrEnum):
    S256 = "S256"


class SpotifyResponseType(StrEnum):
    CODE = "code"


class SpotifyTokenField(StrEnum):
    ACCESS_TOKEN = "access_token"
    EXPIRES_AT = "expires_at"
    EXPIRES_IN = "expires_in"
    REFRESH_TOKEN = "refresh_token"


class TuyaColorValueFormat(StrEnum):
    AUTO = "auto"
    OBJECT = "object"
    STRING = "string"


class TuyaCommandField(StrEnum):
    CODE = "code"
    COMMANDS = "commands"
    VALUE = "value"


class TuyaEnvVar(StrEnum):
    ACCESS_ID = "TUYA_ACCESS_ID"
    ACCESS_SECRET = "TUYA_ACCESS_SECRET"
    COLOR_CODE = "TUYA_COLOR_CODE"
    COLOR_VALUE_FORMAT = "TUYA_COLOR_VALUE_FORMAT"
    DEVICE_ID = "TUYA_DEVICE_ID"
    ENDPOINT = "TUYA_ENDPOINT"
    ENSURE_ON_COLOR_MODE = "TUYA_ENSURE_ON_COLOR_MODE"
    MIN_VALUE_PERCENT = "TUYA_MIN_VALUE_PERCENT"
    SWITCH_CODE = "TUYA_SWITCH_CODE"
    WORK_MODE_CODE = "TUYA_WORK_MODE_CODE"
    WORK_MODE_VALUE = "TUYA_WORK_MODE_VALUE"


class TuyaHeader(StrEnum):
    ACCESS_TOKEN = "access_token"
    CLIENT_ID = "client_id"
    NONCE = "nonce"
    SIGN = "sign"
    SIGN_METHOD = "sign_method"
    TIMESTAMP = "t"


class TuyaHsvField(StrEnum):
    HUE = "h"
    SATURATION = "s"
    VALUE = "v"


class TuyaRequestParam(StrEnum):
    GRANT_TYPE = "grant_type"


class TuyaResponseField(StrEnum):
    MESSAGE = "msg"
    RESULT = "result"
    SUCCESS = "success"


class TuyaSignMethod(StrEnum):
    HMAC_SHA256 = "HMAC-SHA256"


class TuyaSpecField(StrEnum):
    CODE = "code"
    FUNCTIONS = "functions"
    MAX = "max"
    RANGE = "range"
    VALUES = "values"


class TuyaTokenField(StrEnum):
    ACCESS_TOKEN = "access_token"
    EXPIRE_TIME = "expire_time"


class TuyaWorkMode(StrEnum):
    COLOR = "color"
    COLOUR = "colour"

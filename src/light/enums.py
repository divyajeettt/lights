"""Closed string vocabularies for light integrations."""

from enum import StrEnum


class TuyaCommandField(StrEnum):
    CODE = "code"
    COMMANDS = "commands"
    VALUE = "value"


class TuyaEnvVar(StrEnum):
    ACCESS_ID = "TUYA_ACCESS_ID"
    ACCESS_SECRET = "TUYA_ACCESS_SECRET"
    DEVICE_ID = "TUYA_DEVICE_ID"
    DEVICE_IDS = "TUYA_DEVICE_IDS"
    DEVICE_LABELS = "TUYA_DEVICE_LABELS"


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

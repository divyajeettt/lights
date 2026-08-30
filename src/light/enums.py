"""Closed string vocabularies for light integrations."""

from enum import StrEnum


class TinyTuyaEnvVar(StrEnum):
    DEVICE_IDS = "TUYA_DEVICE_IDS"
    DEVICE_IPS = "TUYA_DEVICE_IPS"
    LOCAL_KEYS = "TUYA_LOCAL_KEYS"
    PROTOCOL_VERSIONS = "TUYA_PROTOCOL_VERSIONS"
    DEVICE_LABELS = "TUYA_DEVICE_LABELS"

"""Light backend factory."""

from dataclasses import dataclass

from src.config import ConfigError, env_csv

from .base import GroupLightController, LightController
from .constants import SUPPORTED_TUYA_PROTOCOL_VERSIONS, TINYTUYA_LOCAL_KEY_LENGTH
from .enums import TinyTuyaEnvVar
from .tiny_tuya import TinyTuyaLightController


@dataclass(frozen=True)
class TinyTuyaDeviceConfig:
    device_id: str
    address: str
    local_key: str
    protocol_version: float
    label: str


def configured_tuya_device_ids(required: bool = True) -> list[str]:
    return env_csv(TinyTuyaEnvVar.DEVICE_IDS, required=required)


def configured_tuya_device_labels(device_count: int) -> list[str]:
    labels = env_csv(TinyTuyaEnvVar.DEVICE_LABELS)
    if labels and len(labels) != device_count:
        raise ConfigError("TUYA_DEVICE_LABELS must match the number of Tuya devices")
    if labels:
        return labels
    return [f"bulb {index + 1}" for index in range(device_count)]


def configured_light_count(required: bool = True) -> int:
    return len(configured_tuya_device_ids(required=required)) or 1


def configured_tinytuya_devices() -> list[TinyTuyaDeviceConfig]:
    device_ids = configured_tuya_device_ids(required=True)
    fields = {
        TinyTuyaEnvVar.DEVICE_IPS: env_csv(
            TinyTuyaEnvVar.DEVICE_IPS,
            required=True,
        ),
        TinyTuyaEnvVar.LOCAL_KEYS: env_csv(
            TinyTuyaEnvVar.LOCAL_KEYS,
            required=True,
        ),
        TinyTuyaEnvVar.PROTOCOL_VERSIONS: env_csv(
            TinyTuyaEnvVar.PROTOCOL_VERSIONS,
            required=True,
        ),
    }
    for name, values in fields.items():
        if len(values) != len(device_ids):
            raise ConfigError(
                f"{name} must match the number of entries in "
                f"{TinyTuyaEnvVar.DEVICE_IDS}"
            )

    local_keys = fields[TinyTuyaEnvVar.LOCAL_KEYS]
    for index, local_key in enumerate(local_keys, start=1):
        if len(local_key) != TINYTUYA_LOCAL_KEY_LENGTH:
            raise ConfigError(
                f"TUYA_LOCAL_KEYS entry {index} must contain exactly "
                f"{TINYTUYA_LOCAL_KEY_LENGTH} characters"
            )

    versions = fields[TinyTuyaEnvVar.PROTOCOL_VERSIONS]
    for index, version in enumerate(versions, start=1):
        if version not in SUPPORTED_TUYA_PROTOCOL_VERSIONS:
            supported = ", ".join(sorted(SUPPORTED_TUYA_PROTOCOL_VERSIONS))
            raise ConfigError(
                f"TUYA_PROTOCOL_VERSIONS entry {index} must be one of: {supported}"
            )

    labels = configured_tuya_device_labels(len(device_ids))
    return [
        TinyTuyaDeviceConfig(
            device_id=device_id,
            address=address,
            local_key=local_key,
            protocol_version=float(version),
            label=label,
        )
        for device_id, address, local_key, version, label in zip(
            device_ids,
            fields[TinyTuyaEnvVar.DEVICE_IPS],
            fields[TinyTuyaEnvVar.LOCAL_KEYS],
            versions,
            labels,
            strict=True,
        )
    ]


def build_light_controller() -> LightController:
    controllers = [
        TinyTuyaLightController(
            device_id=config.device_id,
            address=config.address,
            local_key=config.local_key,
            protocol_version=config.protocol_version,
            label=config.label,
        )
        for config in configured_tinytuya_devices()
    ]
    if len(controllers) == 1:
        return controllers[0]
    return GroupLightController(controllers)

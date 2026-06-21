"""Light backend factory."""

from src.config import ConfigError, env, env_csv
from src.enums import LightBackend, LightEnvVar, TuyaEnvVar

from .base import GroupLightController, LightController
from .homeassistant import HomeAssistantLightController
from .tuya import TuyaCloudLightController

INVALID_LIGHT_BACKEND_MESSAGE = "LIGHT_BACKEND must be tuya_cloud or homeassistant"


def configured_tuya_device_ids(required: bool = True) -> list[str]:
    device_ids = env_csv(TuyaEnvVar.DEVICE_IDS)
    if device_ids:
        return device_ids
    device_id = env(TuyaEnvVar.DEVICE_ID, required=required)
    return [device_id] if device_id else []


def configured_tuya_device_labels(device_count: int) -> list[str]:
    labels = env_csv(TuyaEnvVar.DEVICE_LABELS)
    if labels and len(labels) != device_count:
        raise ConfigError("TUYA_DEVICE_LABELS must match the number of Tuya devices")
    if labels:
        return labels
    return [f"bulb {index + 1}" for index in range(device_count)]


def configured_light_count(required: bool = True) -> int:
    raw_backend = env(LightEnvVar.BACKEND, LightBackend.TUYA_CLOUD).lower()
    try:
        backend = LightBackend(raw_backend)
    except ValueError as exc:
        raise ConfigError(INVALID_LIGHT_BACKEND_MESSAGE) from exc

    if backend == LightBackend.TUYA_CLOUD:
        return len(configured_tuya_device_ids(required=required)) or 1
    if backend == LightBackend.HOME_ASSISTANT:
        return 1
    raise ConfigError(INVALID_LIGHT_BACKEND_MESSAGE)


def build_light_controller() -> LightController:
    raw_backend = env(LightEnvVar.BACKEND, LightBackend.TUYA_CLOUD).lower()
    try:
        backend = LightBackend(raw_backend)
    except ValueError as exc:
        raise ConfigError(INVALID_LIGHT_BACKEND_MESSAGE) from exc

    if backend == LightBackend.TUYA_CLOUD:
        device_ids = configured_tuya_device_ids(required=True)
        labels = configured_tuya_device_labels(len(device_ids))
        controllers = [
            TuyaCloudLightController(device_id=device_id, label=label)
            for device_id, label in zip(device_ids, labels, strict=True)
        ]
        if len(controllers) == 1:
            return controllers[0]
        return GroupLightController(controllers)
    if backend == LightBackend.HOME_ASSISTANT:
        return HomeAssistantLightController()
    raise ConfigError(INVALID_LIGHT_BACKEND_MESSAGE)

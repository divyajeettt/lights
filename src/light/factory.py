"""Light backend factory."""

from __future__ import annotations

from src.config import ConfigError, env
from src.enums import LightBackend, LightEnvVar

from .base import LightController
from .homeassistant import HomeAssistantLightController
from .tuya import TuyaCloudLightController

INVALID_LIGHT_BACKEND_MESSAGE = "LIGHT_BACKEND must be tuya_cloud or homeassistant"


def build_light_controller(dry_run: bool) -> LightController | None:
    if dry_run:
        return None
    raw_backend = env(LightEnvVar.BACKEND, LightBackend.TUYA_CLOUD).lower()
    try:
        backend = LightBackend(raw_backend)
    except ValueError as exc:
        raise ConfigError(INVALID_LIGHT_BACKEND_MESSAGE) from exc

    if backend == LightBackend.TUYA_CLOUD:
        return TuyaCloudLightController()
    if backend == LightBackend.HOME_ASSISTANT:
        return HomeAssistantLightController()
    raise ConfigError(INVALID_LIGHT_BACKEND_MESSAGE)

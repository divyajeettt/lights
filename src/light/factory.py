"""Light backend factory."""

from __future__ import annotations

from src.config import ConfigError, env

from .base import LightController
from .homeassistant import HomeAssistantLightController
from .tuya import TuyaCloudLightController


def build_light_controller(dry_run: bool) -> LightController | None:
    if dry_run:
        return None
    backend = env("LIGHT_BACKEND", "tuya_cloud").lower()
    if backend == "tuya_cloud":
        return TuyaCloudLightController()
    if backend == "homeassistant":
        return HomeAssistantLightController()
    raise ConfigError("LIGHT_BACKEND must be tuya_cloud or homeassistant")

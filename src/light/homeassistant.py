"""Home Assistant light backend."""

from __future__ import annotations

from src.config import env
from src.constants import HOME_ASSISTANT_LIGHT_TURN_ON_PATH
from src.enums import (
    HomeAssistantEnvVar,
    HomeAssistantPayloadField,
)
from src.models import Color
from src.spotify import request_json

from .base import LightController


class HomeAssistantLightController(LightController):
    def __init__(self) -> None:
        self.base_url = env(HomeAssistantEnvVar.URL, required=True).rstrip("/")
        self.token = env(HomeAssistantEnvVar.TOKEN, required=True)
        self.entity_id = env(HomeAssistantEnvVar.ENTITY_ID, required=True)

    def set_rgb(self, rgb: Color) -> None:
        url = f"{self.base_url}{HOME_ASSISTANT_LIGHT_TURN_ON_PATH}"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {
            HomeAssistantPayloadField.ENTITY_ID: self.entity_id,
            HomeAssistantPayloadField.RGB_COLOR: list(rgb),
        }
        request_json("POST", url, headers=headers, json=payload)

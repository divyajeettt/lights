"""Home Assistant light backend."""

from __future__ import annotations

from src.config import env
from src.models import Color
from src.spotify import request_json

from .base import LightController


class HomeAssistantLightController(LightController):
    def __init__(self) -> None:
        self.base_url = env("HOME_ASSISTANT_URL", required=True).rstrip("/")
        self.token = env("HOME_ASSISTANT_TOKEN", required=True)
        self.entity_id = env("HOME_ASSISTANT_ENTITY_ID", required=True)

    def set_rgb(self, rgb: Color) -> None:
        url = f"{self.base_url}/api/services/light/turn_on"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"entity_id": self.entity_id, "rgb_color": list(rgb)}
        request_json("POST", url, headers=headers, json=payload)

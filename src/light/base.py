"""Shared light controller interface."""

from __future__ import annotations

from typing import Protocol

from src.models import Color


class LightController(Protocol):
    def set_rgb(self, rgb: Color) -> None:
        """Set the light to an RGB color."""

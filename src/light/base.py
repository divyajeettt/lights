"""Shared light controller interface."""

from typing import Protocol, Sequence

from src.models import Color


class LightController(Protocol):
    @property
    def light_count(self) -> int:
        """Number of physical lights controlled by this instance."""

    @property
    def light_labels(self) -> Sequence[str]:
        """Human-readable labels for controlled lights."""

    def set_rgb(self, rgb: Color) -> None:
        """Set the light to an RGB color."""

    def set_rgbs(self, rgbs: Sequence[Color]) -> None:
        """Set controlled lights to one or more RGB colors."""

    def switch(self) -> None:
        """Toggle the light power state."""


class SingleLightController:
    @property
    def light_count(self) -> int:
        return 1

    @property
    def light_labels(self) -> Sequence[str]:
        return ("bulb-1",)

    def set_rgbs(self, rgbs: Sequence[Color]) -> None:
        if not rgbs:
            raise ValueError("At least one RGB color is required")
        self.set_rgb(rgbs[0])


class GroupLightController:
    def __init__(self, controllers: Sequence[LightController]) -> None:
        if not controllers:
            raise ValueError("At least one light controller is required")
        self.controllers = list(controllers)

    @property
    def light_count(self) -> int:
        return len(self.controllers)

    @property
    def light_labels(self) -> Sequence[str]:
        return tuple(
            label
            for controller in self.controllers
            for label in controller.light_labels[:1]
        )

    def set_rgb(self, rgb: Color) -> None:
        self.set_rgbs([rgb] * self.light_count)

    def set_rgbs(self, rgbs: Sequence[Color]) -> None:
        if not rgbs:
            raise ValueError("At least one RGB color is required")
        errors = []
        for index, controller in enumerate(self.controllers):
            rgb = rgbs[index % len(rgbs)]
            try:
                controller.set_rgb(rgb)
            except Exception as exc:
                errors.append(f"{self.light_labels[index]}: {exc}")
        if errors:
            message = "; ".join(errors)
            raise RuntimeError(f"Failed to update one or more lights: {message}")

    def switch(self) -> None:
        errors = []
        labels = self.light_labels
        for index, controller in enumerate(self.controllers):
            try:
                controller.switch()
            except Exception as exc:
                errors.append(f"{labels[index]}: {exc}")
        if errors:
            message = "; ".join(errors)
            raise RuntimeError(f"Failed to switch one or more lights: {message}")

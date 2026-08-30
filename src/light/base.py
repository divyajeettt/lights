"""Shared light controller interface."""

from concurrent.futures import Future, ThreadPoolExecutor, wait
from typing import Callable, Final, Protocol, Sequence

from src.models import Color

GROUP_LIGHT_OPERATION_TIMEOUT_SECONDS: Final[float] = 10.0


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

    def set_power(self, on: bool) -> None:
        """Set the light power state."""

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

    def _run_concurrently(
        self,
        operation: Callable[[LightController, int], None],
        failure_message: str,
    ) -> None:
        executor = ThreadPoolExecutor(max_workers=self.light_count)
        futures: list[Future[None]] = [
            executor.submit(operation, controller, index)
            for index, controller in enumerate(self.controllers)
        ]
        _, unfinished = wait(
            futures,
            timeout=GROUP_LIGHT_OPERATION_TIMEOUT_SECONDS,
        )

        errors = []
        labels = self.light_labels
        for index, future in enumerate(futures):
            if future in unfinished:
                future.cancel()
                errors.append(
                    f"{labels[index]}: timed out after "
                    f"{GROUP_LIGHT_OPERATION_TIMEOUT_SECONDS:g} seconds"
                )
                continue
            try:
                future.result()
            except Exception as exc:
                errors.append(f"{labels[index]}: {exc}")

        executor.shutdown(wait=False, cancel_futures=True)
        if errors:
            message = "; ".join(errors)
            raise RuntimeError(f"{failure_message}: {message}")

    def set_rgbs(self, rgbs: Sequence[Color]) -> None:
        if not rgbs:
            raise ValueError("At least one RGB color is required")
        self._run_concurrently(
            lambda controller, index: controller.set_rgb(rgbs[index % len(rgbs)]),
            "Failed to update one or more lights",
        )

    def switch(self) -> None:
        self._run_concurrently(
            lambda controller, _index: controller.switch(),
            "Failed to switch one or more lights",
        )

    def set_power(self, on: bool) -> None:
        self._run_concurrently(
            lambda controller, _index: controller.set_power(on),
            "Failed to set power for one or more lights",
        )

"""TinyTuya local-LAN light backend."""

from collections.abc import Callable
from typing import Any

import tinytuya

from src.color import rgb_to_hsv_command
from src.models import Color

from .base import SingleLightController
from .constants import (
    TINYTUYA_HUE_MAX,
    TINYTUYA_SATURATION_VALUE_MAX,
    TINYTUYA_SOCKET_RETRY_LIMIT,
    TINYTUYA_SOCKET_TIMEOUT_SECONDS,
)


class TinyTuyaLightController(SingleLightController):
    def __init__(
        self,
        device_id: str,
        address: str,
        local_key: str,
        protocol_version: float,
        label: str,
    ) -> None:
        self.label = label
        self._local_key = local_key
        self.device = tinytuya.BulbDevice(device_id, address, local_key)
        self.device.set_version(protocol_version)
        self.device.set_socketTimeout(TINYTUYA_SOCKET_TIMEOUT_SECONDS)
        self.device.set_socketRetryLimit(TINYTUYA_SOCKET_RETRY_LIMIT)

    @property
    def light_labels(self) -> tuple[str, ...]:
        return (self.label,)

    def _redact(self, message: str) -> str:
        return message.replace(self._local_key, "[redacted]")

    def _call(self, operation: str, action: Callable[[], Any]) -> Any:
        failure_message = None
        try:
            result = action()
        except Exception as exc:
            failure_message = self._redact(str(exc))

        if failure_message is not None:
            raise RuntimeError(
                f"TinyTuya {operation} failed for {self.label}: {failure_message}"
            ) from None

        if isinstance(result, dict) and result.get("Error"):
            error = self._redact(str(result["Error"]))
            code = result.get("Err")
            suffix = f" (code {code})" if code else ""
            raise RuntimeError(
                f"TinyTuya {operation} failed for {self.label}: {error}{suffix}"
            )
        return result

    def set_rgb(self, rgb: Color) -> None:
        hsv = rgb_to_hsv_command(
            rgb,
            h_max=TINYTUYA_HUE_MAX,
            s_max=TINYTUYA_SATURATION_VALUE_MAX,
            v_max=TINYTUYA_SATURATION_VALUE_MAX,
        )
        self._call(
            "color update",
            lambda: self.device.set_hsv(
                hsv.h / TINYTUYA_HUE_MAX,
                hsv.s / TINYTUYA_SATURATION_VALUE_MAX,
                hsv.v / TINYTUYA_SATURATION_VALUE_MAX,
            ),
        )

    def set_power(self, on: bool) -> None:
        action = self.device.turn_on if on else self.device.turn_off
        operation = "power on" if on else "power off"
        self._call(operation, action)

    def read_state(self) -> dict[str, Any]:
        state = self._call("state read", self.device.state)
        is_on = state.get("is_on") if isinstance(state, dict) else None
        if not isinstance(is_on, bool):
            raise RuntimeError(
                f"TinyTuya state read failed for {self.label}: "
                "response did not contain a boolean is_on value"
            )
        return state

    def switch(self) -> None:
        state = self.read_state()
        is_on = state["is_on"]
        self.set_power(not is_on)

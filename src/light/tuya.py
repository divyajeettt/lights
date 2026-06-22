"""Tuya Cloud light backend."""

import hashlib
import hmac
import json
import time
import urllib.parse
import uuid
from dataclasses import dataclass
from typing import Any

import requests

from src.color import rgb_to_hsv_command
from src.config import ConfigError, env
from src.models import Color

from .base import SingleLightController
from .constants import (
    TUYA_COLOR_CODE_CANDIDATES,
    TUYA_COLOR_CODE_V2_SUFFIX,
    TUYA_DEFAULT_HUE_MAX,
    TUYA_DEFAULT_SATURATION_VALUE_MAX,
    TUYA_DEVICE_COMMANDS_PATH,
    TUYA_DEVICE_SPECIFICATIONS_PATH,
    TUYA_DEVICE_STATUS_PATH,
    TUYA_ENDPOINT,
    TUYA_TOKEN_PATH,
    TUYA_V2_SATURATION_VALUE_MAX,
)
from .enums import (
    TuyaCommandField,
    TuyaEnvVar,
    TuyaHeader,
    TuyaHsvField,
    TuyaRequestParam,
    TuyaResponseField,
    TuyaSignMethod,
    TuyaSpecField,
    TuyaTokenField,
)


def now_ms() -> int:
    return int(time.time() * 1000)


def json_dumps(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


class TuyaCloudClient:
    def __init__(self, device_id: str | None = None) -> None:
        self.endpoint = TUYA_ENDPOINT.rstrip("/")
        self.access_id = env(TuyaEnvVar.ACCESS_ID, required=True)
        self.access_secret = env(TuyaEnvVar.ACCESS_SECRET, required=True)
        self.device_id = device_id or env(TuyaEnvVar.DEVICE_ID, required=True)
        self.access_token = ""
        self.expires_at = 0

    def _make_url_path(
        self,
        path: str,
        params: dict[str, Any] | None = None,
    ) -> str:
        if not params:
            return path
        query = urllib.parse.urlencode(
            sorted((key, str(value)) for key, value in params.items())
        )
        return f"{path}?{query}"

    def _sign(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None,
        body: str,
        access_token: str = "",
    ) -> dict[str, str]:
        timestamp = str(now_ms())
        nonce = uuid.uuid4().hex
        url_path = self._make_url_path(path, params)
        content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
        string_to_sign = f"{method.upper()}\n{content_hash}\n\n{url_path}"
        sign_input = f"{self.access_id}{access_token}{timestamp}{nonce}{string_to_sign}"
        sign = (
            hmac.new(
                self.access_secret.encode("utf-8"),
                sign_input.encode("utf-8"),
                hashlib.sha256,
            )
            .hexdigest()
            .upper()
        )
        headers = {
            TuyaHeader.CLIENT_ID: self.access_id,
            TuyaHeader.SIGN: sign,
            TuyaHeader.TIMESTAMP: timestamp,
            TuyaHeader.NONCE: nonce,
            TuyaHeader.SIGN_METHOD: TuyaSignMethod.HMAC_SHA256,
            "Content-Type": "application/json",
        }
        if access_token:
            headers[TuyaHeader.ACCESS_TOKEN] = access_token
        return headers

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        use_token: bool = True,
    ) -> Any:
        body = "" if payload is None else json_dumps(payload)
        token = self.get_token() if use_token else ""
        headers = self._sign(method, path, params, body, token)
        url = f"{self.endpoint}{self._make_url_path(path, params)}"
        response = requests.request(
            method,
            url,
            headers=headers,
            data=body or None,
            timeout=20,
        )
        try:
            data = response.json()
        except ValueError:
            data = {
                TuyaResponseField.SUCCESS: False,
                TuyaResponseField.MESSAGE: response.text,
            }
        if response.status_code >= 400 or not data.get(
            TuyaResponseField.SUCCESS,
            False,
        ):
            raise RuntimeError(f"Tuya API failed: HTTP {response.status_code}: {data}")
        return data.get(TuyaResponseField.RESULT)

    def get_token(self) -> str:
        if self.access_token and self.expires_at > now_ms() + 60_000:
            return self.access_token
        result = self.request(
            "GET",
            TUYA_TOKEN_PATH,
            params={TuyaRequestParam.GRANT_TYPE: 1},
            payload=None,
            use_token=False,
        )
        self.access_token = result[TuyaTokenField.ACCESS_TOKEN]
        expire_seconds = int(result.get(TuyaTokenField.EXPIRE_TIME, 7200))
        self.expires_at = now_ms() + expire_seconds * 1000
        return self.access_token

    def device_specification(self) -> dict[str, Any]:
        return self.request(
            "GET",
            TUYA_DEVICE_SPECIFICATIONS_PATH.format(device_id=self.device_id),
        )

    def device_status(self) -> list[dict[str, Any]]:
        return self.request(
            "GET",
            TUYA_DEVICE_STATUS_PATH.format(device_id=self.device_id),
        )

    def send_commands(self, commands: list[dict[str, Any]]) -> Any:
        return self.request(
            "POST",
            TUYA_DEVICE_COMMANDS_PATH.format(device_id=self.device_id),
            payload={TuyaCommandField.COMMANDS: commands},
        )


@dataclass
class TuyaLightSpec:
    color_code: str
    h_max: int
    s_max: int
    v_max: int


def _parse_values(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def _value_max(values: dict[str, Any], key: str, default: int) -> int:
    value = values.get(key)
    if isinstance(value, dict):
        return int(value.get(TuyaSpecField.MAX, default))
    return default


def infer_tuya_light_spec(specification: dict[str, Any]) -> TuyaLightSpec:
    functions = specification.get(TuyaSpecField.FUNCTIONS, [])
    by_code = {
        item.get(TuyaSpecField.CODE): item
        for item in functions
        if item.get(TuyaSpecField.CODE)
    }

    color_code = next((c for c in TUYA_COLOR_CODE_CANDIDATES if c in by_code), None)
    if not color_code:
        raise ConfigError(
            "Could not infer Tuya color command from the device specification."
        )

    values = _parse_values(by_code.get(color_code, {}).get(TuyaSpecField.VALUES))
    h_max = _value_max(values, TuyaHsvField.HUE, TUYA_DEFAULT_HUE_MAX)
    if isinstance(values.get(TuyaHsvField.SATURATION), dict) or isinstance(
        values.get(TuyaHsvField.VALUE),
        dict,
    ):
        s_max = _value_max(
            values,
            TuyaHsvField.SATURATION,
            TUYA_DEFAULT_SATURATION_VALUE_MAX,
        )
        v_max = _value_max(
            values,
            TuyaHsvField.VALUE,
            TUYA_DEFAULT_SATURATION_VALUE_MAX,
        )
    elif color_code.endswith(TUYA_COLOR_CODE_V2_SUFFIX):
        s_max = v_max = TUYA_V2_SATURATION_VALUE_MAX
    else:
        s_max = v_max = TUYA_DEFAULT_SATURATION_VALUE_MAX

    return TuyaLightSpec(
        color_code=color_code,
        h_max=h_max,
        s_max=s_max,
        v_max=v_max,
    )


class TuyaCloudLightController(SingleLightController):
    def __init__(self, device_id: str | None = None, label: str | None = None) -> None:
        self.client = TuyaCloudClient(device_id=device_id)
        self.label = label or self.client.device_id
        self.spec = infer_tuya_light_spec(self.client.device_specification())

    @property
    def light_labels(self) -> tuple[str, ...]:
        return (self.label,)

    def set_rgb(self, rgb: Color) -> None:
        hsv = rgb_to_hsv_command(
            rgb,
            h_max=self.spec.h_max,
            s_max=self.spec.s_max,
            v_max=self.spec.v_max,
        )
        color_value: dict[str, int] | str = {
            TuyaHsvField.HUE: hsv.h,
            TuyaHsvField.SATURATION: hsv.s,
            TuyaHsvField.VALUE: hsv.v,
        }
        self.client.send_commands(
            [
                {
                    TuyaCommandField.CODE: self.spec.color_code,
                    TuyaCommandField.VALUE: color_value,
                }
            ]
        )

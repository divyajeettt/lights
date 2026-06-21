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
from src.config import ConfigError, env, env_bool, env_float
from src.constants import (
    DEFAULT_TUYA_BRIGHTNESS_SCALE,
    DEFAULT_TUYA_ENDPOINT,
    DEFAULT_TUYA_MIN_VALUE_PERCENT,
    TUYA_COLOR_CODE_CANDIDATES,
    TUYA_COLOR_CODE_V2_SUFFIX,
    TUYA_DEFAULT_HUE_MAX,
    TUYA_DEFAULT_SATURATION_VALUE_MAX,
    TUYA_DEVICE_COMMANDS_PATH,
    TUYA_DEVICE_SPECIFICATIONS_PATH,
    TUYA_DEVICE_STATUS_PATH,
    TUYA_SWITCH_CODE_CANDIDATES,
    TUYA_TOKEN_PATH,
    TUYA_V2_SATURATION_VALUE_MAX,
    TUYA_WORK_MODE_CODE_CANDIDATES,
)
from src.enums import (
    TuyaColorValueFormat,
    TuyaCommandField,
    TuyaEnvVar,
    TuyaHeader,
    TuyaHsvField,
    TuyaRequestParam,
    TuyaResponseField,
    TuyaSignMethod,
    TuyaSpecField,
    TuyaTokenField,
    TuyaWorkMode,
)
from src.models import Color

from .base import SingleLightController


def now_ms() -> int:
    return int(time.time() * 1000)


def json_dumps(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


class TuyaCloudClient:
    def __init__(self, device_id: str | None = None) -> None:
        self.endpoint = env(TuyaEnvVar.ENDPOINT, DEFAULT_TUYA_ENDPOINT).rstrip("/")
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
    switch_code: str | None
    work_mode_code: str | None
    work_mode_value: str | None
    color_code: str
    h_max: int
    s_max: int
    v_max: int
    color_value_format: str


def _parse_values(raw: Any) -> dict[str, Any]:
    if isinstance(raw, dict):
        return raw
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def _first_auto(value: str, empty: str | None = None) -> str | None:
    if not value or value.lower() == TuyaColorValueFormat.AUTO:
        return empty
    return value


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

    switch_override = _first_auto(
        env(TuyaEnvVar.SWITCH_CODE, TuyaColorValueFormat.AUTO)
    )
    mode_override = _first_auto(
        env(TuyaEnvVar.WORK_MODE_CODE, TuyaColorValueFormat.AUTO)
    )
    color_override = _first_auto(env(TuyaEnvVar.COLOR_CODE, TuyaColorValueFormat.AUTO))
    format_override = _first_auto(
        env(TuyaEnvVar.COLOR_VALUE_FORMAT, TuyaColorValueFormat.AUTO)
    )

    switch_code = switch_override
    if not switch_code:
        for candidate in TUYA_SWITCH_CODE_CANDIDATES:
            if candidate in by_code:
                switch_code = candidate
                break

    work_mode_code = mode_override
    work_mode_value = env(TuyaEnvVar.WORK_MODE_VALUE, "")
    if not work_mode_code:
        for candidate in TUYA_WORK_MODE_CODE_CANDIDATES:
            if candidate in by_code:
                work_mode_code = candidate
                break
    if work_mode_code and not work_mode_value:
        values = _parse_values(
            by_code.get(work_mode_code, {}).get(TuyaSpecField.VALUES)
        )
        mode_range = values.get(TuyaSpecField.RANGE, [])
        if TuyaWorkMode.COLOUR in mode_range:
            work_mode_value = TuyaWorkMode.COLOUR
        elif TuyaWorkMode.COLOR in mode_range:
            work_mode_value = TuyaWorkMode.COLOR
        else:
            work_mode_value = TuyaWorkMode.COLOUR

    color_code = color_override
    if not color_code:
        for candidate in TUYA_COLOR_CODE_CANDIDATES:
            if candidate in by_code:
                color_code = candidate
                break
    if not color_code:
        raise ConfigError(
            "Could not infer Tuya color command. Set TUYA_COLOR_CODE in .env."
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

    raw_value_format = format_override or TuyaColorValueFormat.OBJECT
    try:
        value_format = TuyaColorValueFormat(raw_value_format)
    except ValueError as exc:
        raise ConfigError(
            "TUYA_COLOR_VALUE_FORMAT must be auto, object, or string"
        ) from exc
    if value_format == TuyaColorValueFormat.AUTO:
        value_format = TuyaColorValueFormat.OBJECT

    return TuyaLightSpec(
        switch_code=switch_code,
        work_mode_code=work_mode_code,
        work_mode_value=work_mode_value or None,
        color_code=color_code,
        h_max=h_max,
        s_max=s_max,
        v_max=v_max,
        color_value_format=value_format,
    )


class TuyaCloudLightController(SingleLightController):
    def __init__(self, device_id: str | None = None, label: str | None = None) -> None:
        self.client = TuyaCloudClient(device_id=device_id)
        self.label = label or self.client.device_id
        self.spec = infer_tuya_light_spec(self.client.device_specification())
        self.min_value_percent = env_float(
            TuyaEnvVar.MIN_VALUE_PERCENT,
            DEFAULT_TUYA_MIN_VALUE_PERCENT,
        )
        self.brightness_scale = env_float(
            TuyaEnvVar.BRIGHTNESS_SCALE,
            DEFAULT_TUYA_BRIGHTNESS_SCALE,
        )
        if self.brightness_scale < 0:
            raise ValueError("TUYA_BRIGHTNESS_SCALE must be greater than or equal to 0")
        self.ensure_on_color_mode = env_bool(TuyaEnvVar.ENSURE_ON_COLOR_MODE, False)

    @property
    def light_labels(self) -> tuple[str, ...]:
        return (self.label,)

    def set_rgb(self, rgb: Color) -> None:
        hsv = rgb_to_hsv_command(
            rgb,
            h_max=self.spec.h_max,
            s_max=self.spec.s_max,
            v_max=self.spec.v_max,
            min_value_percent=self.min_value_percent,
            brightness_scale=self.brightness_scale,
        )
        color_value: dict[str, int] | str = {
            TuyaHsvField.HUE: hsv.h,
            TuyaHsvField.SATURATION: hsv.s,
            TuyaHsvField.VALUE: hsv.v,
        }
        if self.spec.color_value_format == TuyaColorValueFormat.STRING:
            color_value = json_dumps(color_value)

        commands: list[dict[str, Any]] = []
        if self.ensure_on_color_mode:
            if self.spec.switch_code:
                commands.append(
                    {
                        TuyaCommandField.CODE: self.spec.switch_code,
                        TuyaCommandField.VALUE: True,
                    }
                )
            if self.spec.work_mode_code and self.spec.work_mode_value:
                commands.append(
                    {
                        TuyaCommandField.CODE: self.spec.work_mode_code,
                        TuyaCommandField.VALUE: self.spec.work_mode_value,
                    }
                )
        commands.append(
            {
                TuyaCommandField.CODE: self.spec.color_code,
                TuyaCommandField.VALUE: color_value,
            }
        )
        self.client.send_commands(commands)

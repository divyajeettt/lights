#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import colorsys
import hashlib
import hmac
import json
import os
import secrets
import sys
import time
import urllib.parse
import uuid
import webbrowser
from dataclasses import dataclass
from http.server import BaseHTTPRequestHandler, HTTPServer
from io import BytesIO
from pathlib import Path
from typing import Any

import requests
from PIL import Image


SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_SCOPE = "user-read-currently-playing user-read-playback-state"


class ConfigError(RuntimeError):
    pass


class SpotifyRateLimitError(RuntimeError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(f"Spotify rate limited the request; retrying after {retry_after}s")
        self.retry_after = retry_after


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value or ""


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return float(value)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"{name} must be true or false")


def validate_spotify_client_id(client_id: str) -> None:
    value = client_id.strip()
    if value in {"your_spotify_client_id", "your_spotify_client_id_here"}:
        raise ConfigError(
            "SPOTIFY_CLIENT_ID is still the placeholder. Use the Client ID from "
            "https://developer.spotify.com/dashboard, not your Spotify username or password."
        )
    if "@" in value or " " in value or ":" in value:
        raise ConfigError(
            "SPOTIFY_CLIENT_ID does not look like a Spotify Developer app Client ID. "
            "It should be the public Client ID from the Spotify Developer Dashboard."
        )
    if len(value) != 32 or not value.isalnum():
        raise ConfigError(
            f"SPOTIFY_CLIENT_ID has length {len(value)}. Spotify Client IDs are normally "
            "32 alphanumeric characters from the Spotify Developer Dashboard."
        )


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def now_ms() -> int:
    return int(time.time() * 1000)


def json_dumps(data: Any) -> str:
    return json.dumps(data, separators=(",", ":"), ensure_ascii=False)


def parse_rgb(value: str) -> tuple[int, int, int]:
    cleaned = value.strip().lstrip("#")
    if len(cleaned) != 6:
        raise ValueError("RGB color must look like #00aaff")
    return tuple(int(cleaned[i : i + 2], 16) for i in (0, 2, 4))


def rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def relative_luminance(rgb: tuple[int, int, int]) -> float:
    r, g, b = rgb
    return (0.2126 * r + 0.7152 * g + 0.0722 * b) / 255


def rgb_saturation(rgb: tuple[int, int, int]) -> float:
    r, g, b = (channel / 255 for channel in rgb)
    return colorsys.rgb_to_hsv(r, g, b)[1]


def is_usable_album_color(rgb: tuple[int, int, int], min_luminance: float, min_saturation: float) -> bool:
    return relative_luminance(rgb) >= min_luminance and rgb_saturation(rgb) >= min_saturation


def image_pixel_data(image: Image.Image) -> Any:
    if hasattr(image, "get_flattened_data"):
        return image.get_flattened_data()
    return image.getdata()


def parse_retry_after(headers: Any) -> int:
    value = headers.get("Retry-After", "5")
    try:
        retry_after = int(value)
    except (TypeError, ValueError):
        retry_after = 5
    return max(1, retry_after)


def request_json(method: str, url: str, **kwargs: Any) -> Any:
    response = requests.request(method, url, timeout=20, **kwargs)
    if response.status_code == 204:
        return None
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    if response.status_code >= 400:
        raise RuntimeError(f"{method} {url} failed: HTTP {response.status_code}: {payload}")
    return payload


class SpotifyCallbackHandler(BaseHTTPRequestHandler):
    server_version = "SpotifyCallback/1.0"

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = params.get("code", [""])[0]  # type: ignore[attr-defined]
        self.server.auth_state = params.get("state", [""])[0]  # type: ignore[attr-defined]
        self.server.auth_error = params.get("error", [""])[0]  # type: ignore[attr-defined]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Spotify authorization received.</h1>"
            b"<p>You can close this tab and return to the terminal.</p></body></html>"
        )

    def log_message(self, format: str, *args: Any) -> None:
        return


class SpotifyClient:
    def __init__(self, client_id: str, redirect_uri: str, cache_file: Path, open_browser: bool = True):
        self.client_id = client_id
        self.redirect_uri = redirect_uri
        self.cache_file = cache_file
        self.open_browser = open_browser
        self.token: dict[str, Any] = self._load_token()

    def _load_token(self) -> dict[str, Any]:
        if not self.cache_file.exists():
            return {}
        try:
            return json.loads(self.cache_file.read_text())
        except ValueError:
            return {}

    def _save_token(self, token: dict[str, Any]) -> None:
        token["expires_at"] = int(time.time()) + int(token.get("expires_in", 3600)) - 60
        if "refresh_token" not in token and self.token.get("refresh_token"):
            token["refresh_token"] = self.token["refresh_token"]
        ensure_parent(self.cache_file)
        self.cache_file.write_text(json.dumps(token, indent=2, sort_keys=True))
        self.token = token

    def access_token(self) -> str:
        if self.token.get("access_token") and int(self.token.get("expires_at", 0)) > int(time.time()):
            return self.token["access_token"]
        if self.token.get("refresh_token"):
            self._refresh_token()
            return self.token["access_token"]
        self._authorize()
        return self.token["access_token"]

    def _refresh_token(self) -> None:
        payload = {
            "grant_type": "refresh_token",
            "refresh_token": self.token["refresh_token"],
            "client_id": self.client_id,
        }
        token = request_json("POST", SPOTIFY_TOKEN_URL, data=payload)
        self._save_token(token)

    def _authorize(self) -> None:
        parsed = urllib.parse.urlparse(self.redirect_uri)
        if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost"}:
            raise ConfigError("SPOTIFY_REDIRECT_URI must be a localhost HTTP URL for this script")

        code_verifier = secrets.token_urlsafe(64)
        challenge = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("=")
        state = secrets.token_urlsafe(24)
        query = urllib.parse.urlencode(
            {
                "client_id": self.client_id,
                "response_type": "code",
                "redirect_uri": self.redirect_uri,
                "scope": SPOTIFY_SCOPE,
                "state": state,
                "code_challenge_method": "S256",
                "code_challenge": code_challenge,
            }
        )
        auth_url = f"{SPOTIFY_AUTH_URL}?{query}"

        host = parsed.hostname or "127.0.0.1"
        port = parsed.port or 80
        server = HTTPServer((host, port), SpotifyCallbackHandler)
        server.auth_code = ""  # type: ignore[attr-defined]
        server.auth_state = ""  # type: ignore[attr-defined]
        server.auth_error = ""  # type: ignore[attr-defined]

        print("Open this URL to authorize Spotify:")
        print(auth_url)
        if self.open_browser:
            webbrowser.open(auth_url)

        while not server.auth_code and not server.auth_error:  # type: ignore[attr-defined]
            server.handle_request()

        if server.auth_error:  # type: ignore[attr-defined]
            raise RuntimeError(f"Spotify authorization failed: {server.auth_error}")  # type: ignore[attr-defined]
        if server.auth_state != state:  # type: ignore[attr-defined]
            raise RuntimeError("Spotify authorization failed: state mismatch")

        payload = {
            "client_id": self.client_id,
            "grant_type": "authorization_code",
            "code": server.auth_code,  # type: ignore[attr-defined]
            "redirect_uri": self.redirect_uri,
            "code_verifier": code_verifier,
        }
        token = request_json("POST", SPOTIFY_TOKEN_URL, data=payload)
        self._save_token(token)

    def currently_playing(self) -> dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {self.access_token()}"}
        params = {"additional_types": "track"}
        response = requests.get(
            SPOTIFY_CURRENTLY_PLAYING_URL,
            headers=headers,
            params=params,
            timeout=20,
        )
        if response.status_code == 204:
            return None
        if response.status_code == 401 and self.token.get("refresh_token"):
            self._refresh_token()
            headers = {"Authorization": f"Bearer {self.token['access_token']}"}
            response = requests.get(
                SPOTIFY_CURRENTLY_PLAYING_URL,
                headers=headers,
                params=params,
                timeout=20,
            )
        if response.status_code == 429:
            raise SpotifyRateLimitError(parse_retry_after(response.headers))
        if response.status_code >= 400:
            raise RuntimeError(f"Spotify currently-playing failed: HTTP {response.status_code}: {response.text}")
        return response.json()


def album_rgb_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
    fallback_rgb: tuple[int, int, int] | None = None,
) -> tuple[tuple[int, int, int], bool]:
    if min_luminance is None:
        min_luminance = env_float("ALBUM_COLOR_MIN_LUMINANCE", 0.08)
    if min_saturation is None:
        min_saturation = env_float("ALBUM_COLOR_MIN_SATURATION", 0.12)
    if fallback_rgb is None:
        fallback_rgb = parse_rgb(env("ALBUM_COLOR_FALLBACK", "#ff6600"))

    image = Image.open(BytesIO(image_bytes)).convert("RGBA")
    image.thumbnail((160, 160), Image.Resampling.LANCZOS)

    pixels = []
    for r, g, b, a in image_pixel_data(image):
        if a < 128:
            continue
        pixels.append((r, g, b))
    if not pixels:
        raise RuntimeError("Album art image had no visible pixels")

    rgb_image = Image.new("RGB", (len(pixels), 1))
    rgb_image.putdata(pixels)
    palette = rgb_image.quantize(colors=colors, method=Image.Quantize.MEDIANCUT)
    counts = palette.getcolors(maxcolors=colors)
    if not counts:
        raise RuntimeError("Could not quantize album art")
    pal = palette.getpalette()

    candidates = []
    for count, palette_index in counts:
        offset = palette_index * 3
        rgb = (pal[offset], pal[offset + 1], pal[offset + 2])
        if is_usable_album_color(rgb, min_luminance, min_saturation):
            candidates.append((count, rgb))

    if not candidates:
        return fallback_rgb, True

    return max(candidates, key=lambda item: item[0])[1], False


def dominant_rgb_from_image_bytes(
    image_bytes: bytes,
    colors: int = 16,
    min_luminance: float | None = None,
    min_saturation: float | None = None,
    fallback_rgb: tuple[int, int, int] | None = None,
) -> tuple[int, int, int]:
    rgb, _ = album_rgb_from_image_bytes(
        image_bytes,
        colors=colors,
        min_luminance=min_luminance,
        min_saturation=min_saturation,
        fallback_rgb=fallback_rgb,
    )
    return rgb


def album_rgb_from_url(image_url: str) -> tuple[tuple[int, int, int], bool]:
    response = requests.get(image_url, timeout=20)
    response.raise_for_status()
    return album_rgb_from_image_bytes(response.content)


def dominant_rgb_from_url(image_url: str) -> tuple[int, int, int]:
    rgb, _ = album_rgb_from_url(image_url)
    return rgb


@dataclass
class HsvCommand:
    h: int
    s: int
    v: int


@dataclass(frozen=True)
class TrackSummary:
    track_id: str
    label: str
    item: dict[str, Any]


@dataclass(frozen=True)
class TrackColor:
    track_id: str
    label: str
    rgb: tuple[int, int, int]
    fallback_used: bool = False


def rgb_to_hsv_command(
    rgb: tuple[int, int, int],
    h_max: int = 360,
    s_max: int = 255,
    v_max: int = 255,
    min_value_percent: float = 35.0,
) -> HsvCommand:
    r, g, b = (channel / 255 for channel in rgb)
    h, s, v = colorsys.rgb_to_hsv(r, g, b)
    min_v = int(round(v_max * (min_value_percent / 100)))
    hue = int(round(h * h_max))
    if hue >= h_max:
        hue = 0
    sat = max(1, int(round(s * s_max)))
    val = max(min_v, int(round(v * v_max)))
    return HsvCommand(h=hue, s=sat, v=val)


class LightController:
    def set_rgb(self, rgb: tuple[int, int, int]) -> None:
        raise NotImplementedError


class HomeAssistantLightController(LightController):
    def __init__(self) -> None:
        self.base_url = env("HOME_ASSISTANT_URL", required=True).rstrip("/")
        self.token = env("HOME_ASSISTANT_TOKEN", required=True)
        self.entity_id = env("HOME_ASSISTANT_ENTITY_ID", required=True)

    def set_rgb(self, rgb: tuple[int, int, int]) -> None:
        url = f"{self.base_url}/api/services/light/turn_on"
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json",
        }
        payload = {"entity_id": self.entity_id, "rgb_color": list(rgb)}
        request_json("POST", url, headers=headers, json=payload)


class TuyaCloudClient:
    def __init__(self) -> None:
        self.endpoint = env("TUYA_ENDPOINT", "https://openapi.tuyain.com").rstrip("/")
        self.access_id = env("TUYA_ACCESS_ID", required=True)
        self.access_secret = env("TUYA_ACCESS_SECRET", required=True)
        self.device_id = env("TUYA_DEVICE_ID", required=True)
        self.access_token = ""
        self.expires_at = 0

    def _make_url_path(self, path: str, params: dict[str, Any] | None = None) -> str:
        if not params:
            return path
        query = urllib.parse.urlencode(sorted((key, str(value)) for key, value in params.items()))
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
        sign = hmac.new(
            self.access_secret.encode("utf-8"),
            sign_input.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest().upper()
        headers = {
            "client_id": self.access_id,
            "sign": sign,
            "t": timestamp,
            "nonce": nonce,
            "sign_method": "HMAC-SHA256",
            "Content-Type": "application/json",
        }
        if access_token:
            headers["access_token"] = access_token
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
        response = requests.request(method, url, headers=headers, data=body or None, timeout=20)
        try:
            data = response.json()
        except ValueError:
            data = {"success": False, "msg": response.text}
        if response.status_code >= 400 or not data.get("success", False):
            raise RuntimeError(f"Tuya API failed: HTTP {response.status_code}: {data}")
        return data.get("result")

    def get_token(self) -> str:
        if self.access_token and self.expires_at > now_ms() + 60_000:
            return self.access_token
        result = self.request(
            "GET",
            "/v1.0/token",
            params={"grant_type": 1},
            payload=None,
            use_token=False,
        )
        self.access_token = result["access_token"]
        expire_seconds = int(result.get("expire_time", 7200))
        self.expires_at = now_ms() + expire_seconds * 1000
        return self.access_token

    def device_specification(self) -> dict[str, Any]:
        return self.request("GET", f"/v1.0/devices/{self.device_id}/specifications")

    def device_status(self) -> list[dict[str, Any]]:
        return self.request("GET", f"/v1.0/devices/{self.device_id}/status")

    def send_commands(self, commands: list[dict[str, Any]]) -> Any:
        return self.request(
            "POST",
            f"/v1.0/devices/{self.device_id}/commands",
            payload={"commands": commands},
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
    if not value or value.lower() == "auto":
        return empty
    return value


def _value_max(values: dict[str, Any], key: str, default: int) -> int:
    value = values.get(key)
    if isinstance(value, dict):
        return int(value.get("max", default))
    return default


def infer_tuya_light_spec(specification: dict[str, Any]) -> TuyaLightSpec:
    functions = specification.get("functions", [])
    by_code = {item.get("code"): item for item in functions if item.get("code")}

    switch_override = _first_auto(env("TUYA_SWITCH_CODE", "auto"))
    mode_override = _first_auto(env("TUYA_WORK_MODE_CODE", "auto"))
    color_override = _first_auto(env("TUYA_COLOR_CODE", "auto"))
    format_override = _first_auto(env("TUYA_COLOR_VALUE_FORMAT", "auto"))

    switch_code = switch_override
    if not switch_code:
        for candidate in ("switch_led", "switch", "switch_1"):
            if candidate in by_code:
                switch_code = candidate
                break

    work_mode_code = mode_override
    work_mode_value = env("TUYA_WORK_MODE_VALUE", "")
    if not work_mode_code:
        for candidate in ("work_mode", "mode"):
            if candidate in by_code:
                work_mode_code = candidate
                break
    if work_mode_code and not work_mode_value:
        values = _parse_values(by_code.get(work_mode_code, {}).get("values"))
        mode_range = values.get("range", [])
        if "colour" in mode_range:
            work_mode_value = "colour"
        elif "color" in mode_range:
            work_mode_value = "color"
        else:
            work_mode_value = "colour"

    color_code = color_override
    if not color_code:
        for candidate in ("colour_data_v2", "colour_data", "color_data", "colour_data_hsv"):
            if candidate in by_code:
                color_code = candidate
                break
    if not color_code:
        raise ConfigError(
            "Could not infer Tuya color command. Run --print-tuya-spec and set TUYA_COLOR_CODE."
        )

    values = _parse_values(by_code.get(color_code, {}).get("values"))
    h_max = _value_max(values, "h", 360)
    if isinstance(values.get("s"), dict) or isinstance(values.get("v"), dict):
        s_max = _value_max(values, "s", 255)
        v_max = _value_max(values, "v", 255)
    elif color_code.endswith("_v2"):
        s_max = 1000
        v_max = 1000
    else:
        s_max = 255
        v_max = 255

    value_format = format_override or "object"
    if value_format not in {"auto", "object", "string"}:
        raise ConfigError("TUYA_COLOR_VALUE_FORMAT must be auto, object, or string")
    if value_format == "auto":
        value_format = "object"

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


class TuyaCloudLightController(LightController):
    def __init__(self) -> None:
        self.client = TuyaCloudClient()
        self.spec = infer_tuya_light_spec(self.client.device_specification())
        self.min_value_percent = env_float("TUYA_MIN_VALUE_PERCENT", 35.0)
        self.ensure_on_color_mode = env_bool("TUYA_ENSURE_ON_COLOR_MODE", False)

    def set_rgb(self, rgb: tuple[int, int, int]) -> None:
        hsv = rgb_to_hsv_command(
            rgb,
            h_max=self.spec.h_max,
            s_max=self.spec.s_max,
            v_max=self.spec.v_max,
            min_value_percent=self.min_value_percent,
        )
        color_value: dict[str, int] | str = {"h": hsv.h, "s": hsv.s, "v": hsv.v}
        if self.spec.color_value_format == "string":
            color_value = json_dumps(color_value)

        commands: list[dict[str, Any]] = []
        if self.ensure_on_color_mode:
            if self.spec.switch_code:
                commands.append({"code": self.spec.switch_code, "value": True})
            if self.spec.work_mode_code and self.spec.work_mode_value:
                commands.append({"code": self.spec.work_mode_code, "value": self.spec.work_mode_value})
        commands.append({"code": self.spec.color_code, "value": color_value})

        self.client.send_commands(commands)


def build_light_controller(dry_run: bool) -> LightController | None:
    if dry_run:
        return None
    backend = env("LIGHT_BACKEND", "tuya_cloud").lower()
    if backend == "tuya_cloud":
        return TuyaCloudLightController()
    if backend == "homeassistant":
        return HomeAssistantLightController()
    raise ConfigError("LIGHT_BACKEND must be tuya_cloud or homeassistant")


def best_album_image(item: dict[str, Any]) -> str | None:
    images = item.get("album", {}).get("images", [])
    if not images:
        return None
    return max(images, key=lambda image: image.get("width", 0) * image.get("height", 0)).get("url")


def track_label(item: dict[str, Any]) -> str:
    name = item.get("name", "Unknown track")
    artists = ", ".join(artist.get("name", "Unknown artist") for artist in item.get("artists", []))
    return f"{name} - {artists}" if artists else name


def current_track_summary(spotify: SpotifyClient, quiet: bool = False) -> TrackSummary | None:
    playback = spotify.currently_playing()
    if not playback or not playback.get("is_playing"):
        if not quiet:
            print("Spotify is not currently playing.")
        return None

    item = playback.get("item") or {}
    if item.get("type") != "track":
        if not quiet:
            print(f"Currently playing item is not a track: {item.get('type')}")
        return None

    track_id = item.get("id") or item.get("uri")
    if not track_id:
        if not quiet:
            print("Currently playing track has no Spotify ID.")
        return None

    return TrackSummary(track_id=track_id, label=track_label(item), item=item)


def track_color_from_summary(summary: TrackSummary) -> TrackColor | None:
    image_url = best_album_image(summary.item)
    if not image_url:
        print(f"No album image for {summary.label}")
        return None
    rgb, fallback_used = album_rgb_from_url(image_url)
    return TrackColor(
        track_id=summary.track_id,
        label=summary.label,
        rgb=rgb,
        fallback_used=fallback_used,
    )


def current_track_color(spotify: SpotifyClient, quiet: bool = False) -> TrackColor | None:
    summary = current_track_summary(spotify, quiet=quiet)
    if not summary:
        return None
    return track_color_from_summary(summary)


def send_or_log_rgb(
    controller: LightController | None,
    rgb: tuple[int, int, int],
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"Dry run: would set bulb to {rgb_hex(rgb)}")
        return
    if controller:
        controller.set_rgb(rgb)


def apply_track_color(
    controller: LightController | None,
    track: TrackColor,
    dry_run: bool,
) -> None:
    suffix = " (fallback color)" if track.fallback_used else ""
    print(f"{track.label} -> {rgb_hex(track.rgb)}{suffix}")
    send_or_log_rgb(controller, track.rgb, dry_run)
    if not dry_run:
        print("Bulb color updated.")


def build_spotify(open_browser: bool) -> SpotifyClient:
    client_id = env("SPOTIFY_CLIENT_ID", required=True)
    validate_spotify_client_id(client_id)
    redirect_uri = env("SPOTIFY_REDIRECT_URI", "http://127.0.0.1:8888/callback")
    cache_file = Path(env("SPOTIFY_CACHE_FILE", ".cache/spotify_token.json"))
    return SpotifyClient(client_id, redirect_uri, cache_file, open_browser=open_browser)


def print_tuya_spec() -> None:
    client = TuyaCloudClient()
    spec = client.device_specification()
    print(json.dumps(spec, indent=2, sort_keys=True))
    inferred = infer_tuya_light_spec(spec)
    print("\nInferred light control:")
    print(json.dumps(inferred.__dict__, indent=2, sort_keys=True))


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(description="Sync a smart bulb color to Spotify album art.")
    parser.add_argument("--once", action="store_true", help="Process the current track once and exit.")
    parser.add_argument("--dry-run", action="store_true", help="Do not send commands to the bulb.")
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=env_float("POLL_SECONDS", 1.0),
        help="Spotify polling interval in seconds. Default: 1.",
    )
    parser.add_argument("--no-open-browser", action="store_true", help="Print Spotify auth URL instead of opening it.")
    parser.add_argument("--print-tuya-spec", action="store_true", help="Print Tuya device functions/status and exit.")
    parser.add_argument("--image-url", help="Extract a dominant color from an image URL and exit.")
    parser.add_argument("--rgb", help="Set the bulb to a manual RGB color like #00aaff and exit.")
    args = parser.parse_args()

    try:
        if args.print_tuya_spec:
            print_tuya_spec()
            return 0

        if args.image_url:
            rgb = dominant_rgb_from_url(args.image_url)
            print(rgb_hex(rgb))
            if args.dry_run:
                send_or_log_rgb(None, rgb, dry_run=True)
            else:
                controller = build_light_controller(False)
                assert controller is not None
                controller.set_rgb(rgb)
            return 0

        if args.rgb:
            rgb = parse_rgb(args.rgb)
            print(f"Setting bulb to {rgb_hex(rgb)}")
            if args.dry_run:
                send_or_log_rgb(None, rgb, dry_run=True)
            else:
                controller = build_light_controller(False)
                assert controller is not None
                controller.set_rgb(rgb)
            return 0

        spotify = build_spotify(open_browser=not args.no_open_browser)
        controller = build_light_controller(args.dry_run)
        last_track_id = None

        while True:
            try:
                track = current_track_color(spotify)
                if track and track.track_id != last_track_id:
                    apply_track_color(controller, track, args.dry_run)
                    last_track_id = track.track_id
            except SpotifyRateLimitError as exc:
                print(f"Spotify rate limited the request; sleeping {exc.retry_after}s.", file=sys.stderr)
                if args.once:
                    return 1
                time.sleep(exc.retry_after)
                continue
            except Exception as exc:  # keep the watcher alive across transient API failures
                print(f"Error: {exc}", file=sys.stderr)
            if args.once:
                return 0
            time.sleep(args.poll_seconds)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

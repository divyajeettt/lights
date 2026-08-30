"""Read-only setup diagnostics for Spotify and TinyTuya."""

import ipaddress
import socket
from dataclasses import dataclass
from typing import Callable

from src.color import album_palette_from_url
from src.config import ConfigError
from src.enums import DiagnosticStatus
from src.light import TinyTuyaDeviceConfig, TinyTuyaLightController
from src.light.constants import TINYTUYA_PORT
from src.light.factory import configured_tinytuya_devices
from src.runner import best_album_image, track_label
from src.spotify import SpotifyClient, build_spotify


@dataclass(frozen=True)
class DiagnosticResult:
    component: str
    status: DiagnosticStatus
    detail: str
    configuration_error: bool = False


def _safe_error(exc: Exception, secrets: tuple[str, ...] = ()) -> str:
    message = str(exc) or exc.__class__.__name__
    for secret in secrets:
        if secret:
            message = message.replace(secret, "[redacted]")
    return message


def _check_reachability(device: TinyTuyaDeviceConfig) -> DiagnosticResult:
    component = f"Tuya {device.label} IP reachability"
    try:
        ipaddress.ip_address(device.address)
    except ValueError:
        return DiagnosticResult(
            component,
            DiagnosticStatus.FAIL,
            f"{device.address!r} is not a valid IP address",
            configuration_error=True,
        )

    try:
        with socket.create_connection((device.address, TINYTUYA_PORT), timeout=2):
            pass
    except OSError as exc:
        return DiagnosticResult(
            component,
            DiagnosticStatus.FAIL,
            f"{device.address}:{TINYTUYA_PORT} is unreachable: {_safe_error(exc)}",
        )
    return DiagnosticResult(
        component,
        DiagnosticStatus.PASS,
        f"{device.address}:{TINYTUYA_PORT} is reachable",
    )


def _check_device(device: TinyTuyaDeviceConfig) -> list[DiagnosticResult]:
    results = [_check_reachability(device)]
    secrets = (device.local_key, device.device_id)
    try:
        controller = TinyTuyaLightController(
            device_id=device.device_id,
            address=device.address,
            local_key=device.local_key,
            protocol_version=device.protocol_version,
            label=device.label,
        )
        state = controller.read_state()
    except Exception as exc:
        detail = _safe_error(exc, secrets)
        results.extend(
            [
                DiagnosticResult(
                    f"Tuya {device.label} protocol compatibility",
                    DiagnosticStatus.FAIL,
                    f"protocol {device.protocol_version:.1f} did not complete a "
                    f"state exchange: {detail}",
                ),
                DiagnosticResult(
                    f"Tuya {device.label} state read",
                    DiagnosticStatus.FAIL,
                    detail,
                ),
            ]
        )
        return results

    power = "on" if state["is_on"] else "off"
    results.extend(
        [
            DiagnosticResult(
                f"Tuya {device.label} protocol compatibility",
                DiagnosticStatus.PASS,
                f"protocol {device.protocol_version:.1f} completed a state exchange",
            ),
            DiagnosticResult(
                f"Tuya {device.label} state read",
                DiagnosticStatus.PASS,
                f"power is {power}",
            ),
        ]
    )
    return results


def _check_spotify(
    spotify_factory: Callable[[], SpotifyClient],
    light_count: int,
) -> list[DiagnosticResult]:
    try:
        spotify = spotify_factory()
        playback = spotify.currently_playing()
    except ConfigError as exc:
        return [
            DiagnosticResult(
                "Spotify authentication",
                DiagnosticStatus.FAIL,
                _safe_error(exc),
                configuration_error=True,
            ),
            DiagnosticResult(
                "Album-art access",
                DiagnosticStatus.SKIP,
                "Spotify configuration is invalid",
            ),
        ]
    except Exception as exc:
        return [
            DiagnosticResult(
                "Spotify authentication",
                DiagnosticStatus.FAIL,
                _safe_error(exc),
            ),
            DiagnosticResult(
                "Album-art access",
                DiagnosticStatus.SKIP,
                "Spotify authentication did not succeed",
            ),
        ]

    results = [
        DiagnosticResult(
            "Spotify authentication",
            DiagnosticStatus.PASS,
            "currently-playing API request authenticated successfully",
        )
    ]
    item = playback.get("item") if playback else None
    if not isinstance(item, dict) or item.get("type") != "track":
        results.append(
            DiagnosticResult(
                "Album-art access",
                DiagnosticStatus.SKIP,
                "play a Spotify track, then run --check again",
            )
        )
        return results

    image_url = best_album_image(item)
    if not image_url:
        results.append(
            DiagnosticResult(
                "Album-art access",
                DiagnosticStatus.FAIL,
                f"{track_label(item)} has no album image",
            )
        )
        return results

    try:
        palette, _fallback_used = album_palette_from_url(
            image_url,
            count=max(light_count, 1),
        )
    except Exception as exc:
        results.append(
            DiagnosticResult(
                "Album-art access",
                DiagnosticStatus.FAIL,
                _safe_error(exc),
            )
        )
        return results

    results.append(
        DiagnosticResult(
            "Album-art access",
            DiagnosticStatus.PASS,
            f"downloaded and decoded artwork for {track_label(item)} "
            f"({len(palette)} palette color(s))",
        )
    )
    return results


def run_diagnostics() -> int:
    """Run all setup checks without changing bulb color or power."""

    results: list[DiagnosticResult] = []
    devices: list[TinyTuyaDeviceConfig] = []
    try:
        devices = configured_tinytuya_devices()
    except ConfigError as exc:
        results.append(
            DiagnosticResult(
                "Parallel Tuya configuration",
                DiagnosticStatus.FAIL,
                _safe_error(exc),
                configuration_error=True,
            )
        )
    else:
        results.append(
            DiagnosticResult(
                "Parallel Tuya configuration",
                DiagnosticStatus.PASS,
                f"{len(devices)} device(s) have aligned IDs, IPs, keys, "
                "protocol versions, and labels",
            )
        )
        for device in devices:
            results.extend(_check_device(device))

    results.extend(_check_spotify(build_spotify, len(devices)))

    print("Setup diagnostic")
    for result in results:
        print(f"[{result.status}] {result.component}: {result.detail}")

    counts = {
        status: sum(result.status == status for result in results)
        for status in DiagnosticStatus
    }
    print(
        "Summary: "
        f"{counts[DiagnosticStatus.PASS]} passed, "
        f"{counts[DiagnosticStatus.FAIL]} failed, "
        f"{counts[DiagnosticStatus.SKIP]} skipped"
    )

    if any(result.configuration_error for result in results):
        print("Overall: CONFIGURATION ERROR")
        return 2
    if any(result.status != DiagnosticStatus.PASS for result in results):
        print("Overall: FAILED")
        return 1
    print("Overall: PASS")
    return 0

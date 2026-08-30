import src.diagnostics as diagnostics
from src.config import ConfigError
from src.diagnostics import DiagnosticResult
from src.enums import DiagnosticStatus
from src.light import TinyTuyaDeviceConfig

DEVICE = TinyTuyaDeviceConfig(
    device_id="device-1",
    address="192.168.1.10",
    local_key="test-key-0000001",
    protocol_version=3.3,
    label="desk",
)


class StubSpotify:
    def __init__(self, playback=None) -> None:
        self.playback = playback
        self.currently_playing_calls = 0

    def currently_playing(self):
        self.currently_playing_calls += 1
        return self.playback


def playback_payload() -> dict:
    return {
        "item": {
            "id": "track-1",
            "type": "track",
            "name": "Song",
            "artists": [{"name": "Artist"}],
            "album": {
                "images": [
                    {
                        "url": "https://example.com/art.jpg",
                        "width": 640,
                        "height": 640,
                    }
                ]
            },
        }
    }


def test_run_diagnostics_reports_all_pass(monkeypatch, capsys) -> None:
    spotify = StubSpotify(playback_payload())
    album_calls = []
    monkeypatch.setattr(diagnostics, "configured_tinytuya_devices", lambda: [DEVICE])
    monkeypatch.setattr(
        diagnostics,
        "_check_device",
        lambda _device: [
            DiagnosticResult(
                "Tuya desk state read", DiagnosticStatus.PASS, "power is on"
            )
        ],
    )
    monkeypatch.setattr(diagnostics, "build_spotify", lambda: spotify)
    monkeypatch.setattr(
        diagnostics,
        "album_palette_from_url",
        lambda url, *, count: album_calls.append((url, count)) or ([(1, 2, 3)], False),
    )

    result = diagnostics.run_diagnostics()

    captured = capsys.readouterr()
    assert result == 0
    assert spotify.currently_playing_calls == 1
    assert album_calls == [("https://example.com/art.jpg", 1)]
    assert "[PASS] Spotify authentication" in captured.out
    assert "[PASS] Album-art access" in captured.out
    assert "Overall: PASS" in captured.out


def test_run_diagnostics_returns_configuration_exit_code(monkeypatch, capsys) -> None:
    def invalid_configuration():
        raise ConfigError("TUYA_DEVICE_IPS must match TUYA_DEVICE_IDS")

    monkeypatch.setattr(
        diagnostics, "configured_tinytuya_devices", invalid_configuration
    )
    monkeypatch.setattr(diagnostics, "build_spotify", lambda: StubSpotify())

    result = diagnostics.run_diagnostics()

    captured = capsys.readouterr()
    assert result == 2
    assert "[FAIL] Parallel Tuya configuration" in captured.out
    assert "[PASS] Spotify authentication" in captured.out
    assert "[SKIP] Album-art access" in captured.out
    assert "Overall: CONFIGURATION ERROR" in captured.out


def test_run_diagnostics_requires_playing_track_for_album_art(
    monkeypatch, capsys
) -> None:
    monkeypatch.setattr(diagnostics, "configured_tinytuya_devices", lambda: [DEVICE])
    monkeypatch.setattr(diagnostics, "_check_device", lambda _device: [])
    monkeypatch.setattr(diagnostics, "build_spotify", lambda: StubSpotify())

    result = diagnostics.run_diagnostics()

    captured = capsys.readouterr()
    assert result == 1
    assert "[SKIP] Album-art access" in captured.out
    assert "play a Spotify track" in captured.out
    assert "Overall: FAILED" in captured.out


def test_run_diagnostics_reports_spotify_authentication_failure(
    monkeypatch, capsys
) -> None:
    class FailingSpotify:
        def currently_playing(self):
            raise RuntimeError("HTTP 401")

    monkeypatch.setattr(diagnostics, "configured_tinytuya_devices", lambda: [DEVICE])
    monkeypatch.setattr(diagnostics, "_check_device", lambda _device: [])
    monkeypatch.setattr(diagnostics, "build_spotify", lambda: FailingSpotify())

    result = diagnostics.run_diagnostics()

    captured = capsys.readouterr()
    assert result == 1
    assert "[FAIL] Spotify authentication: HTTP 401" in captured.out
    assert "[SKIP] Album-art access" in captured.out
    assert "Overall: FAILED" in captured.out


def test_run_diagnostics_returns_configuration_exit_for_spotify_config(
    monkeypatch, capsys
) -> None:
    def invalid_spotify_configuration():
        raise ConfigError("Missing required environment variable: SPOTIFY_CLIENT_ID")

    monkeypatch.setattr(diagnostics, "configured_tinytuya_devices", lambda: [DEVICE])
    monkeypatch.setattr(diagnostics, "_check_device", lambda _device: [])
    monkeypatch.setattr(diagnostics, "build_spotify", invalid_spotify_configuration)

    result = diagnostics.run_diagnostics()

    captured = capsys.readouterr()
    assert result == 2
    assert "[FAIL] Spotify authentication" in captured.out
    assert "[SKIP] Album-art access" in captured.out
    assert "Overall: CONFIGURATION ERROR" in captured.out


def test_run_diagnostics_returns_configuration_exit_for_invalid_ip(
    monkeypatch, capsys
) -> None:
    invalid_ip_device = TinyTuyaDeviceConfig(
        device_id=DEVICE.device_id,
        address="not-an-ip",
        local_key=DEVICE.local_key,
        protocol_version=DEVICE.protocol_version,
        label=DEVICE.label,
    )

    class ReadOnlyController:
        def __init__(self, **_kwargs) -> None:
            pass

        def read_state(self):
            return {"is_on": True}

    monkeypatch.setattr(
        diagnostics, "configured_tinytuya_devices", lambda: [invalid_ip_device]
    )
    monkeypatch.setattr(diagnostics, "TinyTuyaLightController", ReadOnlyController)
    monkeypatch.setattr(
        diagnostics, "build_spotify", lambda: StubSpotify(playback_payload())
    )
    monkeypatch.setattr(
        diagnostics,
        "album_palette_from_url",
        lambda _url, *, count: ([(1, 2, 3)] * count, False),
    )

    result = diagnostics.run_diagnostics()

    captured = capsys.readouterr()
    assert result == 2
    assert "[FAIL] Tuya desk IP reachability: 'not-an-ip'" in captured.out
    assert "Overall: CONFIGURATION ERROR" in captured.out


def test_check_device_only_reads_state(monkeypatch) -> None:
    calls = []

    class ReachableSocket:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

    class ReadOnlyController:
        def __init__(self, **kwargs) -> None:
            calls.append(("init", kwargs))

        def read_state(self):
            calls.append(("read_state",))
            return {"is_on": False}

    monkeypatch.setattr(
        diagnostics.socket,
        "create_connection",
        lambda address, timeout: calls.append(("connect", address, timeout))
        or ReachableSocket(),
    )
    monkeypatch.setattr(diagnostics, "TinyTuyaLightController", ReadOnlyController)

    results = diagnostics._check_device(DEVICE)

    assert [result.status for result in results] == [
        DiagnosticStatus.PASS,
        DiagnosticStatus.PASS,
        DiagnosticStatus.PASS,
    ]
    assert [call[0] for call in calls] == ["connect", "init", "read_state"]


def test_check_device_redacts_credentials(monkeypatch) -> None:
    class FailingController:
        def __init__(self, **_kwargs) -> None:
            pass

        def read_state(self):
            raise OSError(f"bad {DEVICE.device_id} {DEVICE.local_key}")

    monkeypatch.setattr(
        diagnostics.socket,
        "create_connection",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(OSError("offline")),
    )
    monkeypatch.setattr(diagnostics, "TinyTuyaLightController", FailingController)

    results = diagnostics._check_device(DEVICE)
    output = " ".join(result.detail for result in results)

    assert DEVICE.device_id not in output
    assert DEVICE.local_key not in output
    assert output.count("[redacted]") == 4

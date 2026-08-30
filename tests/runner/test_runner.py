import pytest

from src.enums import LightColorMode
from src.runner import current_track_summary, run_watcher
from src.spotify import SpotifyRateLimitError


class StubController:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []
        self.power_calls: list[bool] = []

    def set_rgb(self, rgb: tuple[int, int, int]) -> None:
        self.calls.append(rgb)

    def set_power(self, on: bool) -> None:
        self.power_calls.append(on)


class StubGroupController:
    light_labels = ("left", "right")

    def __init__(self) -> None:
        self.calls = []
        self.power_calls: list[bool] = []

    def set_rgbs(self, rgbs):
        self.calls.append(list(rgbs))

    def set_power(self, on: bool) -> None:
        self.power_calls.append(on)


class StubSpotify:
    def __init__(self, responses) -> None:
        self._responses = iter(responses)

    def currently_playing(self):
        response = next(self._responses)
        if isinstance(response, Exception):
            raise response
        return response


def playback_payload(track_id: str = "track-1"):
    return {
        "is_playing": True,
        "item": {
            "type": "track",
            "id": track_id,
            "name": "Song",
            "artists": [{"name": "Artist"}],
            "album": {"images": [{"url": "https://example.com/a.jpg"}]},
        },
    }


def test_run_watcher_returns_rate_limit_error_code_once(capsys) -> None:
    spotify = StubSpotify([SpotifyRateLimitError(3)])

    result = run_watcher(
        spotify=spotify,
        controller=None,
        poll_seconds=0.0,
        dry_run_once=True,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Spotify rate limited the request" in captured.err


def test_run_watcher_returns_spotify_error_code_once(capsys) -> None:
    spotify = StubSpotify([RuntimeError("Spotify request failed")])

    result = run_watcher(
        spotify=spotify,
        controller=None,
        poll_seconds=0.0,
        dry_run_once=True,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: Spotify request failed" in captured.err


def test_run_watcher_returns_album_art_error_code_once(monkeypatch, capsys) -> None:
    spotify = StubSpotify([playback_payload()])
    original = __import__("src.runner", fromlist=["album_palette_from_url"])
    monkeypatch.setattr(
        original,
        "album_palette_from_url",
        lambda _url, count: (_ for _ in ()).throw(
            RuntimeError("album art processing failed")
        ),
    )

    result = run_watcher(
        spotify=spotify,
        controller=None,
        poll_seconds=0.0,
        dry_run_once=True,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: album art processing failed" in captured.err


def test_run_watcher_applies_track_once_without_controller(capsys) -> None:
    spotify = StubSpotify([playback_payload()])

    original = __import__("src.runner", fromlist=["album_rgb_from_url"])
    old_album_rgb_from_url = original.album_rgb_from_url
    original.album_rgb_from_url = lambda _url: ((0, 170, 255), False)
    try:
        result = run_watcher(
            spotify=spotify,
            controller=None,
            poll_seconds=0.0,
            dry_run_once=True,
            color_mode=LightColorMode.SAME,
        )
    finally:
        original.album_rgb_from_url = old_album_rgb_from_url

    captured = capsys.readouterr()
    assert result == 0
    assert "Song - Artist -> bulb 1=#00aaff" in captured.out


def test_current_track_summary_returns_none_for_non_track_item(capsys) -> None:
    spotify = StubSpotify(
        [
            {
                "is_playing": True,
                "item": {
                    "type": "episode",
                    "id": "episode-1",
                    "name": "Podcast",
                },
            }
        ]
    )

    result = current_track_summary(spotify)

    captured = capsys.readouterr()
    assert result is None
    assert "Currently playing item is not a track: episode" in captured.out


def test_current_track_summary_returns_none_for_track_without_id(capsys) -> None:
    spotify = StubSpotify(
        [
            {
                "is_playing": True,
                "item": {
                    "type": "track",
                    "name": "Song",
                    "artists": [{"name": "Artist"}],
                    "album": {"images": [{"url": "https://example.com/a.jpg"}]},
                },
            }
        ]
    )

    result = current_track_summary(spotify)

    captured = capsys.readouterr()
    assert result is None
    assert "Currently playing track has no Spotify ID." in captured.out


def test_run_watcher_invalid_payload_returns_no_work_once(monkeypatch, capsys) -> None:
    spotify = StubSpotify(
        [
            {
                "is_playing": True,
                "item": {
                    "type": "episode",
                    "id": "episode-1",
                    "name": "Podcast",
                },
            }
        ]
    )
    album_calls = []

    original = __import__("src.runner", fromlist=["album_rgb_from_url"])
    monkeypatch.setattr(
        original,
        "album_rgb_from_url",
        lambda url: album_calls.append(url) or ((0, 170, 255), False),
    )

    result = run_watcher(
        spotify=spotify,
        controller=None,
        poll_seconds=0.0,
        dry_run_once=True,
    )

    captured = capsys.readouterr()
    assert result == 0
    assert album_calls == []
    assert "Podcast ->" not in captured.out


def test_run_watcher_skips_album_color_for_unchanged_track(monkeypatch) -> None:
    class StopLoop(Exception):
        pass

    spotify = StubSpotify([playback_payload(), playback_payload()])
    controller = StubController()
    album_calls = []
    sleep_calls = 0

    original = __import__("src.runner", fromlist=["album_rgb_from_url", "time"])
    monkeypatch.setattr(
        original,
        "album_rgb_from_url",
        lambda url: album_calls.append(url) or ((0, 170, 255), False),
    )

    def sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            raise StopLoop

    monkeypatch.setattr(original.time, "sleep", sleep)

    with pytest.raises(StopLoop):
        run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=0.0,
            dry_run_once=False,
            color_mode=LightColorMode.SAME,
        )

    assert album_calls == ["https://example.com/a.jpg"]
    assert controller.calls == [(0, 170, 255)]


def test_run_watcher_defaults_to_album_palette_for_multiple_lights(monkeypatch) -> None:
    spotify = StubSpotify([playback_payload()])
    controller = StubGroupController()

    original = __import__("src.runner", fromlist=["album_palette_from_url"])
    monkeypatch.setattr(
        original,
        "album_palette_from_url",
        lambda _url, count: ([(0, 170, 255), (255, 102, 0)][:count], False),
    )

    result = run_watcher(
        spotify=spotify,
        controller=controller,
        poll_seconds=0.0,
        dry_run_once=True,
        light_count=2,
    )

    assert result == 0
    assert controller.calls == [[(0, 170, 255), (255, 102, 0)]]


def test_run_watcher_auto_switch_powers_lights_around_watcher(monkeypatch) -> None:
    class StopLoop(Exception):
        pass

    spotify = StubSpotify([playback_payload()])
    controller = StubController()
    original = __import__("src.runner", fromlist=["album_rgb_from_url", "time"])
    monkeypatch.setattr(
        original,
        "album_rgb_from_url",
        lambda _url: ((0, 170, 255), False),
    )
    monkeypatch.setattr(
        original.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(StopLoop),
    )

    with pytest.raises(StopLoop):
        run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=0.0,
            dry_run_once=False,
            color_mode=LightColorMode.SAME,
            auto_switch=True,
        )

    assert controller.power_calls == [True, False]


def test_run_watcher_auto_switch_turns_lights_off_after_keyboard_interrupt(
    monkeypatch,
) -> None:
    spotify = StubSpotify([playback_payload()])
    controller = StubController()
    original = __import__("src.runner", fromlist=["album_rgb_from_url", "time"])
    monkeypatch.setattr(
        original,
        "album_rgb_from_url",
        lambda _url: ((0, 170, 255), False),
    )
    monkeypatch.setattr(
        original.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    result = run_watcher(
        spotify=spotify,
        controller=controller,
        poll_seconds=0.0,
        dry_run_once=False,
        color_mode=LightColorMode.SAME,
        auto_switch=True,
    )

    assert result == 130
    assert controller.power_calls == [True, False]


def test_run_watcher_without_auto_switch_propagates_keyboard_interrupt(
    monkeypatch,
) -> None:
    spotify = StubSpotify([playback_payload()])
    controller = StubController()
    original = __import__("src.runner", fromlist=["album_rgb_from_url", "time"])
    monkeypatch.setattr(
        original,
        "album_rgb_from_url",
        lambda _url: ((0, 170, 255), False),
    )
    monkeypatch.setattr(
        original.time,
        "sleep",
        lambda _seconds: (_ for _ in ()).throw(KeyboardInterrupt),
    )

    with pytest.raises(KeyboardInterrupt):
        run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=0.0,
            dry_run_once=False,
            color_mode=LightColorMode.SAME,
        )

    assert controller.power_calls == []


def test_run_watcher_auto_switch_reports_shutdown_error(
    monkeypatch,
    capsys,
) -> None:
    class FailingShutdownController(StubController):
        def set_power(self, on: bool) -> None:
            super().set_power(on)
            if not on:
                raise RuntimeError("offline")

    spotify = StubSpotify([playback_payload()])
    controller = FailingShutdownController()
    original = __import__("src.runner", fromlist=["album_rgb_from_url"])
    monkeypatch.setattr(
        original,
        "album_rgb_from_url",
        lambda _url: ((0, 170, 255), False),
    )

    result = run_watcher(
        spotify=spotify,
        controller=controller,
        poll_seconds=0.0,
        dry_run_once=True,
        color_mode=LightColorMode.SAME,
        auto_switch=True,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert controller.power_calls == [True, False]
    assert "Error switching bulb(s) off: offline" in captured.err


def test_run_watcher_auto_switch_cleans_up_after_startup_error() -> None:
    class FailingStartupController(StubController):
        def set_power(self, on: bool) -> None:
            super().set_power(on)
            if on:
                raise RuntimeError("startup failed")

    spotify = StubSpotify([playback_payload()])
    controller = FailingStartupController()

    with pytest.raises(RuntimeError, match="startup failed"):
        run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=0.0,
            dry_run_once=True,
            auto_switch=True,
        )

    assert controller.power_calls == [True, False]


def test_run_watcher_retries_same_track_after_color_error(monkeypatch) -> None:
    class StopLoop(Exception):
        pass

    spotify = StubSpotify([playback_payload(), playback_payload()])
    controller = StubController()
    album_calls = 0
    sleep_calls = 0

    original = __import__("src.runner", fromlist=["album_rgb_from_url", "time"])

    def album_rgb_from_url(_url):
        nonlocal album_calls
        album_calls += 1
        if album_calls == 1:
            raise RuntimeError("transient image failure")
        return (0, 170, 255), False

    monkeypatch.setattr(original, "album_rgb_from_url", album_rgb_from_url)

    def sleep(_seconds):
        nonlocal sleep_calls
        sleep_calls += 1
        if sleep_calls == 2:
            raise StopLoop

    monkeypatch.setattr(original.time, "sleep", sleep)

    with pytest.raises(StopLoop):
        run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=0.0,
            dry_run_once=False,
            color_mode=LightColorMode.SAME,
        )

    assert album_calls == 2
    assert controller.calls == [(0, 170, 255)]

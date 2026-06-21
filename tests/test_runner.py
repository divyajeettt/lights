import pytest

from src.runner import current_track_summary, run_watcher, send_or_log_rgb
from src.spotify import SpotifyRateLimitError


class StubController:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def set_rgb(self, rgb: tuple[int, int, int]) -> None:
        self.calls.append(rgb)


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


def test_send_or_log_rgb_dry_run_skips_controller(capsys) -> None:
    controller = StubController()

    send_or_log_rgb(controller, (0, 170, 255), dry_run=True)

    captured = capsys.readouterr()
    assert "Dry run: would set bulb to #00aaff" in captured.out
    assert controller.calls == []


def test_run_watcher_returns_rate_limit_error_code_once(capsys) -> None:
    spotify = StubSpotify([SpotifyRateLimitError(3)])

    result = run_watcher(
        spotify=spotify,
        controller=None,
        poll_seconds=0.0,
        dry_run=True,
        once=True,
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Spotify rate limited the request" in captured.err


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
            dry_run=True,
            once=True,
        )
    finally:
        original.album_rgb_from_url = old_album_rgb_from_url

    captured = capsys.readouterr()
    assert result == 0
    assert "Song - Artist -> #00aaff" in captured.out


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
        dry_run=True,
        once=True,
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
            dry_run=False,
            once=False,
        )

    assert album_calls == ["https://example.com/a.jpg"]
    assert controller.calls == [(0, 170, 255)]


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
            dry_run=False,
            once=False,
        )

    assert album_calls == 2
    assert controller.calls == [(0, 170, 255)]

from src.runner import run_watcher, send_or_log_rgb
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
    spotify = StubSpotify(
        [
            {
                "is_playing": True,
                "item": {
                    "type": "track",
                    "id": "track-1",
                    "name": "Song",
                    "artists": [{"name": "Artist"}],
                    "album": {"images": [{"url": "https://example.com/a.jpg"}]},
                },
            }
        ]
    )

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

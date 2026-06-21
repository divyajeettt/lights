from pathlib import Path

import pytest

import src.spotify.client as spotify_client_module
from src.constants import DEFAULT_SPOTIFY_REDIRECT_URI
from src.enums import SpotifyEnvVar, SpotifyTokenField
from src.spotify import SpotifyClient, build_spotify, parse_retry_after, request_json

TEST_SPOTIFY_CLIENT_ID = "a" * 32
TEST_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:9999/callback"
TEST_SPOTIFY_CACHE_FILE = ".cache/test-token.json"
TEST_REQUEST_URL = "https://example.com"


def test_parse_retry_after_defaults_to_five_seconds() -> None:
    assert parse_retry_after({}) == 5


def test_parse_retry_after_clamps_non_positive_values() -> None:
    assert parse_retry_after({"Retry-After": "0"}) == 1


def test_spotify_client_save_token_preserves_refresh_token(tmp_path) -> None:
    cache_file = tmp_path / "spotify_token.json"
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=DEFAULT_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )
    client.token = {SpotifyTokenField.REFRESH_TOKEN: "refresh-123"}

    client._save_token(
        {
            SpotifyTokenField.ACCESS_TOKEN: "access-123",
            SpotifyTokenField.EXPIRES_IN: 3600,
        }
    )

    assert client.token[SpotifyTokenField.REFRESH_TOKEN] == "refresh-123"
    assert cache_file.exists()


def test_build_spotify_uses_env_values(monkeypatch) -> None:
    monkeypatch.setenv(SpotifyEnvVar.CLIENT_ID, TEST_SPOTIFY_CLIENT_ID)
    monkeypatch.setenv(
        SpotifyEnvVar.REDIRECT_URI,
        TEST_SPOTIFY_REDIRECT_URI,
    )
    monkeypatch.setenv(SpotifyEnvVar.CACHE_FILE, TEST_SPOTIFY_CACHE_FILE)

    client = build_spotify(open_browser=False)

    assert client.client_id == TEST_SPOTIFY_CLIENT_ID
    assert client.redirect_uri == TEST_SPOTIFY_REDIRECT_URI
    assert client.cache_file == Path(TEST_SPOTIFY_CACHE_FILE)
    assert client.open_browser is False


class StubResponse:
    def __init__(
        self,
        status_code: int,
        payload=None,
        text: str = "",
        headers=None,
    ) -> None:
        self.status_code = status_code
        self._payload = payload
        self.text = text
        self.headers = headers or {}

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_request_json_returns_none_for_204(monkeypatch) -> None:
    monkeypatch.setattr(
        spotify_client_module.requests,
        "request",
        lambda *args, **kwargs: StubResponse(204),
    )

    assert request_json("GET", TEST_REQUEST_URL) is None


def test_request_json_raises_on_http_error(monkeypatch) -> None:
    monkeypatch.setattr(
        spotify_client_module.requests,
        "request",
        lambda *args, **kwargs: StubResponse(500, {"error": "boom"}),
    )

    with pytest.raises(RuntimeError):
        request_json("GET", TEST_REQUEST_URL)


def test_currently_playing_refreshes_after_401(monkeypatch, tmp_path) -> None:
    cache_file = tmp_path / "spotify_token.json"
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=DEFAULT_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )
    client.token = {
        SpotifyTokenField.ACCESS_TOKEN: "stale-token",
        SpotifyTokenField.REFRESH_TOKEN: "refresh-token",
        SpotifyTokenField.EXPIRES_AT: 9999999999,
    }
    calls = {"count": 0}

    def fake_get(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return StubResponse(401, text="expired")
        return StubResponse(
            200,
            {"is_playing": True, "item": {"type": "track"}},
        )

    monkeypatch.setattr(spotify_client_module.requests, "get", fake_get)
    monkeypatch.setattr(
        client,
        "_refresh_token",
        lambda: client.token.update({SpotifyTokenField.ACCESS_TOKEN: "fresh-token"}),
    )

    payload = client.currently_playing()

    assert payload == {"is_playing": True, "item": {"type": "track"}}
    assert calls["count"] == 2


def test_currently_playing_raises_rate_limit(monkeypatch, tmp_path) -> None:
    cache_file = tmp_path / "spotify_token.json"
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=DEFAULT_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )
    client.token = {
        SpotifyTokenField.ACCESS_TOKEN: "token",
        SpotifyTokenField.EXPIRES_AT: 9999999999,
    }

    monkeypatch.setattr(
        spotify_client_module.requests,
        "get",
        lambda *args, **kwargs: StubResponse(
            429,
            text="rate limited",
            headers={"Retry-After": "7"},
        ),
    )

    with pytest.raises(spotify_client_module.SpotifyRateLimitError) as exc_info:
        client.currently_playing()

    assert exc_info.value.retry_after == 7

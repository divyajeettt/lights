import json
import stat
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


def test_spotify_client_save_token_writes_private_cache_file(tmp_path) -> None:
    cache_file = tmp_path / "spotify_token.json"
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=DEFAULT_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )

    client._save_token(
        {
            SpotifyTokenField.ACCESS_TOKEN: "access-123",
            SpotifyTokenField.REFRESH_TOKEN: "refresh-123",
            SpotifyTokenField.EXPIRES_IN: 3600,
        }
    )

    assert stat.S_IMODE(cache_file.stat().st_mode) == 0o600
    assert json.loads(cache_file.read_text())[SpotifyTokenField.ACCESS_TOKEN] == (
        "access-123"
    )


def test_spotify_client_save_token_replace_failure_keeps_existing_cache(
    monkeypatch,
    tmp_path,
) -> None:
    cache_file = tmp_path / "spotify_token.json"
    cache_file.write_text('{"access_token": "old-token"}\n')
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=DEFAULT_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )

    def fail_replace(*args, **kwargs):
        raise OSError("replace failed")

    monkeypatch.setattr(spotify_client_module.os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        client._save_token(
            {
                SpotifyTokenField.ACCESS_TOKEN: "new-token",
                SpotifyTokenField.EXPIRES_IN: 3600,
            }
        )

    assert json.loads(cache_file.read_text()) == {"access_token": "old-token"}
    assert not list(tmp_path.glob(".spotify_token.json.*"))
    assert client.token == {SpotifyTokenField.ACCESS_TOKEN: "old-token"}


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


def test_authorize_closes_callback_server_after_success(monkeypatch, tmp_path) -> None:
    cache_file = tmp_path / "spotify_token.json"
    servers = []

    class FakeServer:
        def __init__(self, address, handler) -> None:
            self.address = address
            self.handler = handler
            self.timeout = None
            self.closed = False
            servers.append(self)

        def handle_request(self) -> None:
            self.auth_code = "auth-code"
            self.auth_state = "state-123"

        def server_close(self) -> None:
            self.closed = True

    token_urlsafe_values = iter(["verifier-123", "state-123"])
    monkeypatch.setattr(spotify_client_module, "HTTPServer", FakeServer)
    monkeypatch.setattr(
        spotify_client_module.secrets,
        "token_urlsafe",
        lambda size: next(token_urlsafe_values),
    )
    monkeypatch.setattr(
        spotify_client_module,
        "request_json",
        lambda *args, **kwargs: {
            SpotifyTokenField.ACCESS_TOKEN: "access-123",
            SpotifyTokenField.REFRESH_TOKEN: "refresh-123",
            SpotifyTokenField.EXPIRES_IN: 3600,
        },
    )
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=TEST_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )

    client._authorize()

    assert servers[0].closed is True
    assert servers[0].timeout == spotify_client_module.SPOTIFY_CALLBACK_POLL_SECONDS
    assert client.token[SpotifyTokenField.ACCESS_TOKEN] == "access-123"


def test_authorize_times_out_and_closes_callback_server(monkeypatch, tmp_path) -> None:
    cache_file = tmp_path / "spotify_token.json"
    servers = []

    class FakeServer:
        def __init__(self, address, handler) -> None:
            self.closed = False
            servers.append(self)

        def handle_request(self) -> None:
            raise AssertionError("handle_request should not run after timeout")

        def server_close(self) -> None:
            self.closed = True

    monkeypatch.setattr(spotify_client_module, "HTTPServer", FakeServer)
    monkeypatch.setattr(spotify_client_module, "SPOTIFY_CALLBACK_TIMEOUT_SECONDS", 0)
    client = SpotifyClient(
        client_id=TEST_SPOTIFY_CLIENT_ID,
        redirect_uri=TEST_SPOTIFY_REDIRECT_URI,
        cache_file=cache_file,
        open_browser=False,
    )

    with pytest.raises(RuntimeError, match="timed out"):
        client._authorize()

    assert servers[0].closed is True


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

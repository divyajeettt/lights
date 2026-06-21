"""Spotify Web API client and PKCE auth flow."""

from __future__ import annotations

import base64
import hashlib
import json
import secrets
import time
import urllib.parse
import webbrowser
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any

import requests

from src.config import ConfigError
from src.constants import (
    SPOTIFY_AUTH_URL,
    SPOTIFY_CURRENTLY_PLAYING_URL,
    SPOTIFY_DEFAULT_CALLBACK_HOST,
    SPOTIFY_LOCAL_REDIRECT_HOSTS,
    SPOTIFY_LOCAL_REDIRECT_SCHEME,
    SPOTIFY_SCOPE,
    SPOTIFY_TOKEN_URL,
)
from src.enums import (
    SpotifyGrantType,
    SpotifyOAuthParam,
    SpotifyPkceMethod,
    SpotifyResponseType,
    SpotifyTokenField,
)


class SpotifyRateLimitError(RuntimeError):
    def __init__(self, retry_after: int) -> None:
        super().__init__(
            f"Spotify rate limited the request; retrying after {retry_after}s"
        )
        self.retry_after = retry_after


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
        raise RuntimeError(
            f"{method} {url} failed: HTTP {response.status_code}: {payload}"
        )
    return payload


class SpotifyCallbackHandler(BaseHTTPRequestHandler):
    server_version = "SpotifyCallback/1.0"

    def do_GET(self) -> None:
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = params.get(SpotifyOAuthParam.CODE, [""])[0]
        self.server.auth_state = params.get(SpotifyOAuthParam.STATE, [""])[0]
        self.server.auth_error = params.get(SpotifyOAuthParam.ERROR, [""])[0]
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(
            b"<html><body><h1>Spotify authorization received.</h1>"
            b"<p>You can close this tab and return to the terminal.</p>"
            b"</body></html>"
        )

    def log_message(self, format: str, *args: Any) -> None:
        return


class SpotifyClient:
    def __init__(
        self,
        client_id: str,
        redirect_uri: str,
        cache_file: Path,
        open_browser: bool = True,
    ) -> None:
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
        expires_in = int(token.get(SpotifyTokenField.EXPIRES_IN, 3600))
        token[SpotifyTokenField.EXPIRES_AT] = int(time.time()) + expires_in - 60
        if SpotifyTokenField.REFRESH_TOKEN not in token and self.token.get(
            SpotifyTokenField.REFRESH_TOKEN
        ):
            token[SpotifyTokenField.REFRESH_TOKEN] = self.token[
                SpotifyTokenField.REFRESH_TOKEN
            ]
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(token, indent=2, sort_keys=True))
        self.token = token

    def access_token(self) -> str:
        if self.token.get(SpotifyTokenField.ACCESS_TOKEN) and int(
            self.token.get(SpotifyTokenField.EXPIRES_AT, 0)
        ) > int(time.time()):
            return self.token[SpotifyTokenField.ACCESS_TOKEN]
        if self.token.get(SpotifyTokenField.REFRESH_TOKEN):
            self._refresh_token()
            return self.token[SpotifyTokenField.ACCESS_TOKEN]
        self._authorize()
        return self.token[SpotifyTokenField.ACCESS_TOKEN]

    def _refresh_token(self) -> None:
        payload = {
            SpotifyOAuthParam.GRANT_TYPE: SpotifyGrantType.REFRESH_TOKEN,
            SpotifyOAuthParam.REFRESH_TOKEN: self.token[
                SpotifyTokenField.REFRESH_TOKEN
            ],
            SpotifyOAuthParam.CLIENT_ID: self.client_id,
        }
        token = request_json("POST", SPOTIFY_TOKEN_URL, data=payload)
        self._save_token(token)

    def _authorize(self) -> None:
        parsed = urllib.parse.urlparse(self.redirect_uri)
        if (
            parsed.scheme != SPOTIFY_LOCAL_REDIRECT_SCHEME
            or parsed.hostname not in SPOTIFY_LOCAL_REDIRECT_HOSTS
        ):
            raise ConfigError(
                "SPOTIFY_REDIRECT_URI must be a localhost HTTP URL for this " "script"
            )

        code_verifier = secrets.token_urlsafe(64)
        challenge = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("=")
        state = secrets.token_urlsafe(24)
        query = urllib.parse.urlencode(
            {
                SpotifyOAuthParam.CLIENT_ID: self.client_id,
                SpotifyOAuthParam.RESPONSE_TYPE: SpotifyResponseType.CODE,
                SpotifyOAuthParam.REDIRECT_URI: self.redirect_uri,
                SpotifyOAuthParam.SCOPE: SPOTIFY_SCOPE,
                SpotifyOAuthParam.STATE: state,
                SpotifyOAuthParam.CODE_CHALLENGE_METHOD: SpotifyPkceMethod.S256,
                SpotifyOAuthParam.CODE_CHALLENGE: code_challenge,
            }
        )
        auth_url = f"{SPOTIFY_AUTH_URL}?{query}"

        host = parsed.hostname or SPOTIFY_DEFAULT_CALLBACK_HOST
        port = parsed.port or 80
        server = HTTPServer((host, port), SpotifyCallbackHandler)
        server.auth_code = ""
        server.auth_state = ""
        server.auth_error = ""

        print("Open this URL to authorize Spotify:")
        print(auth_url)
        if self.open_browser:
            webbrowser.open(auth_url)

        while not server.auth_code and not server.auth_error:
            server.handle_request()

        if server.auth_error:
            raise RuntimeError(f"Spotify authorization failed: {server.auth_error}")
        if server.auth_state != state:
            raise RuntimeError("Spotify authorization failed: state mismatch")

        payload = {
            SpotifyOAuthParam.CLIENT_ID: self.client_id,
            SpotifyOAuthParam.GRANT_TYPE: SpotifyGrantType.AUTHORIZATION_CODE,
            SpotifyOAuthParam.CODE: server.auth_code,
            SpotifyOAuthParam.REDIRECT_URI: self.redirect_uri,
            SpotifyOAuthParam.CODE_VERIFIER: code_verifier,
        }
        token = request_json("POST", SPOTIFY_TOKEN_URL, data=payload)
        self._save_token(token)

    def currently_playing(self) -> dict[str, Any] | None:
        headers = {"Authorization": f"Bearer {self.access_token()}"}
        params = {SpotifyOAuthParam.ADDITIONAL_TYPES: "track"}
        response = requests.get(
            SPOTIFY_CURRENTLY_PLAYING_URL,
            headers=headers,
            params=params,
            timeout=20,
        )
        if response.status_code == 204:
            return None
        if response.status_code == 401 and self.token.get(
            SpotifyTokenField.REFRESH_TOKEN
        ):
            self._refresh_token()
            headers = {
                "Authorization": f"Bearer {self.token[SpotifyTokenField.ACCESS_TOKEN]}"
            }
            response = requests.get(
                SPOTIFY_CURRENTLY_PLAYING_URL,
                headers=headers,
                params=params,
                timeout=20,
            )
        if response.status_code == 429:
            raise SpotifyRateLimitError(parse_retry_after(response.headers))
        if response.status_code >= 400:
            raise RuntimeError(
                "Spotify currently-playing failed: HTTP "
                f"{response.status_code}: {response.text}"
            )
        return response.json()

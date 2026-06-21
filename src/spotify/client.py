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
from src.constants import SPOTIFY_AUTH_URL
from src.constants import SPOTIFY_CURRENTLY_PLAYING_URL
from src.constants import SPOTIFY_SCOPE
from src.constants import SPOTIFY_TOKEN_URL


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

    def do_GET(self) -> None:  # noqa: N802
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        self.server.auth_code = (
            params.get("code", [""])[0]
        )  # type: ignore[attr-defined]
        self.server.auth_state = (
            params.get("state", [""])[0]
        )  # type: ignore[attr-defined]
        self.server.auth_error = (
            params.get("error", [""])[0]
        )  # type: ignore[attr-defined]
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
        token["expires_at"] = (
            int(time.time()) + int(token.get("expires_in", 3600)) - 60
        )
        if "refresh_token" not in token and self.token.get("refresh_token"):
            token["refresh_token"] = self.token["refresh_token"]
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        self.cache_file.write_text(json.dumps(token, indent=2, sort_keys=True))
        self.token = token

    def access_token(self) -> str:
        if (
            self.token.get("access_token")
            and int(self.token.get("expires_at", 0)) > int(time.time())
        ):
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
        if (
            parsed.scheme != "http"
            or parsed.hostname not in {"127.0.0.1", "localhost"}
        ):
            raise ConfigError(
                "SPOTIFY_REDIRECT_URI must be a localhost HTTP URL for this "
                "script"
            )

        code_verifier = secrets.token_urlsafe(64)
        challenge = hashlib.sha256(code_verifier.encode("ascii")).digest()
        code_challenge = (
            base64.urlsafe_b64encode(challenge).decode("ascii").rstrip("=")
        )
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

        while not server.auth_code and not server.auth_error:
            server.handle_request()

        if server.auth_error:  # type: ignore[attr-defined]
            raise RuntimeError(
                f"Spotify authorization failed: {server.auth_error}"
            )  # type: ignore[attr-defined]
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
            raise RuntimeError(
                "Spotify currently-playing failed: HTTP "
                f"{response.status_code}: {response.text}"
            )
        return response.json()

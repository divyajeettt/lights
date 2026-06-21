"""Spotify client factory helpers."""

from __future__ import annotations

from pathlib import Path

from src.config import env
from src.config import validate_spotify_client_id
from src.constants import DEFAULT_SPOTIFY_REDIRECT_URI
from src.spotify.client import SpotifyClient


def build_spotify(open_browser: bool) -> SpotifyClient:
    client_id = env("SPOTIFY_CLIENT_ID", required=True)
    validate_spotify_client_id(client_id)
    redirect_uri = env("SPOTIFY_REDIRECT_URI", DEFAULT_SPOTIFY_REDIRECT_URI)
    cache_file = Path(env("SPOTIFY_CACHE_FILE", ".cache/spotify_token.json"))
    return SpotifyClient(
        client_id,
        redirect_uri,
        cache_file,
        open_browser=open_browser,
    )

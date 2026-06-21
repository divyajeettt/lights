"""Spotify client factory helpers."""

from __future__ import annotations

from pathlib import Path

from src.config import env, validate_spotify_client_id
from src.constants import DEFAULT_SPOTIFY_CACHE_FILE, DEFAULT_SPOTIFY_REDIRECT_URI
from src.enums import SpotifyEnvVar

from .client import SpotifyClient


def build_spotify(open_browser: bool) -> SpotifyClient:
    client_id = env(SpotifyEnvVar.CLIENT_ID, required=True)
    validate_spotify_client_id(client_id)
    redirect_uri = env(SpotifyEnvVar.REDIRECT_URI, DEFAULT_SPOTIFY_REDIRECT_URI)
    cache_file = Path(env(SpotifyEnvVar.CACHE_FILE, DEFAULT_SPOTIFY_CACHE_FILE))
    return SpotifyClient(
        client_id,
        redirect_uri,
        cache_file,
        open_browser=open_browser,
    )

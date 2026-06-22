"""Spotify client factory helpers."""

from pathlib import Path

from src.config import env, validate_spotify_client_id

from .client import SpotifyClient
from .constants import SPOTIFY_CACHE_FILE, SPOTIFY_REDIRECT_URI
from .enums import SpotifyEnvVar


def build_spotify() -> SpotifyClient:
    client_id = env(SpotifyEnvVar.CLIENT_ID, required=True)
    validate_spotify_client_id(client_id)
    return SpotifyClient(
        client_id,
        SPOTIFY_REDIRECT_URI,
        Path(SPOTIFY_CACHE_FILE),
    )

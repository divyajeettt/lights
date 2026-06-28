"""Spotify client and auth helpers."""

from typing import Final

from .client import (
    SpotifyClient,
    SpotifyRateLimitError,
    parse_retry_after,
    request_json,
)
from .constants import (
    SPOTIFY_CACHE_FILE,
    SPOTIFY_CALLBACK_POLL_SECONDS,
    SPOTIFY_CALLBACK_TIMEOUT_SECONDS,
    SPOTIFY_REDIRECT_URI,
)
from .enums import SpotifyTokenField
from .factory import build_spotify

__all__: Final[list[str]] = [
    "SPOTIFY_CACHE_FILE",
    "SPOTIFY_CALLBACK_POLL_SECONDS",
    "SPOTIFY_CALLBACK_TIMEOUT_SECONDS",
    "SPOTIFY_REDIRECT_URI",
    "SpotifyClient",
    "SpotifyRateLimitError",
    "SpotifyTokenField",
    "build_spotify",
    "parse_retry_after",
    "request_json",
]

"""Constants for Spotify integration."""

from typing import Final

SPOTIFY_AUTH_URL: Final[str] = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL: Final[str] = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL: Final[str] = (
    "https://api.spotify.com/v1/me/player/currently-playing"
)
SPOTIFY_SCOPE: Final[str] = "user-read-currently-playing user-read-playback-state"
SPOTIFY_PKCE_METHOD: Final[str] = "S256"
SPOTIFY_RESPONSE_TYPE: Final[str] = "code"
SPOTIFY_REDIRECT_URI: Final[str] = "http://127.0.0.1:8888/callback"
SPOTIFY_LOCAL_REDIRECT_SCHEME: Final[str] = "http"
SPOTIFY_LOCAL_REDIRECT_HOSTS: Final[set[str]] = {"127.0.0.1", "localhost"}
SPOTIFY_CACHE_FILE: Final[str] = ".cache/spotify_token.json"
SPOTIFY_CALLBACK_TIMEOUT_SECONDS: Final[int] = 300
SPOTIFY_CALLBACK_POLL_SECONDS: Final[float] = 1.0

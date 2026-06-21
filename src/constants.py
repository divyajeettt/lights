"""Shared constants for the application."""

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL = (
    "https://api.spotify.com/v1/me/player/currently-playing"
)
SPOTIFY_SCOPE = "user-read-currently-playing user-read-playback-state"

DEFAULT_SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
DEFAULT_POLL_SECONDS = 1.0
DEFAULT_ALBUM_COLOR_MIN_LUMINANCE = 0.08
DEFAULT_ALBUM_COLOR_MIN_SATURATION = 0.12
DEFAULT_ALBUM_COLOR_FALLBACK = "#ff6600"
DEFAULT_TUYA_ENDPOINT = "https://openapi.tuyain.com"
DEFAULT_TUYA_MIN_VALUE_PERCENT = 35.0
DEFAULT_SPOTIFY_CACHE_FILE = ".cache/spotify_token.json"

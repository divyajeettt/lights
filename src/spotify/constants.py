"""Constants for Spotify integration."""

SPOTIFY_AUTH_URL = "https://accounts.spotify.com/authorize"
SPOTIFY_TOKEN_URL = "https://accounts.spotify.com/api/token"
SPOTIFY_CURRENTLY_PLAYING_URL = "https://api.spotify.com/v1/me/player/currently-playing"
SPOTIFY_SCOPE = "user-read-currently-playing user-read-playback-state"
SPOTIFY_PKCE_METHOD = "S256"
SPOTIFY_RESPONSE_TYPE = "code"
SPOTIFY_REDIRECT_URI = "http://127.0.0.1:8888/callback"
SPOTIFY_LOCAL_REDIRECT_SCHEME = "http"
SPOTIFY_LOCAL_REDIRECT_HOSTS = {"127.0.0.1", "localhost"}
SPOTIFY_CACHE_FILE = ".cache/spotify_token.json"
SPOTIFY_CALLBACK_TIMEOUT_SECONDS = 300
SPOTIFY_CALLBACK_POLL_SECONDS = 1.0

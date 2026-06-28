"""Shared constants for configuration helpers."""

from typing import Final

ENV_PATH: Final[str] = ".env"
TRUE_ENV_VALUES: Final[set[str]] = {"1", "true", "yes", "y", "on"}
FALSE_ENV_VALUES: Final[set[str]] = {"0", "false", "no", "n", "off"}
SPOTIFY_CLIENT_ID_PLACEHOLDERS: Final[set[str]] = {
    "your_spotify_client_id",
    "your_spotify_client_id_here",
}

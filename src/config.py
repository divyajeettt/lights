"""Environment and configuration helpers."""

from __future__ import annotations

import os
from pathlib import Path

from src.constants import DEFAULT_SPOTIFY_REDIRECT_URI


class ConfigError(RuntimeError):
    pass


def load_dotenv(path: str = ".env") -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        os.environ.setdefault(key, value)


def env(name: str, default: str | None = None, required: bool = False) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value or ""


def env_float(name: str, default: float) -> float:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    return float(value)


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    raise ConfigError(f"{name} must be true or false")


def validate_spotify_client_id(client_id: str) -> None:
    value = client_id.strip()
    if value in {"your_spotify_client_id", "your_spotify_client_id_here"}:
        raise ConfigError(
            "SPOTIFY_CLIENT_ID is still the placeholder. Use the Client ID "
            "from https://developer.spotify.com/dashboard, not your Spotify "
            "username or password."
        )
    if "@" in value or " " in value or ":" in value:
        raise ConfigError(
            "SPOTIFY_CLIENT_ID does not look like a Spotify Developer app "
            "Client ID. It should be the public Client ID from the Spotify "
            "Developer Dashboard."
        )
    if len(value) != 32 or not value.isalnum():
        raise ConfigError(
            f"SPOTIFY_CLIENT_ID has length {len(value)}. Spotify Client IDs "
            "are normally 32 alphanumeric characters from the Spotify "
            "Developer Dashboard."
        )


def default_spotify_redirect_uri() -> str:
    return DEFAULT_SPOTIFY_REDIRECT_URI

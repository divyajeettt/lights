"""Environment and configuration helpers."""

import os
from pathlib import Path

TRUE_ENV_VALUES = {"1", "true", "yes", "y", "on"}
FALSE_ENV_VALUES = {"0", "false", "no", "n", "off"}
SPOTIFY_CLIENT_ID_PLACEHOLDERS = {
    "your_spotify_client_id",
    "your_spotify_client_id_here",
}


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
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc


def env_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_ENV_VALUES:
        return True
    if normalized in FALSE_ENV_VALUES:
        return False
    raise ConfigError(f"{name} must be true or false")


def env_csv(name: str, default: str | None = None, required: bool = False) -> list[str]:
    raw_value = env(name, default, required)
    if not raw_value:
        return []
    values = [item.strip() for item in raw_value.split(",")]
    if any(not item for item in values):
        raise ConfigError(f"{name} must be a comma-separated list without empty values")
    return values


def validate_spotify_client_id(client_id: str) -> None:
    value = client_id.strip()
    if value in SPOTIFY_CLIENT_ID_PLACEHOLDERS:
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

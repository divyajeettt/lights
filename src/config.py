"""Environment and configuration helpers."""

import csv
import os
from pathlib import Path

from src.constants import (
    ENV_PATH,
    FALSE_ENV_VALUES,
    SPOTIFY_CLIENT_ID_PLACEHOLDERS,
    TRUE_ENV_VALUES,
)


class ConfigError(RuntimeError):
    pass


def _raw_env(name: str, default: str | None, required: bool) -> str:
    value = os.environ.get(name, default)
    if required and not value:
        raise ConfigError(f"Missing required environment variable: {name}")
    return value or ""


def _unquote(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def load_dotenv(path: str = ENV_PATH) -> None:
    env_path = Path(path)
    if not env_path.exists():
        return
    for raw_line in env_path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        os.environ.setdefault(key, value)


def env(name: str, default: str | None = None, required: bool = False) -> str:
    return _unquote(_raw_env(name, default, required))


def env_float(name: str, default: float) -> float:
    value = env(name)
    if not value:
        return default
    try:
        return float(value)
    except ValueError as exc:
        raise ConfigError(f"{name} must be a number") from exc


def env_bool(name: str, default: bool) -> bool:
    value = env(name)
    if not value:
        return default
    normalized = value.strip().lower()
    if normalized in TRUE_ENV_VALUES:
        return True
    if normalized in FALSE_ENV_VALUES:
        return False
    raise ConfigError(f"{name} must be true or false")


def env_csv(name: str, default: str | None = None, required: bool = False) -> list[str]:
    raw_value = _raw_env(name, default, required)
    if not raw_value:
        return []
    # Preserve compatibility with existing .env files that single-quote the
    # complete list. Double quotes remain available for standard CSV fields.
    if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == "'":
        raw_value = raw_value[1:-1]
    try:
        values = [
            item.strip()
            for item in next(
                csv.reader([raw_value], skipinitialspace=True, strict=True)
            )
        ]
    except csv.Error as exc:
        raise ConfigError(f"{name} must be a valid comma-separated list") from exc
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

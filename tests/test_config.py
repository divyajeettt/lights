import pytest

from src.config import (
    ConfigError,
    env_bool,
    env_csv,
    env_float,
    validate_spotify_client_id,
)

FEATURE_FLAG = "FEATURE_FLAG"
INVALID_BOOL_VALUE = "maybe"
FLOAT_SETTING = "FLOAT_SETTING"
VALID_SPOTIFY_CLIENT_ID = "a" * 32


def test_env_bool_parses_true_value(monkeypatch) -> None:
    monkeypatch.setenv(FEATURE_FLAG, "yes")
    assert env_bool(FEATURE_FLAG, default=False) is True


def test_env_bool_rejects_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv(FEATURE_FLAG, INVALID_BOOL_VALUE)
    with pytest.raises(ConfigError):
        env_bool(FEATURE_FLAG, default=False)


def test_env_float_rejects_invalid_value_with_variable_name(monkeypatch) -> None:
    monkeypatch.setenv(FLOAT_SETTING, "not-a-number")

    with pytest.raises(ConfigError, match=FLOAT_SETTING):
        env_float(FLOAT_SETTING, default=1.0)


def test_env_csv_parses_comma_separated_values(monkeypatch) -> None:
    monkeypatch.setenv("DEVICE_IDS", "first, second")

    assert env_csv("DEVICE_IDS") == ["first", "second"]


def test_env_csv_rejects_empty_items(monkeypatch) -> None:
    monkeypatch.setenv("DEVICE_IDS", "first,,second")

    with pytest.raises(ConfigError, match="DEVICE_IDS"):
        env_csv("DEVICE_IDS")


def test_validate_spotify_client_id_rejects_placeholder() -> None:
    with pytest.raises(ConfigError):
        validate_spotify_client_id("your_spotify_client_id")


def test_validate_spotify_client_id_accepts_valid_value() -> None:
    validate_spotify_client_id(VALID_SPOTIFY_CLIENT_ID)

import pytest

from src.config import ConfigError, env_bool, validate_spotify_client_id


def test_env_bool_parses_true_value(monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "yes")
    assert env_bool("FEATURE_FLAG", default=False) is True


def test_env_bool_rejects_invalid_value(monkeypatch) -> None:
    monkeypatch.setenv("FEATURE_FLAG", "maybe")
    with pytest.raises(ConfigError):
        env_bool("FEATURE_FLAG", default=False)


def test_validate_spotify_client_id_rejects_placeholder() -> None:
    with pytest.raises(ConfigError):
        validate_spotify_client_id("your_spotify_client_id")


def test_validate_spotify_client_id_accepts_valid_value() -> None:
    validate_spotify_client_id("a" * 32)

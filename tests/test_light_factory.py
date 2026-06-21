import pytest

import src.light.factory as light_factory_module
from src.config import ConfigError
from src.light import build_light_controller


def test_build_light_controller_returns_none_for_dry_run() -> None:
    assert build_light_controller(dry_run=True) is None


def test_build_light_controller_builds_tuya_backend(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "tuya_cloud")
    sentinel = object()
    monkeypatch.setattr(
        light_factory_module,
        "TuyaCloudLightController",
        lambda: sentinel,
    )

    assert build_light_controller(dry_run=False) is sentinel


def test_build_light_controller_builds_home_assistant_backend(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "homeassistant")
    sentinel = object()
    monkeypatch.setattr(
        light_factory_module,
        "HomeAssistantLightController",
        lambda: sentinel,
    )

    assert build_light_controller(dry_run=False) is sentinel


def test_build_light_controller_rejects_invalid_backend(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "invalid")

    with pytest.raises(ConfigError):
        build_light_controller(dry_run=False)

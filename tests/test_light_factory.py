import pytest

import src.light.factory as light_factory_module
from src.config import ConfigError
from src.light import (
    GroupLightController,
    build_light_controller,
    configured_light_count,
)


def test_build_light_controller_builds_tuya_backend(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "tuya_cloud")
    monkeypatch.setenv("TUYA_DEVICE_ID", "device-1")
    sentinel = object()
    monkeypatch.setattr(
        light_factory_module,
        "TuyaCloudLightController",
        lambda device_id=None, label=None: sentinel,
    )

    assert build_light_controller() is sentinel


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

    assert build_light_controller() is sentinel


def test_build_light_controller_builds_tuya_group(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "tuya_cloud")
    monkeypatch.setenv("TUYA_DEVICE_IDS", "device-1,device-2")
    monkeypatch.setenv("TUYA_DEVICE_LABELS", "desk,floor")
    labels = []

    class StubSingleController:
        @property
        def light_count(self):
            return 1

        @property
        def light_labels(self):
            return ("bulb",)

        def set_rgb(self, _rgb):
            pass

        def set_rgbs(self, _rgbs):
            pass

    def make_controller(device_id=None, label=None):
        labels.append(label)
        return StubSingleController()

    monkeypatch.setattr(
        light_factory_module,
        "TuyaCloudLightController",
        make_controller,
    )

    controller = build_light_controller()

    assert isinstance(controller, GroupLightController)
    assert controller.light_count == 2
    assert labels == ["desk", "floor"]


def test_build_light_controller_defaults_tuya_labels(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "tuya_cloud")
    monkeypatch.setenv("TUYA_DEVICE_IDS", "device-1,device-2")
    labels = []

    class StubSingleController:
        @property
        def light_count(self):
            return 1

        @property
        def light_labels(self):
            return ("bulb",)

        def set_rgb(self, _rgb):
            pass

        def set_rgbs(self, _rgbs):
            pass

    def make_controller(device_id=None, label=None):
        labels.append(label)
        return StubSingleController()

    monkeypatch.setattr(
        light_factory_module,
        "TuyaCloudLightController",
        make_controller,
    )

    build_light_controller()

    assert labels == ["bulb 1", "bulb 2"]


def test_build_light_controller_rejects_mismatched_tuya_labels(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "tuya_cloud")
    monkeypatch.setenv("TUYA_DEVICE_IDS", "device-1,device-2")
    monkeypatch.setenv("TUYA_DEVICE_LABELS", "desk")

    with pytest.raises(ConfigError, match="TUYA_DEVICE_LABELS"):
        build_light_controller()


def test_configured_light_count_uses_tuya_device_ids(monkeypatch) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "tuya_cloud")
    monkeypatch.setenv("TUYA_DEVICE_IDS", "device-1,device-2")

    assert configured_light_count() == 2


def test_build_light_controller_rejects_invalid_backend(
    monkeypatch,
) -> None:
    monkeypatch.setenv("LIGHT_BACKEND", "invalid")

    with pytest.raises(ConfigError):
        build_light_controller()

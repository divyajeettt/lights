import pytest

import src.light.factory as light_factory_module
from src.config import ConfigError
from src.light import (
    GroupLightController,
    TinyTuyaDeviceConfig,
    build_light_controller,
    configured_light_count,
    configured_tinytuya_devices,
)


def configure_devices(monkeypatch, count: int = 1) -> None:
    indexes = range(1, count + 1)
    monkeypatch.setenv(
        "TUYA_DEVICE_IDS", ",".join(f"device-{index}" for index in indexes)
    )
    monkeypatch.setenv(
        "TUYA_DEVICE_IPS", ",".join(f"192.168.1.{index}" for index in indexes)
    )
    monkeypatch.setenv(
        "TUYA_LOCAL_KEYS", ",".join(f"test-key-{index:07d}" for index in indexes)
    )
    monkeypatch.setenv("TUYA_PROTOCOL_VERSIONS", ",".join("3.3" for _ in indexes))


class StubSingleController:
    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs
        self.label = kwargs["label"]

    @property
    def light_count(self):
        return 1

    @property
    def light_labels(self):
        return (self.label,)

    def set_rgb(self, _rgb):
        pass

    def set_rgbs(self, _rgbs):
        pass


def test_configured_tinytuya_devices_parses_parallel_values(monkeypatch) -> None:
    configure_devices(monkeypatch, count=2)
    monkeypatch.setenv("TUYA_PROTOCOL_VERSIONS", "3.3,3.5")
    monkeypatch.setenv("TUYA_DEVICE_LABELS", "desk,floor")

    assert configured_tinytuya_devices() == [
        TinyTuyaDeviceConfig(
            "device-1", "192.168.1.1", "test-key-0000001", 3.3, "desk"
        ),
        TinyTuyaDeviceConfig(
            "device-2", "192.168.1.2", "test-key-0000002", 3.5, "floor"
        ),
    ]


def test_build_light_controller_builds_single_local_backend(monkeypatch) -> None:
    configure_devices(monkeypatch)
    built = []

    def make_controller(**kwargs):
        controller = StubSingleController(**kwargs)
        built.append(controller)
        return controller

    monkeypatch.setattr(
        light_factory_module, "TinyTuyaLightController", make_controller
    )

    controller = build_light_controller()

    assert controller is built[0]
    assert built[0].kwargs == {
        "device_id": "device-1",
        "address": "192.168.1.1",
        "local_key": "test-key-0000001",
        "protocol_version": 3.3,
        "label": "bulb 1",
    }


def test_configured_tinytuya_devices_defaults_labels(monkeypatch) -> None:
    configure_devices(monkeypatch, count=2)

    devices = configured_tinytuya_devices()

    assert [device.label for device in devices] == ["bulb 1", "bulb 2"]


def test_build_light_controller_builds_group_with_labels(monkeypatch) -> None:
    configure_devices(monkeypatch, count=2)
    monkeypatch.setenv("TUYA_DEVICE_LABELS", "desk,floor")
    monkeypatch.setattr(
        light_factory_module,
        "TinyTuyaLightController",
        lambda **kwargs: StubSingleController(**kwargs),
    )

    controller = build_light_controller()

    assert isinstance(controller, GroupLightController)
    assert controller.light_count == 2
    assert controller.light_labels == ("desk", "floor")


@pytest.mark.parametrize(
    "name,value",
    [
        ("TUYA_DEVICE_IPS", "192.168.1.1"),
        ("TUYA_LOCAL_KEYS", "key-1"),
        ("TUYA_PROTOCOL_VERSIONS", "3.3"),
        ("TUYA_DEVICE_LABELS", "desk"),
    ],
)
def test_build_light_controller_rejects_mismatched_lists(
    monkeypatch, name, value
) -> None:
    configure_devices(monkeypatch, count=2)
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigError, match=name):
        build_light_controller()


def test_build_light_controller_rejects_unsupported_protocol(monkeypatch) -> None:
    configure_devices(monkeypatch)
    monkeypatch.setenv("TUYA_PROTOCOL_VERSIONS", "2.1")

    with pytest.raises(ConfigError, match="TUYA_PROTOCOL_VERSIONS entry 1"):
        build_light_controller()


def test_build_light_controller_rejects_invalid_local_key_length(monkeypatch) -> None:
    configure_devices(monkeypatch)
    monkeypatch.setenv("TUYA_LOCAL_KEYS", "short")

    with pytest.raises(ConfigError, match="TUYA_LOCAL_KEYS entry 1"):
        build_light_controller()


@pytest.mark.parametrize(
    "name,value,error",
    [
        ("TUYA_LOCAL_KEYS", "test-key-0000001,short", "TUYA_LOCAL_KEYS entry 2"),
        (
            "TUYA_PROTOCOL_VERSIONS",
            "3.3,2.1",
            "TUYA_PROTOCOL_VERSIONS entry 2",
        ),
    ],
)
def test_configured_tinytuya_devices_validates_each_record(
    monkeypatch, name, value, error
) -> None:
    configure_devices(monkeypatch, count=2)
    monkeypatch.setenv(name, value)

    with pytest.raises(ConfigError, match=error):
        configured_tinytuya_devices()


def test_build_light_controller_requires_every_local_setting(monkeypatch) -> None:
    monkeypatch.setenv("TUYA_DEVICE_IDS", "device-1")

    with pytest.raises(ConfigError, match="TUYA_DEVICE_IPS"):
        build_light_controller()


def test_configured_light_count_uses_tuya_device_ids(monkeypatch) -> None:
    monkeypatch.setenv("TUYA_DEVICE_IDS", "device-1,device-2")

    assert configured_light_count() == 2

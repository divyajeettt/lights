import pytest

import src.light.tiny_tuya as tiny_tuya_module
from src.light import TinyTuyaLightController


class StubBulbDevice:
    def __init__(self, device_id, address, local_key) -> None:
        self.constructor_args = (device_id, address, local_key)
        self.version = None
        self.hsv_colours = []
        self.power_calls = []
        self.current_state = {"is_on": True}
        self.next_result = None

    def set_version(self, version) -> None:
        self.version = version

    def set_hsv(self, hue, saturation, value):
        self.hsv_colours.append((hue, saturation, value))
        return self.next_result

    def turn_on(self):
        self.power_calls.append(True)
        return self.next_result

    def turn_off(self):
        self.power_calls.append(False)
        return self.next_result

    def state(self):
        return self.current_state


def make_controller(monkeypatch):
    devices = []

    def make_device(*args):
        device = StubBulbDevice(*args)
        devices.append(device)
        return device

    monkeypatch.setattr(tiny_tuya_module.tinytuya, "BulbDevice", make_device)
    controller = TinyTuyaLightController(
        device_id="device-1",
        address="192.168.1.10",
        local_key="secret-key",
        protocol_version=3.3,
        label="desk",
    )
    return controller, devices[0]


def test_controller_configures_local_bulb(monkeypatch) -> None:
    controller, device = make_controller(monkeypatch)

    assert controller.light_labels == ("desk",)
    assert device.constructor_args == ("device-1", "192.168.1.10", "secret-key")
    assert device.version == 3.3


def test_controller_preserves_application_hsv_policy(monkeypatch) -> None:
    controller, device = make_controller(monkeypatch)

    controller.set_rgb((0, 170, 255))

    assert device.hsv_colours == [pytest.approx((200 / 360, 1.0, 0.401))]


def test_controller_sets_power(monkeypatch) -> None:
    controller, device = make_controller(monkeypatch)

    controller.set_power(True)
    controller.set_power(False)

    assert device.power_calls == [True, False]


@pytest.mark.parametrize(
    "is_on,expected_power",
    [(True, False), (False, True)],
)
def test_controller_toggles_from_local_state(
    monkeypatch, is_on, expected_power
) -> None:
    controller, device = make_controller(monkeypatch)
    device.current_state = {"is_on": is_on}

    controller.switch()

    assert device.power_calls == [expected_power]


def test_controller_rejects_state_without_boolean(monkeypatch) -> None:
    controller, device = make_controller(monkeypatch)
    device.current_state = {"is_on": "true"}

    with pytest.raises(RuntimeError, match="boolean is_on"):
        controller.switch()


def test_controller_raises_tinytuya_error_response(monkeypatch) -> None:
    controller, device = make_controller(monkeypatch)
    device.next_result = {"Error": "offline", "Err": "905"}

    with pytest.raises(RuntimeError, match=r"offline \(code 905\)"):
        controller.set_power(True)


def test_controller_redacts_local_key_from_exception(monkeypatch) -> None:
    controller, device = make_controller(monkeypatch)

    def fail():
        raise OSError("connection failed using secret-key")

    device.turn_on = fail

    with pytest.raises(RuntimeError) as error:
        controller.set_power(True)

    assert "secret-key" not in str(error.value)
    assert "[redacted]" in str(error.value)

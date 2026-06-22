import src.light.tuya as tuya_module
from src.light import (
    TuyaCloudLightController,
    TuyaCommandField,
    TuyaHsvField,
    TuyaLightSpec,
)


class StubTuyaClient:
    def __init__(self) -> None:
        self.device_id = "device-1"
        self.commands = None

    def device_specification(self):
        return {"functions": []}

    def send_commands(self, commands):
        self.commands = commands


def make_controller(
    monkeypatch,
) -> tuple[TuyaCloudLightController, StubTuyaClient]:
    client = StubTuyaClient()
    spec = TuyaLightSpec(
        color_code="colour_data_v2",
        h_max=360,
        s_max=1000,
        v_max=1000,
    )
    monkeypatch.setattr(tuya_module, "TuyaCloudClient", lambda device_id=None: client)
    monkeypatch.setattr(tuya_module, "infer_tuya_light_spec", lambda _spec: spec)
    return TuyaCloudLightController(), client


def test_tuya_controller_sends_only_color_command_by_default(monkeypatch) -> None:
    controller, client = make_controller(monkeypatch)

    controller.set_rgb((0, 170, 255))

    assert client.commands == [
        {
            TuyaCommandField.CODE: "colour_data_v2",
            TuyaCommandField.VALUE: {
                TuyaHsvField.HUE: 200,
                TuyaHsvField.SATURATION: 1000,
                TuyaHsvField.VALUE: 401,
            },
        }
    ]


def test_tuya_controller_uses_black_distance_brightness(monkeypatch) -> None:
    controller, client = make_controller(monkeypatch)

    controller.set_rgb((0, 170, 255))

    assert client.commands[0][TuyaCommandField.VALUE][TuyaHsvField.VALUE] == 401

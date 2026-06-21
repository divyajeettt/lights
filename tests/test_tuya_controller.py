import src.light.tuya as tuya_module
from src.light.tuya import TuyaCloudLightController
from src.light.tuya import TuyaLightSpec


class StubTuyaClient:
    def __init__(self) -> None:
        self.commands = None

    def device_specification(self):
        return {"functions": []}

    def send_commands(self, commands):
        self.commands = commands


def make_controller(
    monkeypatch,
    *,
    ensure_on_color_mode: bool,
    color_value_format: str = "object",
) -> tuple[TuyaCloudLightController, StubTuyaClient]:
    client = StubTuyaClient()
    spec = TuyaLightSpec(
        switch_code="switch_led",
        work_mode_code="work_mode",
        work_mode_value="colour",
        color_code="colour_data_v2",
        h_max=360,
        s_max=1000,
        v_max=1000,
        color_value_format=color_value_format,
    )
    monkeypatch.setattr(tuya_module, "TuyaCloudClient", lambda: client)
    monkeypatch.setattr(tuya_module, "infer_tuya_light_spec", lambda _spec: spec)
    monkeypatch.setenv(
        "TUYA_ENSURE_ON_COLOR_MODE",
        "true" if ensure_on_color_mode else "false",
    )
    monkeypatch.setenv("TUYA_MIN_VALUE_PERCENT", "35")
    return TuyaCloudLightController(), client


def test_tuya_controller_sends_only_color_command_by_default(
    monkeypatch,
) -> None:
    controller, client = make_controller(
        monkeypatch,
        ensure_on_color_mode=False,
    )

    controller.set_rgb((0, 170, 255))

    assert client.commands == [
        {
            "code": "colour_data_v2",
            "value": {"h": 200, "s": 1000, "v": 1000},
        }
    ]


def test_tuya_controller_can_include_mode_commands(monkeypatch) -> None:
    controller, client = make_controller(
        monkeypatch,
        ensure_on_color_mode=True,
    )

    controller.set_rgb((0, 170, 255))

    assert client.commands[0] == {"code": "switch_led", "value": True}
    assert client.commands[1] == {"code": "work_mode", "value": "colour"}
    assert client.commands[2]["code"] == "colour_data_v2"


def test_tuya_controller_can_send_string_color_payload(monkeypatch) -> None:
    controller, client = make_controller(
        monkeypatch,
        ensure_on_color_mode=False,
        color_value_format="string",
    )

    controller.set_rgb((0, 170, 255))

    assert client.commands == [
        {
            "code": "colour_data_v2",
            "value": '{"h":200,"s":1000,"v":1000}',
        }
    ]

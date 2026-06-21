from src.enums import TuyaEnvVar
from src.light import infer_tuya_light_spec


def test_infer_tuya_light_spec_prefers_colour_data_v2(monkeypatch) -> None:
    monkeypatch.setenv(TuyaEnvVar.SWITCH_CODE, "auto")
    monkeypatch.setenv(TuyaEnvVar.WORK_MODE_CODE, "auto")
    monkeypatch.setenv(TuyaEnvVar.COLOR_CODE, "auto")
    monkeypatch.setenv(TuyaEnvVar.COLOR_VALUE_FORMAT, "auto")
    monkeypatch.delenv(TuyaEnvVar.WORK_MODE_VALUE, raising=False)

    spec = {
        "functions": [
            {
                "code": "switch_led",
                "values": "{}",
            },
            {
                "code": "work_mode",
                "values": '{"range":["white","colour"]}',
            },
            {
                "code": "colour_data_v2",
                "values": '{"h":{"max":360},"s":{"max":1000},' '"v":{"max":1000}}',
            },
        ]
    }

    inferred = infer_tuya_light_spec(spec)

    assert inferred.switch_code == "switch_led"
    assert inferred.work_mode_code == "work_mode"
    assert inferred.work_mode_value == "colour"
    assert inferred.color_code == "colour_data_v2"
    assert inferred.s_max == 1000
    assert inferred.v_max == 1000
    assert inferred.color_value_format == "object"

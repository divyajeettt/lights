from src.light import infer_tuya_light_spec


def test_infer_tuya_light_spec_prefers_colour_data_v2() -> None:
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

    assert inferred.color_code == "colour_data_v2"
    assert inferred.s_max == 1000
    assert inferred.v_max == 1000

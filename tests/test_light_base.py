import pytest

from src.light import GroupLightController


class StubLightController:
    def __init__(self, label: str, fail: bool = False) -> None:
        self.label = label
        self.fail = fail
        self.switch_calls = 0

    @property
    def light_count(self) -> int:
        return 1

    @property
    def light_labels(self) -> tuple[str, ...]:
        return (self.label,)

    def set_rgb(self, _rgb) -> None:
        pass

    def set_rgbs(self, _rgbs) -> None:
        pass

    def switch(self) -> None:
        self.switch_calls += 1
        if self.fail:
            raise RuntimeError("offline")


def test_group_light_controller_switches_all_lights() -> None:
    desk = StubLightController("desk")
    floor = StubLightController("floor")
    controller = GroupLightController([desk, floor])

    controller.switch()

    assert desk.switch_calls == 1
    assert floor.switch_calls == 1


def test_group_light_controller_switch_aggregates_errors() -> None:
    desk = StubLightController("desk")
    floor = StubLightController("floor", fail=True)
    controller = GroupLightController([desk, floor])

    with pytest.raises(RuntimeError, match="Failed to switch one or more lights"):
        controller.switch()

    assert desk.switch_calls == 1
    assert floor.switch_calls == 1

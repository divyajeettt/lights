from threading import Event

import pytest

import src.light.base as light_base_module
from src.light import GroupLightController


class StubLightController:
    def __init__(
        self,
        label: str,
        fail: bool = False,
        block_until: Event | None = None,
    ) -> None:
        self.label = label
        self.fail = fail
        self.block_until = block_until
        self.rgb_calls = []
        self.power_calls: list[bool] = []
        self.switch_calls = 0

    @property
    def light_count(self) -> int:
        return 1

    @property
    def light_labels(self) -> tuple[str, ...]:
        return (self.label,)

    def set_rgb(self, rgb) -> None:
        self.rgb_calls.append(rgb)
        if self.block_until is not None:
            self.block_until.wait()
        if self.fail:
            raise RuntimeError("offline")

    def set_rgbs(self, _rgbs) -> None:
        pass

    def set_power(self, on: bool) -> None:
        self.power_calls.append(on)
        if self.fail:
            raise RuntimeError("offline")

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


def test_group_light_controller_updates_lights_concurrently() -> None:
    release_slow_bulb = Event()
    slow_started = Event()

    class SlowController(StubLightController):
        def set_rgb(self, rgb) -> None:
            self.rgb_calls.append(rgb)
            slow_started.set()
            release_slow_bulb.wait()

    class FastController(StubLightController):
        def set_rgb(self, rgb) -> None:
            assert slow_started.wait(timeout=0.5)
            self.rgb_calls.append(rgb)
            release_slow_bulb.set()

    desk = SlowController("desk")
    floor = FastController("floor")
    controller = GroupLightController([desk, floor])

    controller.set_rgbs([(1, 2, 3), (4, 5, 6)])

    assert desk.rgb_calls == [(1, 2, 3)]
    assert floor.rgb_calls == [(4, 5, 6)]


def test_group_light_controller_times_out_only_slow_light(monkeypatch) -> None:
    monkeypatch.setattr(
        light_base_module,
        "GROUP_LIGHT_OPERATION_TIMEOUT_SECONDS",
        0.01,
    )
    release_slow_bulb = Event()
    desk = StubLightController("desk", block_until=release_slow_bulb)
    floor = StubLightController("floor")
    controller = GroupLightController([desk, floor])

    try:
        with pytest.raises(RuntimeError) as exc_info:
            controller.set_rgbs([(1, 2, 3), (4, 5, 6)])
    finally:
        release_slow_bulb.set()

    assert str(exc_info.value) == (
        "Failed to update one or more lights: desk: timed out after 0.01 seconds"
    )
    assert floor.rgb_calls == [(4, 5, 6)]


def test_group_light_controller_aggregates_errors_in_label_order() -> None:
    desk = StubLightController("desk", fail=True)
    floor = StubLightController("floor", fail=True)
    controller = GroupLightController([desk, floor])

    with pytest.raises(RuntimeError) as exc_info:
        controller.set_rgbs([(1, 2, 3)])

    assert str(exc_info.value) == (
        "Failed to update one or more lights: desk: offline; floor: offline"
    )


def test_group_light_controller_switch_aggregates_errors() -> None:
    desk = StubLightController("desk")
    floor = StubLightController("floor", fail=True)
    controller = GroupLightController([desk, floor])

    with pytest.raises(RuntimeError, match="Failed to switch one or more lights"):
        controller.switch()

    assert desk.switch_calls == 1
    assert floor.switch_calls == 1


def test_group_light_controller_sets_power_for_all_lights() -> None:
    desk = StubLightController("desk")
    floor = StubLightController("floor")
    controller = GroupLightController([desk, floor])

    controller.set_power(True)

    assert desk.power_calls == [True]
    assert floor.power_calls == [True]


def test_group_light_controller_set_power_aggregates_errors() -> None:
    desk = StubLightController("desk")
    floor = StubLightController("floor", fail=True)
    controller = GroupLightController([desk, floor])

    with pytest.raises(
        RuntimeError, match="Failed to set power for one or more lights"
    ):
        controller.set_power(False)

    assert desk.power_calls == [False]
    assert floor.power_calls == [False]

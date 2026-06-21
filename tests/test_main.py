import sys

import main as cli
from src.config import ConfigError


class StubController:
    def __init__(self) -> None:
        self.calls: list[tuple[int, int, int]] = []

    def set_rgb(self, rgb: tuple[int, int, int]) -> None:
        self.calls.append(rgb)


def run_cli(monkeypatch, tmp_path, args: list[str]) -> int:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(sys, "argv", ["lights", *args])
    return cli.main()


def test_main_preserves_config_error_exit(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("POLL_SECONDS", "not-a-number")

    result = run_cli(monkeypatch, tmp_path, [])

    captured = capsys.readouterr()
    assert result == 2
    assert "Configuration error: POLL_SECONDS must be a number" in captured.err


def test_main_rejects_non_positive_poll_before_watcher(
    monkeypatch,
    tmp_path,
    capsys,
) -> None:
    calls: list[str] = []

    monkeypatch.setenv("POLL_SECONDS", "0")
    monkeypatch.setattr(
        cli,
        "build_spotify",
        lambda: calls.append("spotify"),
    )
    monkeypatch.setattr(cli, "run_watcher", lambda **_kwargs: calls.append("watcher"))

    result = run_cli(monkeypatch, tmp_path, [])

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: POLL_SECONDS must be greater than 0" in captured.err
    assert calls == []


def test_main_default_run_calls_watcher(monkeypatch, tmp_path) -> None:
    controller = StubController()
    calls = {}

    monkeypatch.setattr(cli, "build_spotify", lambda: "spotify")
    monkeypatch.setattr(cli, "build_light_controller", lambda: controller)

    def run_watcher(**kwargs):
        calls.update(kwargs)
        return 0

    monkeypatch.setattr(cli, "run_watcher", run_watcher)

    result = run_cli(monkeypatch, tmp_path, [])

    assert result == 0
    assert calls == {
        "spotify": "spotify",
        "controller": controller,
        "poll_seconds": 1.0,
        "dry_run_once": False,
    }


def test_main_dry_run_once_calls_watcher_without_controller(
    monkeypatch,
    tmp_path,
) -> None:
    calls = {}

    monkeypatch.setattr(cli, "build_spotify", lambda: "spotify")

    def fail_build_light_controller():
        raise AssertionError("dry-run-once should not build a light controller")

    def run_watcher(**kwargs):
        calls.update(kwargs)
        return 0

    monkeypatch.setattr(cli, "build_light_controller", fail_build_light_controller)
    monkeypatch.setattr(cli, "run_watcher", run_watcher)

    result = run_cli(monkeypatch, tmp_path, ["--dry-run-once"])

    assert result == 0
    assert calls == {
        "spotify": "spotify",
        "controller": None,
        "poll_seconds": 1.0,
        "dry_run_once": True,
    }


def test_main_set_rgb_uses_light_controller_without_spotify(monkeypatch, tmp_path) -> None:
    controller = StubController()

    def fail_build_spotify():
        raise AssertionError("--set-rgb should not build Spotify")

    monkeypatch.setattr(cli, "build_spotify", fail_build_spotify)
    monkeypatch.setattr(cli, "build_light_controller", lambda: controller)

    result = run_cli(monkeypatch, tmp_path, ["--set-rgb", "#00aaff"])

    assert result == 0
    assert controller.calls == [(0, 170, 255)]


def test_main_set_rgb_does_not_require_poll_seconds(monkeypatch, tmp_path) -> None:
    controller = StubController()

    monkeypatch.setenv("POLL_SECONDS", "not-a-number")
    monkeypatch.setattr(cli, "build_light_controller", lambda: controller)

    result = run_cli(monkeypatch, tmp_path, ["--set-rgb", "#00aaff"])

    assert result == 0
    assert controller.calls == [(0, 170, 255)]


def test_main_set_rgb_rejects_invalid_color(monkeypatch, tmp_path, capsys) -> None:
    result = run_cli(monkeypatch, tmp_path, ["--set-rgb", "abc"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: RGB color must look like #00aaff" in captured.err


def test_main_rejects_set_rgb_with_dry_run_once(monkeypatch, tmp_path, capsys) -> None:
    result = run_cli(
        monkeypatch,
        tmp_path,
        ["--set-rgb", "#00aaff", "--dry-run-once"],
    )

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: --set-rgb cannot be combined with --dry-run-once" in captured.err


def test_main_preserves_late_config_error_exit(monkeypatch, tmp_path, capsys) -> None:
    def fail_build_spotify():
        raise ConfigError("missing spotify client")

    monkeypatch.setattr(cli, "build_spotify", fail_build_spotify)

    result = run_cli(monkeypatch, tmp_path, ["--dry-run-once"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Configuration error: missing spotify client" in captured.err

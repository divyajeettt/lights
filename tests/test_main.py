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


def test_main_returns_user_error_for_invalid_rgb(monkeypatch, tmp_path, capsys) -> None:
    result = run_cli(monkeypatch, tmp_path, ["--rgb", "abc", "--dry-run"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: RGB color must look like #00aaff" in captured.err


def test_main_preserves_config_error_exit(monkeypatch, tmp_path, capsys) -> None:
    monkeypatch.setenv("POLL_SECONDS", "not-a-number")

    result = run_cli(monkeypatch, tmp_path, [])

    captured = capsys.readouterr()
    assert result == 2
    assert "Configuration error: POLL_SECONDS must be a number" in captured.err


def test_main_catches_runtime_error(monkeypatch, tmp_path, capsys) -> None:
    def fail_image(_url: str) -> tuple[int, int, int]:
        raise RuntimeError("image fetch failed")

    monkeypatch.setattr(cli, "dominant_rgb_from_url", fail_image)

    result = run_cli(monkeypatch, tmp_path, ["--image-url", "https://example.com/a.jpg"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: image fetch failed" in captured.err


def test_main_image_url_uses_one_shot_controller(monkeypatch, tmp_path, capsys) -> None:
    controller = StubController()

    monkeypatch.setattr(cli, "dominant_rgb_from_url", lambda _url: (1, 2, 3))
    monkeypatch.setattr(cli, "build_light_controller", lambda dry_run: controller)

    result = run_cli(monkeypatch, tmp_path, ["--image-url", "https://example.com/a.jpg"])

    captured = capsys.readouterr()
    assert result == 0
    assert "#010203" in captured.out
    assert controller.calls == [(1, 2, 3)]


def test_main_rgb_uses_one_shot_controller(monkeypatch, tmp_path) -> None:
    controller = StubController()

    monkeypatch.setattr(cli, "build_light_controller", lambda dry_run: controller)

    result = run_cli(monkeypatch, tmp_path, ["--rgb", "#00aaff"])

    assert result == 0
    assert controller.calls == [(0, 170, 255)]


def test_main_rejects_non_positive_poll_before_watcher(monkeypatch, tmp_path, capsys) -> None:
    calls: list[str] = []

    def build_spotify(*, open_browser: bool):
        calls.append("spotify")
        return object()

    def run_watcher(**_kwargs):
        calls.append("watcher")
        return 0

    monkeypatch.setattr(cli, "build_spotify", build_spotify)
    monkeypatch.setattr(cli, "run_watcher", run_watcher)

    result = run_cli(monkeypatch, tmp_path, ["--poll-seconds", "0", "--dry-run"])

    captured = capsys.readouterr()
    assert result == 1
    assert "Error: --poll-seconds must be greater than 0" in captured.err
    assert calls == []


def test_main_preserves_late_config_error_exit(monkeypatch, tmp_path, capsys) -> None:
    def fail_build_spotify(*, open_browser: bool):
        raise ConfigError("missing spotify client")

    monkeypatch.setattr(cli, "build_spotify", fail_build_spotify)

    result = run_cli(monkeypatch, tmp_path, ["--once", "--dry-run"])

    captured = capsys.readouterr()
    assert result == 2
    assert "Configuration error: missing spotify client" in captured.err

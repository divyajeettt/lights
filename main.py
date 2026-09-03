#!/usr/bin/env python3

import argparse
import sys
from typing import Final

from src.color import parse_rgb, rgb_hex
from src.config import ConfigError, load_dotenv
from src.diagnostics import run_diagnostics
from src.enums import LightColorMode
from src.light import build_light_controller, configured_light_count
from src.models import Color
from src.runner import run_watcher
from src.spotify import build_spotify

POLL_SECONDS: Final[float] = 1.0
LIGHT_COLOR_MODE: Final[LightColorMode] = LightColorMode.ALBUM_PALETTE


def _set_manual_rgb(rgb: Color, label: str | None = None) -> None:
    controller = (
        build_light_controller()
        if label is None
        else build_light_controller(label=label)
    )
    controller.set_rgb(rgb)


def _switch_lights() -> None:
    controller = build_light_controller()
    controller.switch()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync a smart bulb color to Spotify album art."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run read-only Spotify, album-art, and per-bulb diagnostics.",
    )
    parser.add_argument(
        "--dry-run-once",
        action="store_true",
        help="Process the current track once without sending bulb commands.",
    )
    parser.add_argument(
        "--set-rgb",
        metavar="COLOR",
        help="Set bulbs to a manual RGB color like #00aaff and exit.",
    )
    parser.add_argument(
        "--bulb-label",
        metavar="LABEL",
        help="With --set-rgb, update only the bulb with this exact label.",
    )
    parser.add_argument(
        "--switch",
        action="store_true",
        help="Toggle configured bulbs on or off and exit.",
    )
    parser.add_argument(
        "--auto-switch",
        action="store_true",
        help="Switch bulbs on while the app runs and off when it exits.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        load_dotenv()

        selected_actions = [
            option
            for option, selected in (
                ("--dry-run-once", args.dry_run_once),
                ("--check", args.check),
                ("--set-rgb", args.set_rgb is not None),
                ("--switch", args.switch),
                ("--auto-switch", args.auto_switch),
            )
            if selected
        ]
        if len(selected_actions) > 1:
            raise ValueError(
                f"{selected_actions[1]} cannot be combined with {selected_actions[0]}"
            )
        if args.set_rgb is None and args.bulb_label is not None:
            raise ValueError("--bulb-label can only be used with --set-rgb")

        if args.set_rgb is not None:
            rgb = parse_rgb(args.set_rgb)
            label = args.bulb_label
            target = f"bulb {label!r}" if label is not None else "bulb(s)"
            print(f"Setting {target} to {rgb_hex(rgb)}")
            _set_manual_rgb(rgb, label=label)
            return 0

        if args.check:
            return run_diagnostics()

        if args.switch:
            print("Switching bulb(s)")
            _switch_lights()
            return 0

        light_count = configured_light_count(required=not args.dry_run_once)
        spotify = build_spotify()
        controller = None if args.dry_run_once else build_light_controller()
        return run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=POLL_SECONDS,
            dry_run_once=args.dry_run_once,
            light_count=light_count,
            color_mode=LIGHT_COLOR_MODE,
            auto_switch=args.auto_switch,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

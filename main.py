#!/usr/bin/env python3

import argparse
import sys

from src.color import parse_rgb, rgb_hex
from src.config import ConfigError, load_dotenv
from src.enums import LightColorMode
from src.light import build_light_controller, configured_light_count
from src.models import Color
from src.runner import run_watcher
from src.spotify import build_spotify

POLL_SECONDS = 1.0
LIGHT_COLOR_MODE = LightColorMode.ALBUM_PALETTE


def _set_manual_rgb(rgb: Color) -> None:
    controller = build_light_controller()
    controller.set_rgb(rgb)


def _switch_lights() -> None:
    controller = build_light_controller()
    controller.switch()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Sync a smart bulb color to Spotify album art."
    )
    parser.add_argument(
        "--dry-run-once",
        action="store_true",
        help="Process the current track once without sending bulb commands.",
    )
    parser.add_argument(
        "--set-rgb",
        help="Set the bulb to a manual RGB color like #00aaff and exit.",
    )
    parser.add_argument(
        "--switch",
        action="store_true",
        help="Toggle configured bulbs on or off and exit.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        load_dotenv()

        if args.dry_run_once and args.set_rgb:
            raise ValueError("--set-rgb cannot be combined with --dry-run-once")
        if args.dry_run_once and args.switch:
            raise ValueError("--switch cannot be combined with --dry-run-once")
        if args.set_rgb and args.switch:
            raise ValueError("--switch cannot be combined with --set-rgb")

        if args.set_rgb:
            rgb = parse_rgb(args.set_rgb)
            print(f"Setting bulb(s) to {rgb_hex(rgb)}")
            _set_manual_rgb(rgb)
            return 0

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
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

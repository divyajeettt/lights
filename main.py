#!/usr/bin/env python3

import argparse
import sys

from src.color import parse_rgb, rgb_hex
from src.config import ConfigError, env_float, load_dotenv
from src.constants import DEFAULT_POLL_SECONDS
from src.enums import AppEnvVar
from src.light import build_light_controller
from src.models import Color
from src.runner import run_watcher
from src.spotify import build_spotify


def _set_manual_rgb(rgb: Color) -> None:
    controller = build_light_controller()
    controller.set_rgb(rgb)


def _validated_poll_seconds(poll_seconds: float) -> float:
    if poll_seconds <= 0:
        raise ValueError("POLL_SECONDS must be greater than 0")
    return poll_seconds


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
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        load_dotenv()

        if args.dry_run_once and args.set_rgb:
            raise ValueError("--set-rgb cannot be combined with --dry-run-once")

        if args.set_rgb:
            rgb = parse_rgb(args.set_rgb)
            print(f"Setting bulb to {rgb_hex(rgb)}")
            _set_manual_rgb(rgb)
            return 0

        poll_seconds = _validated_poll_seconds(
            env_float(AppEnvVar.POLL_SECONDS, DEFAULT_POLL_SECONDS)
        )
        spotify = build_spotify(open_browser=True)
        controller = None if args.dry_run_once else build_light_controller()
        return run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=poll_seconds,
            dry_run_once=args.dry_run_once,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2
    except (ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

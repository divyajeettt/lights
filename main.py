#!/usr/bin/env python3
from __future__ import annotations

import argparse
import sys

from src.color import dominant_rgb_from_url, parse_rgb, rgb_hex
from src.config import ConfigError, env_float, load_dotenv
from src.light import build_light_controller, print_tuya_spec
from src.runner import run_watcher, send_or_log_rgb
from src.spotify import build_spotify


def main() -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Sync a smart bulb color to Spotify album art."
    )
    parser.add_argument(
        "--once",
        action="store_true",
        help="Process the current track once and exit.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Do not send commands to the bulb.",
    )
    parser.add_argument(
        "--poll-seconds",
        type=float,
        default=env_float("POLL_SECONDS", 1.0),
        help="Spotify polling interval in seconds. Default: 1.",
    )
    parser.add_argument(
        "--no-open-browser",
        action="store_true",
        help="Print Spotify auth URL instead of opening it.",
    )
    parser.add_argument(
        "--print-tuya-spec",
        action="store_true",
        help="Print Tuya device functions/status and exit.",
    )
    parser.add_argument(
        "--image-url",
        help="Extract a dominant color from an image URL and exit.",
    )
    parser.add_argument(
        "--rgb",
        help="Set the bulb to a manual RGB color like #00aaff and exit.",
    )
    args = parser.parse_args()

    try:
        if args.print_tuya_spec:
            print_tuya_spec()
            return 0

        if args.image_url:
            rgb = dominant_rgb_from_url(args.image_url)
            print(rgb_hex(rgb))
            if args.dry_run:
                send_or_log_rgb(None, rgb, dry_run=True)
            else:
                controller = build_light_controller(False)
                assert controller is not None
                controller.set_rgb(rgb)
            return 0

        if args.rgb:
            rgb = parse_rgb(args.rgb)
            print(f"Setting bulb to {rgb_hex(rgb)}")
            if args.dry_run:
                send_or_log_rgb(None, rgb, dry_run=True)
            else:
                controller = build_light_controller(False)
                assert controller is not None
                controller.set_rgb(rgb)
            return 0

        spotify = build_spotify(open_browser=not args.no_open_browser)
        controller = build_light_controller(args.dry_run)
        return run_watcher(
            spotify=spotify,
            controller=controller,
            poll_seconds=args.poll_seconds,
            dry_run=args.dry_run,
            once=args.once,
        )
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

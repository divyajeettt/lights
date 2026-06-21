#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

from src.color.extractor import album_rgb_from_url
from src.color.extractor import dominant_rgb_from_url
from src.color.utils import parse_rgb
from src.color.utils import rgb_hex
from src.config import ConfigError
from src.config import env
from src.config import env_float
from src.config import load_dotenv
from src.config import validate_spotify_client_id
from src.constants import DEFAULT_SPOTIFY_REDIRECT_URI
from src.light.base import LightController
from src.light.factory import build_light_controller
from src.light.tuya import print_tuya_spec
from src.models import Color
from src.models import TrackColor
from src.models import TrackSummary
from src.spotify.client import SpotifyClient
from src.spotify.client import SpotifyRateLimitError


def best_album_image(item: dict[str, Any]) -> str | None:
    images = item.get("album", {}).get("images", [])
    if not images:
        return None
    return max(
        images,
        key=lambda image: image.get("width", 0) * image.get("height", 0),
    ).get("url")


def track_label(item: dict[str, Any]) -> str:
    name = item.get("name", "Unknown track")
    artists = ", ".join(
        artist.get("name", "Unknown artist")
        for artist in item.get("artists", [])
    )
    return f"{name} - {artists}" if artists else name


def current_track_summary(
    spotify: SpotifyClient,
    quiet: bool = False,
) -> TrackSummary | None:
    playback = spotify.currently_playing()
    if not playback or not playback.get("is_playing"):
        if not quiet:
            print("Spotify is not currently playing.")
        return None

    item = playback.get("item") or {}
    if item.get("type") != "track":
        if not quiet:
            print(f"Currently playing item is not a track: {item.get('type')}")
        return None

    track_id = item.get("id") or item.get("uri")
    if not track_id:
        if not quiet:
            print("Currently playing track has no Spotify ID.")
        return None

    return TrackSummary(track_id=track_id, label=track_label(item), item=item)


def track_color_from_summary(summary: TrackSummary) -> TrackColor | None:
    image_url = best_album_image(summary.item)
    if not image_url:
        print(f"No album image for {summary.label}")
        return None
    rgb, fallback_used = album_rgb_from_url(image_url)
    return TrackColor(
        track_id=summary.track_id,
        label=summary.label,
        rgb=rgb,
        fallback_used=fallback_used,
    )


def current_track_color(
    spotify: SpotifyClient,
    quiet: bool = False,
) -> TrackColor | None:
    summary = current_track_summary(spotify, quiet=quiet)
    if not summary:
        return None
    return track_color_from_summary(summary)


def send_or_log_rgb(
    controller: LightController | None,
    rgb: Color,
    dry_run: bool,
) -> None:
    if dry_run:
        print(f"Dry run: would set bulb to {rgb_hex(rgb)}")
        return
    if controller:
        controller.set_rgb(rgb)


def apply_track_color(
    controller: LightController | None,
    track: TrackColor,
    dry_run: bool,
) -> None:
    suffix = " (fallback color)" if track.fallback_used else ""
    print(f"{track.label} -> {rgb_hex(track.rgb)}{suffix}")
    send_or_log_rgb(controller, track.rgb, dry_run)
    if not dry_run:
        print("Bulb color updated.")


def build_spotify(open_browser: bool) -> SpotifyClient:
    client_id = env("SPOTIFY_CLIENT_ID", required=True)
    validate_spotify_client_id(client_id)
    redirect_uri = env("SPOTIFY_REDIRECT_URI", DEFAULT_SPOTIFY_REDIRECT_URI)
    cache_file = Path(env("SPOTIFY_CACHE_FILE", ".cache/spotify_token.json"))
    return SpotifyClient(
        client_id,
        redirect_uri,
        cache_file,
        open_browser=open_browser,
    )

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
        last_track_id = None

        while True:
            try:
                track = current_track_color(spotify)
                if track and track.track_id != last_track_id:
                    apply_track_color(controller, track, args.dry_run)
                    last_track_id = track.track_id
            except SpotifyRateLimitError as exc:
                print(
                    f"Spotify rate limited the request; sleeping "
                    f"{exc.retry_after}s.",
                    file=sys.stderr,
                )
                if args.once:
                    return 1
                time.sleep(exc.retry_after)
                continue
            except Exception as exc:
                # Keep the watcher alive across transient API failures.
                print(f"Error: {exc}", file=sys.stderr)
            if args.once:
                return 0
            time.sleep(args.poll_seconds)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Application orchestration helpers."""

from __future__ import annotations

import sys
import time
from typing import Any

from src.color.extractor import album_rgb_from_url
from src.color.utils import rgb_hex
from src.light.base import LightController
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


def run_watcher(
    spotify: SpotifyClient,
    controller: LightController | None,
    poll_seconds: float,
    dry_run: bool,
    once: bool,
) -> int:
    last_track_id = None

    while True:
        try:
            track = current_track_color(spotify)
            if track and track.track_id != last_track_id:
                apply_track_color(controller, track, dry_run)
                last_track_id = track.track_id
        except SpotifyRateLimitError as exc:
            print(
                f"Spotify rate limited the request; sleeping "
                f"{exc.retry_after}s.",
                file=sys.stderr,
            )
            if once:
                return 1
            time.sleep(exc.retry_after)
            continue
        except Exception as exc:
            # Keep the watcher alive across transient API failures.
            print(f"Error: {exc}", file=sys.stderr)
        if once:
            return 0
        time.sleep(poll_seconds)

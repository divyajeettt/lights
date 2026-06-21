"""Application orchestration helpers."""

import sys
import time
from typing import Any

from src.color import album_rgb_from_url, rgb_hex
from src.light import LightController
from src.models import TrackColor, TrackSummary
from src.spotify import SpotifyClient, SpotifyRateLimitError


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
        artist.get("name", "Unknown artist") for artist in item.get("artists", [])
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


def apply_track_color(
    controller: LightController | None,
    track: TrackColor,
) -> None:
    suffix = " (fallback color)" if track.fallback_used else ""
    print(f"{track.label} -> {rgb_hex(track.rgb)}{suffix}")
    if controller is None:
        print(f"Dry run: would set bulb to {rgb_hex(track.rgb)}")
        return
    controller.set_rgb(track.rgb)
    print("Bulb color updated.")


def run_watcher(
    spotify: SpotifyClient,
    controller: LightController | None,
    poll_seconds: float,
    dry_run_once: bool,
) -> int:
    last_track_id = None

    while True:
        try:
            summary = current_track_summary(spotify)
            if summary and summary.track_id != last_track_id:
                if (track := track_color_from_summary(summary)):
                    apply_track_color(controller, track)
                last_track_id = summary.track_id
        except SpotifyRateLimitError as exc:
            print(
                f"Spotify rate limited the request; sleeping {exc.retry_after}s.",
                file=sys.stderr,
            )
            if dry_run_once:
                return 1
            time.sleep(exc.retry_after)
            continue
        except Exception as exc:
            # Keep the watcher alive across transient API failures.
            print(f"Error: {exc}", file=sys.stderr)
        if dry_run_once:
            return 0
        time.sleep(poll_seconds)

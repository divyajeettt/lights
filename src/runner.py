"""Application orchestration helpers."""

import sys
import time
from typing import Any

from src.color import album_palette_from_url, album_rgb_from_url, rgb_hex
from src.enums import LightColorMode
from src.light import LightController
from src.models import TrackColor, TrackLightColors, TrackSummary
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


def track_light_colors_from_summary(
    summary: TrackSummary,
    light_count: int,
    color_mode: LightColorMode,
) -> TrackLightColors | None:
    image_url = best_album_image(summary.item)
    if not image_url:
        print(f"No album image for {summary.label}")
        return None
    if color_mode == LightColorMode.SAME:
        rgb, fallback_used = album_rgb_from_url(image_url)
        rgbs = [rgb] * light_count
    elif color_mode == LightColorMode.ALBUM_PALETTE:
        rgbs, fallback_used = album_palette_from_url(image_url, count=light_count)
    else:
        raise ValueError(f"Unsupported light color mode: {color_mode}")
    return TrackLightColors(
        track_id=summary.track_id,
        label=summary.label,
        rgbs=rgbs,
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


def apply_track_light_colors(
    controller: LightController | None,
    track: TrackLightColors,
    light_labels: list[str],
) -> None:
    suffix = " (fallback color)" if track.fallback_used else ""
    colors = ", ".join(
        f"{label}={rgb_hex(rgb)}"
        for label, rgb in zip(light_labels, track.rgbs, strict=False)
    )
    print(f"{track.label} -> {colors}{suffix}")
    if controller is None:
        print(f"Dry run: would set {colors}")
        return
    if hasattr(controller, "set_rgbs"):
        controller.set_rgbs(track.rgbs)
    else:
        controller.set_rgb(track.rgbs[0])
    print("Bulb colors updated.")


def _run_watcher_loop(
    spotify: SpotifyClient,
    controller: LightController | None,
    poll_seconds: float,
    dry_run_once: bool,
    light_labels: list[str],
    light_count: int,
    color_mode: LightColorMode,
) -> int:
    last_track_id = None
    while True:
        try:
            summary = current_track_summary(spotify)
            if summary and summary.track_id != last_track_id:
                track = track_light_colors_from_summary(
                    summary,
                    light_count=light_count,
                    color_mode=color_mode,
                )
                if track:
                    apply_track_light_colors(controller, track, light_labels)
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
                return 1
        if dry_run_once:
            return 0
        time.sleep(poll_seconds)


def run_watcher(
    spotify: SpotifyClient,
    controller: LightController | None,
    poll_seconds: float,
    dry_run_once: bool,
    light_count: int = 1,
    color_mode: LightColorMode = LightColorMode.ALBUM_PALETTE,
    auto_switch: bool = False,
) -> int:
    default_labels = [f"bulb {index}" for index in range(1, light_count + 1)]
    light_labels = (
        list(getattr(controller, "light_labels", default_labels))
        if controller is not None
        else default_labels
    )

    result = 0
    try:
        if auto_switch:
            print("Switching bulb(s) on")
            controller.set_power(True)

        result = _run_watcher_loop(
            spotify=spotify,
            controller=controller,
            poll_seconds=poll_seconds,
            dry_run_once=dry_run_once,
            light_labels=light_labels,
            light_count=light_count,
            color_mode=color_mode,
        )
    except KeyboardInterrupt:
        if not auto_switch:
            raise
        result = 130
    finally:
        if auto_switch:
            try:
                print("Switching bulb(s) off")
                controller.set_power(False)
            except Exception as exc:
                print(f"Error switching bulb(s) off: {exc}", file=sys.stderr)
                if result == 0:
                    result = 1

    return result

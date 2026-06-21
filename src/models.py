"""Shared application models."""

from dataclasses import dataclass
from typing import Any, TypeAlias

Color: TypeAlias = tuple[int, int, int]


@dataclass(frozen=True)
class TrackSummary:
    track_id: str
    label: str
    item: dict[str, Any]


@dataclass(frozen=True)
class TrackColor:
    track_id: str
    label: str
    rgb: Color
    fallback_used: bool = False

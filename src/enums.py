"""Closed string vocabularies used across integrations."""

from enum import StrEnum


class LightColorMode(StrEnum):
    SAME = "same"
    ALBUM_PALETTE = "album_palette"


class DiagnosticStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    SKIP = "SKIP"

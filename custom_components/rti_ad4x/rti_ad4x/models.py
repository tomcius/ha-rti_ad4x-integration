"""Data model for RTI AD-4x zone state."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ZoneState:
    zone: int
    power: bool
    mute: bool
    source: int
    volume: int  # native device scale, 0-75 (0 = loudest)
    bass: int  # -12..12
    treble: int  # -12..12

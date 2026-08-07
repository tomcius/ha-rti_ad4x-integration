"""Low-level RTI AD-4x ASCII control-port protocol.

Reverse-engineered from a live AD-4x (fw 1.03.18, TCP port 23) plus the
open-source AD-8x MQTT bridge (srhunt-cyber/RTI-AD8x-Home-Assistant-bridge)
— the AD-4x and AD-8x share the same zone-amp command set and only differ
in zone count. Not real Telnet: no option negotiation, plain ASCII lines
terminated with a bare "\\r".
"""
from __future__ import annotations

from dataclasses import dataclass

EOL = b"\r"
# Sent once right after connect, before any *ZN command is accepted.
INIT_HANDSHAKE = b"\x1b2\r"

VOL_MIN = 0
VOL_MAX = 75
TONE_MIN = -12
TONE_MAX = 12


def _zz(zone: int) -> str:
    return f"{zone:02d}"


def cmd_power(zone: int, on: bool) -> bytes:
    return f"*ZN{_zz(zone)}PWR{'01' if on else '00'}\r".encode("ascii")


def cmd_mute(zone: int, on: bool) -> bytes:
    return f"*ZN{_zz(zone)}MUT{'01' if on else '00'}\r".encode("ascii")


def cmd_source(zone: int, source: int) -> bytes:
    return f"*ZN{_zz(zone)}SRC{source:02d}\r".encode("ascii")


def cmd_volume(zone: int, raw_volume: int) -> bytes:
    """raw_volume is the amp's native 0-75 scale (0 = loudest)."""
    raw_volume = max(VOL_MIN, min(VOL_MAX, raw_volume))
    return f"*ZN{_zz(zone)}VOL{raw_volume:02d}\r".encode("ascii")


def cmd_volume_up(zone: int) -> bytes:
    return f"*ZN{_zz(zone)}VOLUP\r".encode("ascii")


def cmd_volume_down(zone: int) -> bytes:
    return f"*ZN{_zz(zone)}VOLDN\r".encode("ascii")


def encode_tone(level: int) -> str:
    """Encode a -12..12 bass/treble level into the amp's two-digit form.

    Negative values are offset by +20 before formatting (e.g. -4 -> "24"),
    zero/positive values are sent as-is. Odd values are rounded toward
    zero to the nearest even step — mirrors the only tested reference impl.
    """
    lvl = max(TONE_MIN, min(TONE_MAX, int(level)))
    if lvl % 2 != 0:
        lvl = lvl - 1 if lvl > 0 else lvl + 1
    return f"{lvl:02d}" if lvl >= 0 else f"{abs(lvl) + 20:02d}"


def decode_tone(raw: int) -> int:
    """Inverse of encode_tone's +20 offset for values read back in replies.

    encode_tone stores negative levels as abs(lvl) + 20, so recovering the
    sign requires 20 - raw, not raw - 20.
    """
    return 20 - raw if raw > TONE_MAX else raw


def cmd_bass(zone: int, level: int) -> bytes:
    return f"*ZN{_zz(zone)}BAS{encode_tone(level)}\r".encode("ascii")


def cmd_treble(zone: int, level: int) -> bytes:
    return f"*ZN{_zz(zone)}TRB{encode_tone(level)}\r".encode("ascii")


def cmd_status_query(zone: int) -> bytes:
    return f"*ZN{_zz(zone)}STA00\r".encode("ascii")


def cmd_tone_query(zone: int) -> bytes:
    return f"*ZN{_zz(zone)}SET00\r".encode("ascii")


def cmd_all_off() -> bytes:
    return b"*ZALLPWR00\r"


@dataclass
class ParsedStatus:
    zone: int
    power: bool
    mute: bool
    source: int
    volume: int


@dataclass
class ParsedTone:
    zone: int
    bass: int
    treble: int


def parse_status(line: str) -> ParsedStatus | None:
    """Parse a '#zz,power,mute,source,vol' reply. None for anything else,
    including the generic '#?' invalid-command reply."""
    line = line.strip()
    if not line.startswith("#") or line == "#?":
        return None
    parts = line[1:].split(",")
    if len(parts) != 5:
        return None
    try:
        zone_s, power_s, mute_s, source_s, vol_s = parts
        return ParsedStatus(
            zone=int(zone_s),
            power=power_s == "1",
            mute=mute_s == "1",
            source=int(source_s),
            volume=abs(int(vol_s)),
        )
    except ValueError:
        return None


def parse_tone(line: str) -> ParsedTone | None:
    """Parse a '$zz,bass,treble' reply. None for anything else."""
    line = line.strip()
    if not line.startswith("$") or line == "$?":
        return None
    parts = line[1:].split(",")
    if len(parts) != 3:
        return None
    try:
        zone_s, bass_s, treble_s = parts
        return ParsedTone(
            zone=int(zone_s),
            bass=decode_tone(int(bass_s)),
            treble=decode_tone(int(treble_s)),
        )
    except ValueError:
        return None

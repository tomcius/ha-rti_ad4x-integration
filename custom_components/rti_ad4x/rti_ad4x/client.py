"""Async TCP client for the RTI AD-4x zone amplifier."""
from __future__ import annotations

import asyncio
import logging

from .models import ZoneState
from .protocol import (
    EOL,
    INIT_HANDSHAKE,
    cmd_all_off,
    cmd_bass,
    cmd_mute,
    cmd_power,
    cmd_source,
    cmd_status_query,
    cmd_tone_query,
    cmd_treble,
    cmd_volume,
    cmd_volume_down,
    cmd_volume_up,
    parse_status,
    parse_tone,
)

_LOGGER = logging.getLogger(__name__)

CONNECT_TIMEOUT = 3.0
COMMAND_TIMEOUT = 3.0
_MAX_NOISE_LINES = 5
_QUERY_RETRIES = 2
_RETRY_SLEEP = 0.3


class RtiAd4xError(Exception):
    """Raised on connection/communication failure."""


class RtiAd4xClient:
    """One persistent TCP session to the amp's control port (23).

    The protocol has no push notifications — unlike FNIP, callers must
    poll for state (see coordinator.py). Every command/query is guarded
    by a lock so replies can never be read out of order, and the socket
    is transparently reopened on the next call after any I/O error.
    """

    def __init__(self, host: str, port: int) -> None:
        self._host = host
        self._port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._lock = asyncio.Lock()

    async def async_connect(self) -> None:
        async with self._lock:
            await self._connect_locked()

    async def _connect_locked(self) -> None:
        await self._close_locked()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(self._host, self._port), timeout=CONNECT_TIMEOUT
            )
        except (OSError, asyncio.TimeoutError) as exc:
            raise RtiAd4xError(str(exc)) from exc
        self._reader = reader
        self._writer = writer
        writer.write(INIT_HANDSHAKE)
        await writer.drain()

    async def async_close(self) -> None:
        async with self._lock:
            await self._close_locked()

    async def _close_locked(self) -> None:
        if self._writer is not None:
            self._writer.close()
            try:
                await self._writer.wait_closed()
            except OSError:
                pass
        self._reader = None
        self._writer = None

    async def _send_raw(self, payload: bytes) -> None:
        if self._writer is None:
            await self._connect_locked()
        assert self._writer is not None
        try:
            self._writer.write(payload)
            await self._writer.drain()
        except OSError as exc:
            await self._close_locked()
            raise RtiAd4xError(str(exc)) from exc

    async def _read_line(self) -> str:
        if self._reader is None:
            raise RtiAd4xError("not connected")
        try:
            raw = await asyncio.wait_for(self._reader.readuntil(EOL), timeout=COMMAND_TIMEOUT)
        except (asyncio.TimeoutError, asyncio.IncompleteReadError, OSError) as exc:
            await self._close_locked()
            raise RtiAd4xError(str(exc)) from exc
        return raw.decode("ascii", errors="replace")

    async def _read_matching(self, parser, zone: int):
        for _ in range(_MAX_NOISE_LINES):
            parsed = parser(await self._read_line())
            if parsed is not None and parsed.zone == zone:
                return parsed
        raise RtiAd4xError(f"no valid reply for zone {zone}")

    async def _send(self, payload: bytes) -> None:
        async with self._lock:
            await self._send_raw(payload)

    async def async_set_power(self, zone: int, on: bool) -> None:
        await self._send(cmd_power(zone, on))

    async def async_set_mute(self, zone: int, on: bool) -> None:
        await self._send(cmd_mute(zone, on))

    async def async_set_source(self, zone: int, source: int) -> None:
        await self._send(cmd_source(zone, source))

    async def async_set_volume(self, zone: int, raw_volume: int) -> None:
        await self._send(cmd_volume(zone, raw_volume))

    async def async_volume_up(self, zone: int) -> None:
        await self._send(cmd_volume_up(zone))

    async def async_volume_down(self, zone: int) -> None:
        await self._send(cmd_volume_down(zone))

    async def async_set_bass(self, zone: int, level: int) -> None:
        await self._send(cmd_bass(zone, level))

    async def async_set_treble(self, zone: int, level: int) -> None:
        await self._send(cmd_treble(zone, level))

    async def async_all_off(self) -> None:
        await self._send(cmd_all_off())

    async def async_query_zone(self, zone: int) -> ZoneState:
        """Query one zone, retrying once (with reconnect) on failure.

        A single flaky exchange right after a (re)connect — observed live,
        typically the first query after an HA restart — would otherwise
        bubble up as UpdateFailed and flash *all* zones' entities
        unavailable at once, even though only one zone's query actually
        failed.
        """
        last_exc: RtiAd4xError | None = None
        for attempt in range(_QUERY_RETRIES):
            try:
                return await self._query_zone_once(zone)
            except RtiAd4xError as exc:
                last_exc = exc
                if attempt < _QUERY_RETRIES - 1:
                    await asyncio.sleep(_RETRY_SLEEP)
        assert last_exc is not None
        raise last_exc

    async def _query_zone_once(self, zone: int) -> ZoneState:
        async with self._lock:
            await self._send_raw(cmd_status_query(zone))
            status = await self._read_matching(parse_status, zone)
            await self._send_raw(cmd_tone_query(zone))
            tone = await self._read_matching(parse_tone, zone)

        return ZoneState(
            zone=zone,
            power=status.power,
            mute=status.mute,
            source=status.source,
            volume=status.volume,
            bass=tone.bass,
            treble=tone.treble,
        )

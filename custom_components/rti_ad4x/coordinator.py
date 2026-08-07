"""DataUpdateCoordinator for the RTI AD-4x.

The amp has no push notifications (unlike FNIP) — state must be polled.
"""
from __future__ import annotations

import logging
from datetime import timedelta

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DEFAULT_POLL_INTERVAL, NUM_ZONES
from .rti_ad4x.client import RtiAd4xClient, RtiAd4xError
from .rti_ad4x.models import ZoneState

_LOGGER = logging.getLogger(__name__)


class RtiAd4xCoordinator(DataUpdateCoordinator[dict[int, ZoneState]]):
    def __init__(self, hass: HomeAssistant, client: RtiAd4xClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="RTI AD-4x",
            update_interval=timedelta(seconds=DEFAULT_POLL_INTERVAL),
        )
        self.client = client

    async def _async_update_data(self) -> dict[int, ZoneState]:
        data: dict[int, ZoneState] = {}
        try:
            for zone in range(1, NUM_ZONES + 1):
                data[zone] = await self.client.async_query_zone(zone)
        except RtiAd4xError as exc:
            raise UpdateFailed(str(exc)) from exc
        return data

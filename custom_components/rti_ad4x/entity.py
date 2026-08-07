"""Shared base entity for RTI AD-4x zone entities."""
from __future__ import annotations

import dataclasses
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_FW_VERSION, CONF_MAC, CONF_MODEL, DOMAIN
from .coordinator import RtiAd4xCoordinator
from .rti_ad4x.models import ZoneState


class RtiAd4xZoneEntity(CoordinatorEntity[RtiAd4xCoordinator]):
    """Base for every entity backed by one AD-4x zone.

    All 4 zones belong to a single physical amp, so — unlike FNIP, where
    each module is its own HA device — every zone entity here is attached
    to one shared device.
    """

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: RtiAd4xCoordinator,
        entry: ConfigEntry,
        zone: int,
        name: str,
        unique_suffix: str,
    ) -> None:
        super().__init__(coordinator)
        self._entry = entry
        self._zone = zone
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{unique_suffix}_{zone}"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.data.get(CONF_MAC) or entry.entry_id)},
            name=entry.title,
            manufacturer="RTI",
            model=entry.data.get(CONF_MODEL) or "AD-4x",
            sw_version=entry.data.get(CONF_FW_VERSION),
        )

    @property
    def _zone_state(self) -> ZoneState | None:
        return self.coordinator.data.get(self._zone) if self.coordinator.data else None

    def _optimistic_update(self, **changes: Any) -> None:
        """Reflect a just-sent command in HA immediately instead of waiting
        on a full 4-zone/8-round-trip coordinator poll (async_request_refresh
        made every write feel like it "froze" for a few seconds). The next
        scheduled poll (DEFAULT_POLL_INTERVAL) reconciles this against the
        amp's actual state, correcting any rounding/clamping drift (e.g.
        odd bass/treble values, out-of-range volume).
        """
        state = self._zone_state
        if state is None:
            return
        data = dict(self.coordinator.data)
        data[self._zone] = dataclasses.replace(state, **changes)
        self.coordinator.async_set_updated_data(data)

"""Select platform for RTI AD-4x — per-zone source input."""
from __future__ import annotations

from homeassistant.components.select import SelectEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, CONF_ZONES, DOMAIN, NUM_ZONES, SOURCE_NAMES
from .coordinator import RtiAd4xCoordinator
from .entity import RtiAd4xZoneEntity

_NAME_TO_SOURCE = {name: num for num, name in SOURCE_NAMES.items()}


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RtiAd4xCoordinator = hass.data[DOMAIN][entry.entry_id]
    zones = entry.data[CONF_ZONES]

    entities = [
        RtiAd4xSourceSelect(coordinator, entry, zone, zones[str(zone)][CONF_NAME])
        for zone in range(1, NUM_ZONES + 1)
    ]
    async_add_entities(entities)


class RtiAd4xSourceSelect(RtiAd4xZoneEntity, SelectEntity):
    _attr_options = list(SOURCE_NAMES.values())

    def __init__(
        self, coordinator: RtiAd4xCoordinator, entry: ConfigEntry, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry, zone, f"{zone_name} źródło", "source")

    @property
    def current_option(self) -> str | None:
        state = self._zone_state
        if state is None:
            return None
        return SOURCE_NAMES.get(state.source)

    async def async_select_option(self, option: str) -> None:
        source = _NAME_TO_SOURCE.get(option)
        if source is None:
            return
        await self.coordinator.client.async_set_source(self._zone, source)
        await self.coordinator.async_request_refresh()

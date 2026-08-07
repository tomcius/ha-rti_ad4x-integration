"""Switch platform for RTI AD-4x — per-zone power and mute."""
from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import CONF_NAME, CONF_ZONES, DOMAIN, NUM_ZONES
from .coordinator import RtiAd4xCoordinator
from .entity import RtiAd4xZoneEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RtiAd4xCoordinator = hass.data[DOMAIN][entry.entry_id]
    zones = entry.data[CONF_ZONES]

    entities: list[SwitchEntity] = []
    for zone in range(1, NUM_ZONES + 1):
        zone_name = zones[str(zone)][CONF_NAME]
        entities.append(RtiAd4xPowerSwitch(coordinator, entry, zone, zone_name))
        entities.append(RtiAd4xMuteSwitch(coordinator, entry, zone, zone_name))
    async_add_entities(entities)


class RtiAd4xPowerSwitch(RtiAd4xZoneEntity, SwitchEntity):
    def __init__(
        self, coordinator: RtiAd4xCoordinator, entry: ConfigEntry, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry, zone, f"{zone_name} zasilanie", "power")

    @property
    def is_on(self) -> bool | None:
        state = self._zone_state
        return None if state is None else state.power

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_power(self._zone, True)
        self._optimistic_update(power=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_power(self._zone, False)
        self._optimistic_update(power=False)


class RtiAd4xMuteSwitch(RtiAd4xZoneEntity, SwitchEntity):
    def __init__(
        self, coordinator: RtiAd4xCoordinator, entry: ConfigEntry, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry, zone, f"{zone_name} wyciszenie", "mute")

    @property
    def is_on(self) -> bool | None:
        state = self._zone_state
        return None if state is None else state.mute

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_mute(self._zone, True)
        self._optimistic_update(mute=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.client.async_set_mute(self._zone, False)
        self._optimistic_update(mute=False)

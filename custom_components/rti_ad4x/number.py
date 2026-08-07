"""Number platform for RTI AD-4x — per-zone volume, bass, treble."""
from __future__ import annotations

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import (
    CONF_NAME,
    CONF_ZONES,
    DOMAIN,
    NUM_ZONES,
    TONE_MAX,
    TONE_MIN,
    TONE_STEP,
    VOL_MAX,
    VOL_MIN,
)
from .coordinator import RtiAd4xCoordinator
from .entity import RtiAd4xZoneEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ConfigEntry, async_add_entities: AddEntitiesCallback
) -> None:
    coordinator: RtiAd4xCoordinator = hass.data[DOMAIN][entry.entry_id]
    zones = entry.data[CONF_ZONES]

    entities: list[NumberEntity] = []
    for zone in range(1, NUM_ZONES + 1):
        zone_name = zones[str(zone)][CONF_NAME]
        entities.append(RtiAd4xVolumeNumber(coordinator, entry, zone, zone_name))
        entities.append(RtiAd4xBassNumber(coordinator, entry, zone, zone_name))
        entities.append(RtiAd4xTrebleNumber(coordinator, entry, zone, zone_name))
    async_add_entities(entities)


class RtiAd4xVolumeNumber(RtiAd4xZoneEntity, NumberEntity):
    """Zone volume, shown 0-75 with the intuitive higher-is-louder direction.

    The amp's own native scale is inverted (0 = loudest, 75 = near-silent)
    — confirmed against the AD-8x reference bridge's MQTT number config,
    which applies the same "75 minus value" flip for the same reason. We
    invert here so the HA slider behaves the way anyone would expect.
    """

    _attr_native_min_value = VOL_MIN
    _attr_native_max_value = VOL_MAX
    _attr_native_step = 1
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self, coordinator: RtiAd4xCoordinator, entry: ConfigEntry, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry, zone, f"{zone_name} głośność", "volume")

    @property
    def native_value(self) -> float | None:
        state = self._zone_state
        return None if state is None else VOL_MAX - state.volume

    async def async_set_native_value(self, value: float) -> None:
        raw = VOL_MAX - int(value)
        await self.coordinator.client.async_set_volume(self._zone, raw)
        await self.coordinator.async_request_refresh()


class RtiAd4xBassNumber(RtiAd4xZoneEntity, NumberEntity):
    _attr_native_min_value = TONE_MIN
    _attr_native_max_value = TONE_MAX
    _attr_native_step = TONE_STEP
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self, coordinator: RtiAd4xCoordinator, entry: ConfigEntry, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry, zone, f"{zone_name} tony niskie", "bass")

    @property
    def native_value(self) -> float | None:
        state = self._zone_state
        return None if state is None else state.bass

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_bass(self._zone, int(value))
        await self.coordinator.async_request_refresh()


class RtiAd4xTrebleNumber(RtiAd4xZoneEntity, NumberEntity):
    _attr_native_min_value = TONE_MIN
    _attr_native_max_value = TONE_MAX
    _attr_native_step = TONE_STEP
    _attr_mode = NumberMode.SLIDER

    def __init__(
        self, coordinator: RtiAd4xCoordinator, entry: ConfigEntry, zone: int, zone_name: str
    ) -> None:
        super().__init__(coordinator, entry, zone, f"{zone_name} tony wysokie", "treble")

    @property
    def native_value(self) -> float | None:
        state = self._zone_state
        return None if state is None else state.treble

    async def async_set_native_value(self, value: float) -> None:
        await self.coordinator.client.async_set_treble(self._zone, int(value))
        await self.coordinator.async_request_refresh()

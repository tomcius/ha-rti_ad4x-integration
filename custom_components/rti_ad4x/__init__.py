"""The RTI AD-4x integration."""
from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT, Platform
from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .coordinator import RtiAd4xCoordinator
from .rti_ad4x.client import RtiAd4xClient

PLATFORMS: list[Platform] = [Platform.SWITCH, Platform.NUMBER, Platform.SELECT]


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    client = RtiAd4xClient(entry.data[CONF_HOST], entry.data[CONF_PORT])
    await client.async_connect()

    coordinator = RtiAd4xCoordinator(hass, client)
    await coordinator.async_config_entry_first_refresh()

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = coordinator
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        coordinator: RtiAd4xCoordinator = hass.data[DOMAIN].pop(entry.entry_id)
        await coordinator.client.async_close()
    return unload_ok

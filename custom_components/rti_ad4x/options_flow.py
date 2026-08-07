"""Options flow for RTI AD-4x — edit zone names after setup."""
from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, OptionsFlow
from homeassistant.data_entry_flow import FlowResult

from .const import CONF_NAME, CONF_ZONES, NUM_ZONES


class RtiAd4xOptionsFlow(OptionsFlow):
    """Re-run the zone-naming step against the entry's current values."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        current = self._entry.data.get(CONF_ZONES, {})

        if user_input is not None:
            zones = {
                str(zone): {
                    CONF_NAME: user_input.get(f"zone_{zone}_name", f"Strefa {zone}")
                }
                for zone in range(1, NUM_ZONES + 1)
            }
            new_data = dict(self._entry.data)
            new_data[CONF_ZONES] = zones
            self.hass.config_entries.async_update_entry(self._entry, data=new_data)
            return self.async_create_entry(title="", data={})

        fields: dict[Any, Any] = {}
        for zone in range(1, NUM_ZONES + 1):
            existing = current.get(str(zone), {})
            fields[
                vol.Optional(
                    f"zone_{zone}_name", default=existing.get(CONF_NAME, f"Strefa {zone}")
                )
            ] = str

        return self.async_show_form(step_id="init", data_schema=vol.Schema(fields))

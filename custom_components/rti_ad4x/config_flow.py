"""Config flow for the RTI AD-4x integration."""
from __future__ import annotations

import logging
import re
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigEntry, ConfigFlow, OptionsFlow
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_FW_VERSION,
    CONF_MAC,
    CONF_MODEL,
    CONF_NAME,
    CONF_ZONES,
    DEFAULT_PORT,
    DOMAIN,
    NUM_ZONES,
)
from .rti_ad4x.client import RtiAd4xClient, RtiAd4xError

_LOGGER = logging.getLogger(__name__)

_WEB_PROBE_TIMEOUT = 5

# Extracted from the amp's own unauthenticated status page (confirmed live
# against a real AD-4x, fw 1.03.18): inline <script> vars set by the
# firmware itself, e.g. `var modname="RTI AD-4x";` / `var fwrev='1.03.18';`.
_RE_MODNAME = re.compile(r"modname\s*=\s*\"([^\"]+)\"")
_RE_FWREV = re.compile(r"fwrev\s*=\s*'([^']+)'")
_RE_MAC = re.compile(r"macaddr\s*=\s*'([^']+)'")


class CannotConnect(Exception):
    """Raised when the amp's control port doesn't answer."""


async def _probe_web_ui(hass, host: str) -> dict[str, str]:
    """Best-effort scrape of the amp's unauthenticated status page for
    model/firmware/MAC. Purely informational — an empty result here is not
    fatal, the control-port probe below is the real connectivity check.
    """
    session = async_get_clientsession(hass)
    try:
        async with session.get(f"http://{host}/", timeout=_WEB_PROBE_TIMEOUT) as resp:
            text = await resp.text()
    except Exception:  # noqa: BLE001 - informational probe, any failure is fine
        return {}

    info: dict[str, str] = {}
    for key, pattern in (
        (CONF_MODEL, _RE_MODNAME),
        (CONF_FW_VERSION, _RE_FWREV),
        (CONF_MAC, _RE_MAC),
    ):
        if match := pattern.search(text):
            info[key] = match.group(1)
    return info


async def _probe_control_port(host: str, port: int) -> None:
    client = RtiAd4xClient(host, port)
    try:
        await client.async_connect()
        await client.async_query_zone(1)
    except RtiAd4xError as exc:
        raise CannotConnect from exc
    finally:
        await client.async_close()


def _default_zone_name(zone: int) -> str:
    return f"Strefa {zone}"


class RtiAd4xConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for the RTI AD-4x."""

    VERSION = 1

    def __init__(self) -> None:
        self._host: str | None = None
        self._port: int = DEFAULT_PORT
        self._info: dict[str, str] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            self._host = user_input[CONF_HOST]
            self._port = user_input[CONF_PORT]
            try:
                await _probe_control_port(self._host, self._port)
            except CannotConnect:
                errors["base"] = "cannot_connect"
            else:
                self._info = await _probe_web_ui(self.hass, self._host)
                unique_id = self._info.get(CONF_MAC) or f"{self._host}:{self._port}"
                await self.async_set_unique_id(unique_id)
                self._abort_if_unique_id_configured()
                return await self.async_step_zones()

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST): str,
                vol.Optional(CONF_PORT, default=DEFAULT_PORT): int,
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def async_step_zones(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        if user_input is not None:
            zones = {
                str(zone): {
                    CONF_NAME: user_input.get(f"zone_{zone}_name", _default_zone_name(zone))
                }
                for zone in range(1, NUM_ZONES + 1)
            }
            model = self._info.get(CONF_MODEL, "RTI AD-4x")
            return self.async_create_entry(
                title=f"{model} ({self._host})",
                data={
                    CONF_HOST: self._host,
                    CONF_PORT: self._port,
                    CONF_MAC: self._info.get(CONF_MAC),
                    CONF_MODEL: model,
                    CONF_FW_VERSION: self._info.get(CONF_FW_VERSION),
                    CONF_ZONES: zones,
                },
            )

        schema = vol.Schema(
            {
                vol.Optional(f"zone_{zone}_name", default=_default_zone_name(zone)): str
                for zone in range(1, NUM_ZONES + 1)
            }
        )
        return self.async_show_form(
            step_id="zones",
            data_schema=schema,
            description_placeholders={
                "model": self._info.get(CONF_MODEL, "RTI AD-4x"),
                "fw": self._info.get(CONF_FW_VERSION, "?"),
            },
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        from .options_flow import RtiAd4xOptionsFlow

        return RtiAd4xOptionsFlow(config_entry)

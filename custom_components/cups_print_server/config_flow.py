"""Config flow for CUPS Print Server."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_PORT, CONF_USE_SSL, DEFAULT_PORT, DEFAULT_USE_SSL, DOMAIN
from .ipp import CupsClient, CupsConnectionError, CupsIppError


async def _validate(hass: HomeAssistant, data: dict[str, Any]) -> list[str]:
    client = CupsClient(
        async_get_clientsession(hass),
        data[CONF_HOST],
        data[CONF_PORT],
        data[CONF_USE_SSL],
    )
    queues = await client.discover_queues()
    if not queues:
        raise CupsIppError("No CUPS printer queues found")
    await client.get_printer(queues[0])
    return queues


class CupsPrintServerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for CUPS Print Server."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> FlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input[CONF_HOST] = host

            await self.async_set_unique_id(f"{host}:{user_input[CONF_PORT]}")
            self._abort_if_unique_id_configured()

            try:
                queues = await _validate(self.hass, user_input)
            except CupsConnectionError:
                errors["base"] = "cannot_connect"
            except CupsIppError:
                errors["base"] = "no_printers"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(
                    title=f"CUPS Print Server ({host})",
                    data=user_input,
                    description_placeholders={"queues": ", ".join(queues)},
                )

        schema = vol.Schema(
            {
                vol.Required(CONF_HOST, default=(user_input or {}).get(CONF_HOST, "")): str,
                vol.Required(CONF_PORT, default=(user_input or {}).get(CONF_PORT, DEFAULT_PORT)): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=65535)
                ),
                vol.Required(CONF_USE_SSL, default=(user_input or {}).get(CONF_USE_SSL, DEFAULT_USE_SSL)): bool,
            }
        )

        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

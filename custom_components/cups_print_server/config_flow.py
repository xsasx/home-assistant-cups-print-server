"""Config flow for CUPS Print Server."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_AUTO_POWER_OFF,
    CONF_AUTO_POWER_ON,
    CONF_PORT,
    CONF_POWER_OFF_DELAY,
    CONF_POWER_SWITCH,
    CONF_USE_SSL,
    DEFAULT_AUTO_POWER_OFF,
    DEFAULT_AUTO_POWER_ON,
    DEFAULT_PORT,
    DEFAULT_POWER_OFF_DELAY,
    DEFAULT_USE_SSL,
    DOMAIN,
)
from .ipp import CupsClient, CupsConnectionError, CupsIppError


async def _validate(
    hass: HomeAssistant,
    data: dict[str, Any],
) -> list[str]:
    """Validate connection and discover CUPS queues."""
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


def _schema(defaults: dict[str, Any]) -> vol.Schema:
    """Build the connection form."""
    return vol.Schema(
        {
            vol.Required(
                CONF_HOST,
                default=defaults.get(CONF_HOST, ""),
            ): str,
            vol.Required(
                CONF_PORT,
                default=defaults.get(CONF_PORT, DEFAULT_PORT),
            ): vol.All(
                vol.Coerce(int),
                vol.Range(min=1, max=65535),
            ),
            vol.Required(
                CONF_USE_SSL,
                default=defaults.get(CONF_USE_SSL, DEFAULT_USE_SSL),
            ): bool,
        }
    )


class CupsPrintServerConfigFlow(
    config_entries.ConfigFlow,
    domain=DOMAIN,
):
    """Handle a config flow for CUPS Print Server."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> CupsPrintServerOptionsFlow:
        """Return the options flow."""
        return CupsPrintServerOptionsFlow()

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Handle initial setup."""
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input[CONF_HOST] = host

            await self.async_set_unique_id(
                f"{host}:{user_input[CONF_PORT]}"
            )
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
                    description_placeholders={
                        "queues": ", ".join(queues)
                    },
                )

        return self.async_show_form(
            step_id="user",
            data_schema=_schema(user_input or {}),
            errors=errors,
        )

    async def async_step_reconfigure(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Reconfigure an existing CUPS server."""
        entry = self._get_reconfigure_entry()
        errors: dict[str, str] = {}

        if user_input is not None:
            host = user_input[CONF_HOST].strip()
            user_input[CONF_HOST] = host

            new_unique_id = (
                f"{host}:{user_input[CONF_PORT]}"
            )

            try:
                await _validate(self.hass, user_input)
            except CupsConnectionError:
                errors["base"] = "cannot_connect"
            except CupsIppError:
                errors["base"] = "no_printers"
            except Exception:
                errors["base"] = "unknown"
            else:
                return self.async_update_reload_and_abort(
                    entry,
                    data_updates=user_input,
                    unique_id=new_unique_id,
                    title=f"CUPS Print Server ({host})",
                )

        return self.async_show_form(
            step_id="reconfigure",
            data_schema=_schema(
                user_input or dict(entry.data)
            ),
            errors=errors,
        )


class CupsPrintServerOptionsFlow(
    config_entries.OptionsFlow,
):
    """Manage optional printer power settings."""

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> FlowResult:
        """Show printer power options."""
        if user_input is not None:
            return self.async_create_entry(
                title="",
                data=user_input,
            )

        options = self.config_entry.options

        schema_fields: dict[Any, Any] = {}

        switch = options.get(CONF_POWER_SWITCH)

        if switch:
            switch_key = vol.Optional(
                CONF_POWER_SWITCH,
                default=switch,
            )
        else:
            switch_key = vol.Optional(CONF_POWER_SWITCH)

        schema_fields[switch_key] = selector.EntitySelector(
            selector.EntitySelectorConfig(
                domain="switch",
            )
        )

        schema_fields[
            vol.Required(
                CONF_AUTO_POWER_ON,
                default=options.get(
                    CONF_AUTO_POWER_ON,
                    DEFAULT_AUTO_POWER_ON,
                ),
            )
        ] = selector.BooleanSelector()

        schema_fields[
            vol.Required(
                CONF_AUTO_POWER_OFF,
                default=options.get(
                    CONF_AUTO_POWER_OFF,
                    DEFAULT_AUTO_POWER_OFF,
                ),
            )
        ] = selector.BooleanSelector()

        schema_fields[
            vol.Required(
                CONF_POWER_OFF_DELAY,
                default=options.get(
                    CONF_POWER_OFF_DELAY,
                    DEFAULT_POWER_OFF_DELAY,
                ),
            )
        ] = vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=1440),
        )

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(schema_fields),
        )

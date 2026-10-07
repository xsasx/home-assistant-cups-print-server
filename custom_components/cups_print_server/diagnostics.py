"""Diagnostics support for CUPS Print Server."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .coordinator import CupsCoordinator


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: ConfigEntry
) -> dict:
    """Return diagnostics for a config entry."""
    coordinator: CupsCoordinator = entry.runtime_data
    return {
        "config": {
            "host": entry.data.get("host"),
            "port": entry.data.get("port"),
            "use_ssl": entry.data.get("use_ssl"),
        },
        "data": coordinator.data,
    }

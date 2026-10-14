"""CUPS Print Server integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import PLATFORMS
from .coordinator import CupsCoordinator
from .power import CupsPowerManager


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up CUPS Print Server."""
    coordinator = CupsCoordinator(hass, entry)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    manager = CupsPowerManager(hass, entry, coordinator)
    coordinator.power_manager = manager

    await hass.config_entries.async_forward_entry_setups(
        entry,
        PLATFORMS,
    )

    manager.start()

    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload CUPS Print Server."""
    unloaded = await hass.config_entries.async_unload_platforms(
        entry,
        PLATFORMS,
    )

    if unloaded:
        coordinator = entry.runtime_data
        manager = getattr(coordinator, "power_manager", None)

        if manager is not None:
            await manager.stop()

    return unloaded

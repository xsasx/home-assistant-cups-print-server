"""Countdown sensor for CUPS printer power management."""

from __future__ import annotations

from homeassistant.components.sensor import SensorEntity
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN


class CupsPowerCountdown(CoordinatorEntity, SensorEntity):
    """Show remaining time until automatic printer shutdown."""

    _attr_has_entity_name = True
    _attr_name = "Verbleibende Ausschaltzeit"
    _attr_native_unit_of_measurement = "s"
    _attr_icon = "mdi:timer-outline"

    def __init__(self, coordinator, entry, queue):
        super().__init__(coordinator)

        self.entry = entry
        self.queue = queue

        self._attr_unique_id = (
            f"{entry.entry_id}_{queue}_power_countdown"
        )

    @property
    def device_info(self) -> DeviceInfo:
        """Attach sensor to the existing printer device."""
        return DeviceInfo(
            identifiers={
                (
                    DOMAIN,
                    f"{self.entry.entry_id}_{self.queue}",
                )
            }
        )

    @property
    def native_value(self) -> int | None:
        """Return remaining shutdown time in seconds."""
        manager = getattr(
            self.coordinator,
            "power_manager",
            None,
        )

        if manager is None:
            return None

        return manager.remaining_seconds

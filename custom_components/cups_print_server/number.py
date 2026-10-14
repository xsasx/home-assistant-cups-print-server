"""Number entities for CUPS printer power settings."""

from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    CONF_POWER_OFF_DELAY,
    DEFAULT_POWER_OFF_DELAY,
    DOMAIN,
)


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CUPS power-off delay controls."""
    coordinator = entry.runtime_data

    async_add_entities(
        CupsPowerOffDelay(coordinator, entry, queue)
        for queue in coordinator.data.get("queues", {})
    )


class CupsPowerOffDelay(CoordinatorEntity, NumberEntity):
    """Adjust the automatic power-off delay."""

    _attr_has_entity_name = True
    _attr_name = "Ausschaltverzögerung"
    _attr_native_min_value = 1
    _attr_native_max_value = 1440
    _attr_native_step = 1
    _attr_native_unit_of_measurement = "min"
    _attr_mode = NumberMode.BOX
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, coordinator, entry, queue):
        super().__init__(coordinator)
        self.entry = entry
        self.queue = queue
        self._attr_unique_id = (
            f"{entry.entry_id}_{queue}_power_off_delay"
        )

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={
                (DOMAIN, f"{self.entry.entry_id}_{self.queue}")
            }
        )

    @property
    def native_value(self):
        return self.entry.options.get(
            CONF_POWER_OFF_DELAY,
            DEFAULT_POWER_OFF_DELAY,
        )

    async def async_set_native_value(self, value):
        options = dict(self.entry.options)
        options[CONF_POWER_OFF_DELAY] = int(value)

        self.hass.config_entries.async_update_entry(
            self.entry,
            options=options,
        )
        self.async_write_ha_state()

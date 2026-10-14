"""Switch entities for CUPS printer power management."""

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import STATE_OFF, STATE_ON
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_AUTO_POWER_OFF, CONF_AUTO_POWER_ON, DOMAIN


async def async_setup_entry(hass, entry, async_add_entities):
    """Set up CUPS power switches."""
    coordinator = entry.runtime_data

    entities = []
    for queue in coordinator.data.get("queues", {}):
        entities.extend(
            [
                CupsPowerSwitch(coordinator, entry, queue),
                CupsAutomationSwitch(
                    coordinator, entry, queue,
                    CONF_AUTO_POWER_ON, "Automatisch einschalten",
                ),
                CupsAutomationSwitch(
                    coordinator, entry, queue,
                    CONF_AUTO_POWER_OFF, "Automatisch ausschalten",
                ),
            ]
        )

    async_add_entities(entities)


class CupsBaseSwitch(CoordinatorEntity, SwitchEntity):
    """Base switch attached to the existing CUPS printer device."""

    _attr_has_entity_name = True

    def __init__(self, coordinator, entry, queue, suffix, name):
        super().__init__(coordinator)
        self.entry = entry
        self.queue = queue
        self._attr_name = name
        self._attr_unique_id = f"{entry.entry_id}_{queue}_{suffix}"

    @property
    def device_info(self):
        return DeviceInfo(
            identifiers={(DOMAIN, f"{self.entry.entry_id}_{self.queue}")}
        )


class CupsPowerSwitch(CupsBaseSwitch):
    """Control the physical printer's configured smart plug."""

    def __init__(self, coordinator, entry, queue):
        super().__init__(
            coordinator, entry, queue,
            "power_control", "Drucker-Stromversorgung",
        )

    @property
    def available(self):
        entity_id = self.coordinator.power_manager.switch_entity_id
        state = self.hass.states.get(entity_id) if entity_id else None
        return state is not None and state.state in (STATE_ON, STATE_OFF)

    @property
    def is_on(self):
        entity_id = self.coordinator.power_manager.switch_entity_id
        state = self.hass.states.get(entity_id) if entity_id else None
        return state is not None and state.state == STATE_ON

    async def async_turn_on(self, **kwargs):
        await self.coordinator.power_manager.turn_on()

    async def async_turn_off(self, **kwargs):
        await self.coordinator.power_manager.turn_off()


class CupsAutomationSwitch(CupsBaseSwitch):
    """Enable or disable automatic printer power management."""

    def __init__(self, coordinator, entry, queue, key, name):
        super().__init__(coordinator, entry, queue, key, name)
        self.key = key

    @property
    def is_on(self):
        return bool(self.entry.options.get(self.key, False))

    async def _set_value(self, value):
        options = dict(self.entry.options)
        options[self.key] = value
        self.hass.config_entries.async_update_entry(
            self.entry, options=options
        )
        self.async_write_ha_state()

    async def async_turn_on(self, **kwargs):
        await self._set_value(True)

    async def async_turn_off(self, **kwargs):
        await self._set_value(False)
